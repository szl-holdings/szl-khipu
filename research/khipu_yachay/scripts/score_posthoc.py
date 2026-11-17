"""Reproducible *post-hoc* OOD stress evidence for Yachay v0.

Prompts were authored after inspecting the model curriculum. This IS NOT a
sealed prospective evaluation, independent cultural validation or benchmark
score. No model training, network calls, uploads or weight changes occur.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from space.app import load_state
from src.core import route_question

DATA = ROOT / "data" / "posthoc_ood_v0.jsonl"
DATA_SHA256 = "41ef4eeabfb1ed12e42e659aff39fa32f405474e59e973c7ff6f0090751b9838"
CATEGORIES = ("NUMERACY", "RECORDS", "RESEARCH_LIMITS", "DATA_RIGHTS", "METHODS")


def read_challenge(path: Path = DATA) -> list[dict]:
    raw = path.read_bytes()
    if (len(raw) > 24000 or b"\r\n" in raw or
            hashlib.sha256(raw).hexdigest() != DATA_SHA256):
        raise ValueError("POSTHOC_CHALLENGE_IDENTITY_MISMATCH")

    def unique_pairs(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError("DUPLICATE_CHALLENGE_KEY")
            obj[key] = value
        return obj

    rows = [json.loads(line, object_pairs_hook=unique_pairs)
            for line in raw.splitlines() if line]
    required = {"id", "label", "text", "data_class", "split",
                "model_training_admitted"}
    names = []
    counts = Counter()
    for row in rows:
        if type(row) is not dict or set(row) != required:
            raise ValueError("CHALLENGE_SCHEMA_MISMATCH")
        if (type(row["text"]) is not str or
                not 10 <= len(row["text"]) <= 500 or
                row["data_class"] != "SZL_ORIGINAL_POSTHOC_CHALLENGE" or
                row["split"] != "DEVELOPER_POSTHOC_EVAL_ONLY_NOT_BLIND" or
                row["model_training_admitted"] is not False):
            raise ValueError("CHALLENGE_RIGHTS_OR_TEXT_INVALID")
        label = row["label"]
        if label not in (*CATEGORIES, "ABSTAIN") or type(label) is not str:
            raise ValueError("CHALLENGE_LABEL_INVALID")
        counts[label] += 1
        names.append(row["id"])
    if len(rows) != 52 or len(set(names)) != len(rows) or any(
            counts[k] != (12 if k == "ABSTAIN" else 8)
            for k in (*CATEGORIES, "ABSTAIN")):
        raise ValueError("CHALLENGE_COVERAGE_INVALID")
    # Exact text exclusion prevents accidental reuse as development prompts.
    train_eval = set()
    for name in ("synthetic_train.jsonl", "synthetic_eval.jsonl"):
        for line in (ROOT / "data" / name).read_text(encoding="utf-8").splitlines():
            train_eval.add(json.loads(line)["text"].casefold())
    if any(row["text"].casefold() in train_eval for row in rows):
        raise ValueError("CHALLENGE_TRAINING_OVERLAP")
    return rows


def measure() -> dict:
    model_state = load_state(ROOT)
    rows = read_challenge()
    hits = Counter()
    abstains = Counter()
    mismatches = Counter()
    for row in rows:
        label = row["label"]
        predicted = route_question(row["text"], model_state["model"])["intent"]
        hits[label] += int(predicted == label)
        abstains[label] += int(predicted == "ABSTAIN")
        if predicted != label:
            mismatches[(label, predicted)] += 1
    known = sum(hits[k] for k in CATEGORIES)
    unrelated = hits["ABSTAIN"]
    data = {
        "schema": "szl.khipu-yachay.posthoc-stress/v1",
        "model_sha256": model_state["model_sha256"],
        "fixture_sha256": DATA_SHA256,
        "evaluation_design": "POSTHOC_AFTER_CURRICULUM_INSPECTION_NOT_BLIND",
        "model_training_performed": False,
        "source_data_training_rights": "NONE_FROM_THIS_EVAL",
        "in_domain": {"n": 40, "correct": known,
                       "accuracy": round(known / 40, 6)},
        "out_of_domain": {"n": 12, "correct_abstentions": unrelated,
                          "abstention_rate": round(unrelated / 12, 6)},
        "class_correct": {k: hits[k] for k in CATEGORIES},
        "class_abstained": {k: abstains[k] for k in CATEGORIES},
        "confusions": [
            {"expected": k[0], "predicted": k[1], "count": v}
            for k, v in sorted(mismatches.items())
        ],
        "not_independent_human_review": True,
        "calibrated_probability": False,
        "archaeological_accuracy_measured": False,
        "production_eligible": False,
        "model_or_dataset_publication_authorized": False,
        "decision": "HOLD_GENERALIZATION_NOT_ESTABLISHED",
    }
    return data


if __name__ == "__main__":
    print(json.dumps(measure(), sort_keys=True, indent=2))
