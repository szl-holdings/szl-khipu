#!/usr/bin/env python3
"""Post-hoc bounded spatial sensitivity test of OKR top-cord arithmetic.

For each eligible khipu, cyclically rotate observed *known* direct-pendant
values separately within each primary-cord sequence, and do not cross an
unknown-value gap. Preserve the complete relative order of each run,
original top cord values, all cord positions and candidate group structure.
The original R2 search is then rerun with exactly the shifted values.

This is intentionally exploratory: this spatial null was chosen after viewing
the discovery result, cannot establish causation/decipherment and is not
an independently blinded archaeological validation.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "szl_khipu/okr_khipu.py"
SCHEMA = "szl.okr.spatial-shift-posthoc/v1"
DOMAIN = b"szl.okr.spatial-shift-posthoc/v1\x00"
SEED = 2026
TRIALS = 1000
MAX_TRIALS = 2000
SOURCE_HEAD = "d5ce329722b60f6d87058936dc0fe795193bda3c"


class Hold(ValueError):
    """Refuse invalid source/data/simulation scope."""


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("ascii")


def _engine():
    spec = importlib.util.spec_from_file_location("szl_okr_spatial_audit_engine", ENGINE)
    if spec is None or spec.loader is None:
        raise Hold("ENGINE_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def is_named_provenance(record: dict) -> bool:
    """Exclude both empty and explicitly unknown un-normalized metadata."""
    if not isinstance(record, dict):
        raise Hold("KHIPU_RECORD_NOT_OBJECT")
    value = record.get("provenance")
    if not isinstance(value, str):
        raise Hold("KHIPU_PROVENANCE_INVALID")
    return value.strip().casefold() not in {"", "unknown", "unspecified"}


def shift_runs(record: dict, structure) -> tuple[tuple[int, ...], ...]:
    """Known direct-pendant runs, ordered by ordinal; unknown is a hard barrier."""
    groups: dict[int, list[int]] = defaultdict(list)
    for i, cord in enumerate(record["cords"]):
        if structure.roles[i] == "pendant" and cord.get("parent_kind") == "primary":
            groups[cord["parent"]].append(i)
    runs = []
    for primary in sorted(groups):
        indexes = groups[primary]
        indexes.sort(key=lambda i: (record["cords"][i]["ordinal"], structure.ids[i]))
        segment = []
        for idx in indexes:
            if structure.known[idx]:
                segment.append(idx)
            else:
                if len(segment) > 1:
                    runs.append(tuple(segment))
                segment = []
        if len(segment) > 1:
            runs.append(tuple(segment))
    return tuple(runs)


def shifted_values(original: tuple[int, ...], runs: tuple[tuple[int, ...], ...],
                   rng: random.Random) -> list[int]:
    """Only cyclic permutations; identity rotation is included without bias."""
    values = list(original)
    for run in runs:
        if len(run) < 2 or len(set(run)) != len(run):
            raise Hold("SHIFT_RUN_INVALID")
        offset = rng.randrange(len(run))
        for j, idx in enumerate(run):
            values[idx] = original[run[(j + offset) % len(run)]]
    return values


def _aggregate(observed: int, eligible: int, simulations: list[int]) -> dict:
    count = len(simulations)
    mean = sum(simulations) / count
    variance = sum((v - mean) ** 2 for v in simulations) / (count - 1)
    return {
        "eligible": eligible,
        "observed_r2": observed,
        "null_mean": round(mean, 4),
        "null_sd_sample": round(math.sqrt(variance), 4),
        "null_max": max(simulations),
        "observed_over_null": round(observed / mean, 4) if mean > 0 else None,
        "monte_carlo_p_upper": round(
            (1 + sum(v >= observed for v in simulations)) / (count + 1), 6
        ),
        "simulation_trials": count,
    }


def audit(*, trials: int = TRIALS, seed: int = SEED) -> dict:
    if type(trials) is not int or not 2 <= trials <= MAX_TRIALS:
        raise Hold("SIMULATION_BUDGET_INVALID")
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise Hold("RANDOM_SEED_INVALID")
    engine = _engine()
    corpus = engine.load_corpus()
    if corpus.get("sha256") != engine.CORPUS_SHA256:
        raise Hold("REQUIRED_SOURCE_DIGEST_MISMATCH")
    if len(corpus["khipus"]) != 619:
        raise Hold("CORPUS_POPULATION_UNEXPECTED")
    unknown_provenance = sum(
        not is_named_provenance(record) for record in corpus["khipus"]
    )
    if unknown_provenance != 221:
        raise Hold("PROVENANCE_COVERAGE_CHANGED")

    totals = [0] * trials
    named_totals = [0] * trials
    eligible = named_eligible = observed = named_observed = 0
    shiftable = 0
    for record in corpus["khipus"]:
        structure = engine._Structure(record)
        if not structure.candidates()["R2"]:
            continue
        eligible += 1
        original = tuple(engine._value_vector(structure))
        observed_count = structure.count(original)["R2"]
        observed += observed_count
        named = is_named_provenance(record)
        if named:
            named_eligible += 1
            named_observed += observed_count
        runs = shift_runs(record, structure)
        if any(len({original[i] for i in group}) > 1 for group in runs):
            shiftable += 1

        # No dependence on input order beyond the pinned immutable corpus.
        key = hashlib.sha256(
            f"szl.okr.cyclic-shift-posthoc.v1:{seed}:{record['id']}".encode("ascii")
        ).digest()
        rng = random.Random(int.from_bytes(key[:8], "big"))
        for t in range(trials):
            vals = shifted_values(original, runs, rng)
            score = structure.count(vals)["R2"]
            totals[t] += score
            if named:
                named_totals[t] += score

    # A 0-trial or empty cohort must not be reported as a positive evaluation.
    if eligible != 35 or named_eligible != 21 or not shiftable:
        raise Hold("SOURCE_COHORT_CHANGED")
    if observed != 54 or named_observed != 29:
        raise Hold("OBSERVED_BASELINE_CHANGED")
    core = {
        "schema": SCHEMA,
        "status": "POST_HOC_EXPLORATORY_CONTROL_ONLY",
        "source_branch_snapshot": SOURCE_HEAD,
        "upstream_okr_revision": engine.OKR_COMMIT,
        "input_corpus_sha256": engine.CORPUS_SHA256,
        "seed": seed,
        "trials": trials,
        "null_design": (
            "independent uniform cyclic shifts of ordered known primary-attached "
            "pendant values within each primary, split at unknown-value gaps; "
            "top values, cord geometry, group boundaries and null identity rotations unchanged"
        ),
        "all_eligible": _aggregate(observed, eligible, totals),
        "specified_provenance_eligible": _aggregate(
            named_observed, named_eligible, named_totals
        ),
        "n_pendant_shiftable_records": shiftable,
        "khipus_all": len(corpus["khipus"]),
        "provenance_blank_or_unknown_count": unknown_provenance,
        "preregistered": False,
        "prospective_heldout": False,
        "independent_research_lab_replication": False,
        "historical_khipu_decipherment": False,
        "historical_intent_established": False,
        "HJO_mathematical_theorem_proved": False,
        "new_model_trained": False,
        "signature_verified": False,
        "production_qualification": "NOT_ASSESSED",
    }
    return {**core, "sha256": hashlib.sha256(DOMAIN + canonical(core)).hexdigest()}


def render(report: dict) -> bytes:
    return (json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    exclusive = parser.add_mutually_exclusive_group(required=True)
    exclusive.add_argument("--write", type=Path)
    exclusive.add_argument("--check", type=Path)
    args = parser.parse_args()
    try:
        if args.write and args.write.exists():
            raise Hold("REFUSE_OVERWRITE")
        raw = render(audit())
        if args.write:
            # No overwrite, symlink following or best-effort normalization.
            with args.write.open("xb") as target:
                target.write(raw)
            status = "WRITTEN"
        else:
            if args.check.is_symlink() or not args.check.is_file():
                raise Hold("RECEIPT_UNAVAILABLE")
            if args.check.read_bytes() != raw:
                raise Hold("RECEIPT_REPLAY_MISMATCH")
            status = "REPLAY_MATCH"
        print(json.dumps({
            "status": status, "sha256": hashlib.sha256(raw).hexdigest(),
            "report_digest": json.loads(raw)["sha256"],
            "source_input": SOURCE_HEAD,
        }, sort_keys=True))
        return 0
    except (Hold, OSError) as error:
        print(json.dumps({
            "status": "HOLD",
            "reason": str(error) if isinstance(error, Hold) else "FILE_IO_FAILED",
        }, sort_keys=True))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
