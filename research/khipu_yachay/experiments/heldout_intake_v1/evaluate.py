# SPDX-License-Identifier: Apache-2.0
"""Bounded, read-only intake for prospective Khipu Yachay evaluation.

A caller-controlled manifest never proves evaluator independence, rights or
historical correctness. Software computes descriptive case-set metrics only;
it cannot authorize training, publicity or model deployment.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import importlib
import json
import math
import os
from pathlib import Path
import re
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT))
_training_source = importlib.import_module('experiments.open_set_r1.train_open_set')
candidate_data = _training_source.candidate_data
predict = _training_source.predict

MODEL_SHA = "1f5dfaf9da2ff2a6228eed02df0cdf12aa9407bf1d5df51f654d53c92c60f47e"
MODEL = PROJECT / "experiments/open_set_r1/candidate_model.json"
INTENTS = frozenset(("NUMERACY", "RECORDS", "RESEARCH_LIMITS", "DATA_RIGHTS", "METHODS"))
CASE_SCHEMA = "szl.yachay.external-intent-case/v1"
MANIFEST_SCHEMA = "szl.yachay.external-intent-manifest/v1"


class EvaluationHold(ValueError):
    """Refuse unsupported inputs without filling in evidence gaps."""


def pairs_unique(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise EvaluationHold("DUPLICATE_JSON_KEY")
        d[k] = v
    return d


def parse(raw: bytes):
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs_unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(
                              EvaluationHold("NONFINITE_NUMBER")))
    except EvaluationHold:
        raise
    except (UnicodeError, ValueError, OverflowError, RecursionError):
        raise EvaluationHold("INVALID_JSON") from None


def read_bounded(path: Path, maximum: int) -> bytes:
    try:
        if path.is_symlink() or not path.is_file():
            raise EvaluationHold("FILE_UNOBSERVED")
        length = path.stat().st_size
        if not 0 < length <= maximum:
            raise EvaluationHold("FILE_BYTE_LIMIT")
        data = path.read_bytes()
        if len(data) != length:
            raise EvaluationHold("FILE_CHANGED_DURING_READ")
        return data
    except OSError:
        raise EvaluationHold("FILE_UNOBSERVED") from None


def validate(manifest_file: Path, cases_file: Path):
    manifest_raw = read_bounded(manifest_file, 8192)
    m = parse(manifest_raw)
    required = {
        "schema", "case_count", "cases_sha256", "model_sha256",
        "data_class", "evaluation_permission", "training_admitted",
        "evaluator_identity_verified", "group_definition"
    }
    if type(m) is not dict or set(m) != required or m["schema"] != MANIFEST_SCHEMA:
        raise EvaluationHold("MANIFEST_SCHEMA")
    if (m["data_class"] != "EVALUATOR_AUTHORED_SYNTHETIC" or
        m["evaluation_permission"] != "CALLER_DECLARED_NOT_INDEPENDENTLY_VERIFIED" or
        m["training_admitted"] is not False or
        m["evaluator_identity_verified"] is not False or
        m["group_definition"] != "SOURCE_FAMILY_DECLARED_NOT_ATTESTED"):
        raise EvaluationHold("RIGHTS_OR_CUSTODY_NOT_VERIFIED")
    if m["model_sha256"] != MODEL_SHA:
        raise EvaluationHold("MODEL_REVISION_MISMATCH")
    if type(m["case_count"]) is not int or not 20 <= m["case_count"] <= 300:
        raise EvaluationHold("CASE_COUNT_BUDGET")
    if type(m["cases_sha256"]) is not str or not re.fullmatch("[0-9a-f]{64}", m["cases_sha256"]):
        raise EvaluationHold("CASE_DIGEST_FORMAT")
    raw = read_bounded(cases_file, 125000)
    if sha256(raw).hexdigest() != m["cases_sha256"]:
        raise EvaluationHold("CASE_SHA256_MISMATCH")
    if b"\r\n" in raw or not raw.endswith(b"\n"):
        raise EvaluationHold("NOT_CANONICAL_LF")
    rows = [parse(x) for x in raw.splitlines()]
    if len(rows) != m["case_count"]:
        raise EvaluationHold("CASE_COUNT_MISMATCH")
    expected_keys = {"schema", "id", "question", "expected", "source_group", "rights_class"}
    ids, texts, groups = set(), set(), set()
    supported = ood = 0
    for row in rows:
        if type(row) is not dict or set(row) != expected_keys or row["schema"] != CASE_SCHEMA:
            raise EvaluationHold("CASE_SCHEMA")
        if (type(row["id"]) is not str or
                not re.fullmatch("[A-Za-z0-9_-]{1,48}", row["id"]) or row["id"] in ids):
            raise EvaluationHold("DUPLICATE_OR_INVALID_CASE_ID")
        ids.add(row["id"])
        text = row["question"]
        if type(text) is not str or not 8 <= len(text) <= 500:
            raise EvaluationHold("QUESTION_BOUNDS")
        normal = text.strip().casefold()
        if normal in texts:
            raise EvaluationHold("DUPLICATE_QUESTION")
        texts.add(normal)
        if type(row["expected"]) is not str or row["expected"] not in INTENTS | {"ABSTAIN"}:
            raise EvaluationHold("EXPECTED_INTENT")
        if (type(row["source_group"]) is not str or
                not re.fullmatch("[A-Za-z0-9_-]{1,40}", row["source_group"])):
            raise EvaluationHold("SOURCE_GROUP")
        groups.add(row["source_group"])
        if row["rights_class"] != "CALLER_DECLARED_EVAL_ONLY":
            raise EvaluationHold("RIGHTS_NOT_DECLARED")
        supported += row["expected"] != "ABSTAIN"
        ood += row["expected"] == "ABSTAIN"
    if supported < 10 or ood < 10 or len(groups) < 2:
        raise EvaluationHold("INCOMPLETE_DENOMINATORS")
    # Exact overlap is observable. Semantic and template leakage are not.
    train, development, _ = candidate_data(PROJECT)
    old_eval = [parse(x) for x in read_bounded(
        PROJECT / "data/synthetic_eval.jsonl", 30000).splitlines()]
    old_posthoc = [parse(x) for x in read_bounded(
        PROJECT / "data/posthoc_ood_v0.jsonl", 24000).splitlines()]
    seen = {row["text"].strip().casefold()
            for row in train + development + old_eval + old_posthoc}
    if texts & seen:
        raise EvaluationHold("PREVIOUSLY_SEEN_QUESTION_OVERLAP")
    return rows, {
        "manifest_sha256": sha256(manifest_raw).hexdigest(),
        "cases_sha256": m["cases_sha256"],
        "n": len(rows), "supported_n": supported, "ood_n": ood,
        "declared_source_groups": len(groups),
        "source_custody_verified": False,
        "rights_independently_verified": False
    }


def wilson_95(success: int, n: int):
    if n == 0:
        return None
    z = 1.959963984540054
    p = success / n
    a = 1 + z*z/n
    center = (p + z*z/(2*n))/a
    span = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/a
    return [max(0., center-span), min(1., center+span)]


def evaluate(manifest_file: Path, cases_file: Path):
    rows, provenance = validate(manifest_file, cases_file)
    raw = read_bounded(MODEL, 2000000)
    if sha256(raw).hexdigest() != MODEL_SHA:
        raise EvaluationHold("TRAINED_WEIGHT_BYTES_CHANGED")
    model = parse(raw)
    if (type(model) is not dict or
        model.get("schema") != "szl.khipu-yachay.open-set-router/v1" or
        model.get("production_qualified") is not False or
        model.get("historical_training") is not False or
        type(model.get("classes")) is not list or
        set(model["classes"]) != INTENTS | {"OUT_OF_SCOPE"}):
        raise EvaluationHold("MODEL_RUNTIME_SCHEMA")
    totals = Counter()
    groups: dict[str, Counter] = {}
    for row in rows:
        result = predict(row["question"], model)
        label = result["intent"]
        if label not in INTENTS | {"ABSTAIN"}:
            raise EvaluationHold("MODEL_OUTPUT_UNRECOGNIZED")
        bucket = groups.setdefault(row["source_group"], Counter())
        if row["expected"] == "ABSTAIN":
            totals["ood"] += 1
            bucket["ood"] += 1
            if label != "ABSTAIN":
                totals["ood_false_accept"] += 1
                bucket["ood_false_accept"] += 1
        else:
            totals["supported"] += 1
            bucket["supported"] += 1
            if label == row["expected"]:
                totals["supported_correct"] += 1
                bucket["supported_correct"] += 1
            if label == "ABSTAIN":
                totals["unnecessary_abstain"] += 1
    assert totals["supported"] == provenance["supported_n"]
    assert totals["ood"] == provenance["ood_n"]
    a, b = totals["supported"], totals["ood"]
    return {
        "schema": "szl.yachay.external-eval-descriptive-receipt/v1",
        "observed_utc": datetime.now(timezone.utc).isoformat(),
        "model_sha256": MODEL_SHA,
        "cases": provenance,
        "supported": {
            "n": a, "correct": totals["supported_correct"],
            "correct_rate": totals["supported_correct"]/a,
            "unnecessary_abstain": totals["unnecessary_abstain"],
            "wilson_95_conditional": wilson_95(totals["supported_correct"], a)
        },
        "out_of_domain": {
            "n": b, "false_accept": totals["ood_false_accept"],
            "false_accept_rate": totals["ood_false_accept"]/b,
            "wilson_95_conditional": wilson_95(totals["ood_false_accept"], b)
        },
        "source_group_counts": {
            k: {
                "supported_n": v["supported"], "supported_correct": v["supported_correct"],
                "ood_n": v["ood"], "ood_false_accept": v["ood_false_accept"]
            } for k,v in sorted(groups.items())
        },
        "caveat": "Conditional intervals describe the supplied cases only, not real-world accuracy.",
        "model_trained_this_run": False,
        "independent_evaluation_proved": False,
        "archaeological_accuracy_measured": False,
        "permission_independently_verified": False,
        "model_published": False, "production_qualified": False,
        "admission": "HOLD_FOR_EXTERNAL_REVIEW_AND_PROVENANCE"
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--cases", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        if args.out.exists() or args.out.is_symlink():
            raise EvaluationHold("RECEIPT_ALREADY_EXISTS")
        if not args.out.parent.is_dir():
            raise EvaluationHold("RECEIPT_PARENT_MISSING")
        result = evaluate(args.manifest, args.cases)
        data = (json.dumps(result, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False)+"\n").encode()
        with args.out.open("xb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        print(json.dumps({
            "state":result["admission"], "cases":result["cases"]["n"],
            "receipt_sha256":sha256(data).hexdigest(),
            "model_trained":False,"published":False
        },sort_keys=True))
        return 0  # evaluation completed; independent qualification did NOT.
    except (EvaluationHold, OSError) as e:
        print(json.dumps({
            "state":"UNAVAILABLE", "reason":str(e) if isinstance(e,EvaluationHold)
            else "IO_HOLD", "published":False
        },sort_keys=True))
        return 3


if __name__ == "__main__":
    sys.exit(main())
