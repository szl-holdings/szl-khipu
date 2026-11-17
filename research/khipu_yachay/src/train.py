"""Train a real tiny Multinomial NB model on clearly synthetic, author-generated intent examples.

No model downloads, GPU jobs or archaeological record-derived labels. This is an
educational routing model; deterministic verification and source rights control releases.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
import json
import math
import pathlib
import random

from .core import canonical, sha256, tokenize, route_question

LABELS = ("NUMERACY", "RECORDS", "RESEARCH_LIMITS", "DATA_RIGHTS", "METHODS")
# The development and holdout prompt families are structurally separate.
TEMPLATES = {
    "NUMERACY": {
        "train": ["how were decimal knots used to count {}", "show me the numeral places for {}", "how do pendant knots record {}", "describe decimal counting and khipu {}", "what is a numeric cord record for {}", "how are place values positioned on {}", "explain base ten knots and numerical digits {}", "what do knot positions encode in {}", "describe place value and base ten counting {}"],
        "eval": ["explain the position values of knots in {}", "were khipu knots used for base ten {}"],
    },
    "RECORDS": {
        "train": ["where can I find the museum catalog for {}", "look up archival KH number {}", "show me khipu collection metadata {}", "find the Open Khipu Repository record {}", "where is the public KH register for {}", "where do I locate the archive identifier {}", "catalog entry and collection accession for {}", "where can I search a record identifier {}", "identify repository museum metadata {}"],
        "eval": ["locate the archive identifier for {}", "is there a catalog entry for khipu {}"],
    },
    "RESEARCH_LIMITS": {
        "train": ["can we decipher the story in {}", "do we know the secret meaning of {}", "has the writing on cord {} been translated", "is every khipu decoded now {}", "prove who authored this ancient record {}", "is the historical meaning certain {}", "what is still unknown about interpreting {}", "has anyone definitively decoded {}", "why is decipherment still uncertain {}"],
        "eval": ["is the historical meaning of {} certain", "have researchers definitively translated {}"],
    },
    "DATA_RIGHTS": {
        "train": ["what reuse rights apply to khipu images {}", "must we credit the original scholars for {}", "who gave permission to train on these records {}", "how should Andean communities be involved {}", "can we scrape copyrighted papers for {}", "does licensing permit reuse of museum photographs {}", "should Indigenous custodians approve data uses {}", "which permissions apply to museum archives {}", "how to respect ownership and consent for {}"],
        "eval": ["are museum photographs licensed for reuse {}", "should Indigenous custodians approve dataset use {}"],
    },
    "METHODS": {
        "train": ["how can we validate cord sums {}", "what does a sha256 record prove about {}", "explain the numerical integrity method {}", "how to test whether the total matches {}", "what does the hash witness actually establish {}", "check arithmetic consistency and sum totals {}", "is a digest enough for historical authenticity {}", "what can a checksum verify about a record {}", "what is the distinction between a numerical match and truth {}"],
        "eval": ["check the arithmetic consistency of {}", "can a digest show a source is authentic {}"],
    }
}
TRAIN_SUBJECTS = ["KH0001", "KH0231", "a record", "a knot", "a cord", "museum data", "an archive", "Inka counting", "a primary cord", "Andean research", "an artifact", "a case study"]
EVAL_SUBJECTS = ["KH0702", "a pendant", "a historical object", "collection evidence", "a museum specimen", "a cord sample", "a collection", "field notes"]


def build_rows(split: str) -> list[dict]:
    if split not in {"train", "eval"}:
        raise ValueError("SPLIT")
    subjects = TRAIN_SUBJECTS if split == "train" else EVAL_SUBJECTS
    out = []
    for label in LABELS:
        for t, template in enumerate(TEMPLATES[label][split]):
            for s, subject in enumerate(subjects):
                text = template.format(subject)
                out.append({"id": f"{split}:{label}:{t}:{s}", "text": text,
                            "label": label, "data_class": "SYNTHETIC_SZL_AUTHORED",
                            "template_family": f"{split}:{label}:{t}"})
    random.Random(14 if split == "train" else 29).shuffle(out)
    return out


def train(rows: list[dict]) -> dict:
    if not rows or any(row["data_class"] != "SYNTHETIC_SZL_AUTHORED" for row in rows):
        raise ValueError("TRAIN_SOURCE_UNQUALIFIED")
    vocab = sorted({token for item in rows for token in tokenize(item["text"])})
    indices = {token: i for i, token in enumerate(vocab)}
    class_counts = Counter(row["label"] for row in rows)
    log_likelihood = {}
    log_prior = {}
    alpha = 1.0
    for label in LABELS:
        counts = Counter(tok for row in rows if row["label"] == label
                         for tok in tokenize(row["text"]))
        denom = sum(counts.values()) + alpha * len(vocab)
        log_likelihood[label] = [round(math.log((counts[word]+alpha)/denom), 12)
                                 for word in vocab]
        log_prior[label] = round(math.log(class_counts[label] / len(rows)), 12)
    return {"schema": "szl.khipu-yachay.nb/v0", "algorithm": "MULTINOMIAL_NAIVE_BAYES",
            "classes": list(LABELS), "vocab": indices,
            "log_prior": log_prior, "log_likelihood": log_likelihood,
            "training_data_class": "SYNTHETIC_ONLY", "historical_dataset_used_for_training": False,
            "trained_weights": True, "production_qualified": False, "uses_quechua_language_model": False}


def evaluate(model: dict, examples: list[dict]) -> dict:
    confusion = {key: {other: 0 for other in (*LABELS, "ABSTAIN")} for key in LABELS}
    correct = 0
    for ex in examples:
        predicted = route_question(ex["text"], model)["intent"]
        confusion[ex["label"]][predicted] += 1
        correct += int(predicted == ex["label"])
    metrics = {}
    for label in LABELS:
        tp = confusion[label][label]
        fp = sum(confusion[y][label] for y in LABELS if y != label)
        fn = sum(n for k, n in confusion[label].items() if k != label)
        denom = 2*tp+fp+fn
        metrics[label] = (2*tp / denom) if denom else None
    return {"evaluation_class": "SYNTHETIC_TEMPLATE_HELDOUT_ONLY",
            "n": len(examples), "correct": correct, "accuracy": correct/len(examples),
            "macro_f1": sum(x for x in metrics.values() if x is not None)/len(metrics),
            "f1_by_class": metrics, "confusion": confusion,
            "archaeological_relevance_measured": False,
            "calibrated_probability": False,
            "independent_human_review": False}


def write_outputs(project: pathlib.Path) -> dict:
    # Never overwrite a prior artifact with an unchecked replacement.
    trainrows, evalrows = build_rows("train"), build_rows("eval")
    model = train(trainrows)
    scores = evaluate(model, evalrows)
    files = {
        "data/synthetic_train.jsonl": b"".join(canonical(r) for r in trainrows),
        "data/synthetic_eval.jsonl": b"".join(canonical(r) for r in evalrows),
        "model/yachay_nb_v0.json": canonical(model),
    }
    for path, data in files.items():
        p = project / path
        with p.open("xb") as f:
            f.write(data)
    report = {"schema": "szl.khipu-yachay.training-receipt/v0",
              "observed_utc": datetime.now(timezone.utc).isoformat(),
              "training_mode": "LOCAL_CPU_TEXT_ROUTER",
              "initialization": "LAPLACE_SMOOTHED_COUNTS",
              "training_examples": len(trainrows), "evaluation_examples": len(evalrows),
              "data": {path: {"sha256": sha256(b), "bytes": len(b)} for path, b in files.items()},
              "metrics": scores, "external_data_training": False,
              "gpu_hours": 0, "paid_jobs": 0, "final_model_is_1_5B": False,
              "weights_are_available": True, "public_model_published": False,
              "deployment_verified": False, "production_qualified": False}
    with (project/"model/training_receipt.json").open("xb") as f:
        f.write(canonical(report))
    return report


if __name__ == "__main__":
    root = pathlib.Path(__file__).resolve().parents[1]
    print(json.dumps(write_outputs(root)["metrics"], indent=2))
