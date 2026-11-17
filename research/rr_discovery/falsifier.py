"""Finite Conjecture Crucible — exact, bounded falsifier for classical RR cases.

This is NOT an HJO (a,b) identity engine, infinite proof, archaeological khipu
model, or neural learner. Two independent first-party recurrences triangulate
the expected finite coefficients; a third evaluates a user-proposed modular
partition product. A single mismatch is a falsifying finite counterexample.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import re
from functools import lru_cache

SCHEMA = "szl.khipu.finite-conjecture-crucible/v1"
DOMAIN = b"szl.khipu.finite-conjecture-crucible/v1\x00"
MAX_DEGREE = 256
MAX_MODULUS = 12
MAX_RESIDUES = 4
MAX_SAMPLES = 5
REFERENCE_CASES = {"RR1": 1, "RR2": 2}


class Hold(ValueError):
    """Reject unbounded, malformed or untrustworthy mathematical inputs."""


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def parse_residues(raw: str) -> tuple[int, ...]:
    if type(raw) is not str or len(raw) > 16:
        raise Hold("RESIDUES_FORMAT_INVALID")
    if re.fullmatch(r"[1-9][0-9]?(?:,[1-9][0-9]?){0,3}", raw) is None:
        raise Hold("RESIDUES_FORMAT_INVALID")
    classes = tuple(int(part) for part in raw.split(","))
    if tuple(sorted(set(classes))) != classes:
        raise Hold("RESIDUE_CLASSES_NOT_STRICTLY_INCREASING")
    return classes


def _validate(case: str, modulus: int, residues: tuple[int, ...], limit: int) -> None:
    if type(case) is not str or case not in REFERENCE_CASES:
        raise Hold("UNKNOWN_CLASSICAL_IDENTITY")
    if type(modulus) is not int or not 2 <= modulus <= MAX_MODULUS:
        raise Hold("MODULUS_BOUND_INVALID")
    if (
        type(residues) is not tuple
        or not 1 <= len(residues) <= MAX_RESIDUES
        or any(type(r) is not int or not 1 <= r < modulus for r in residues)
        or tuple(sorted(set(residues))) != residues
    ):
        raise Hold("RESIDUE_CLASSES_INVALID")
    if type(limit) is not int or not 1 <= limit <= MAX_DEGREE:
        raise Hold("FINITE_DEGREE_BOUND_INVALID")


def qseries_coefficients(case: str, limit: int) -> tuple[int, ...]:
    """Classical exact sum over k of q^(k² or k²+k) / (q;q)_k."""
    if case not in REFERENCE_CASES or type(limit) is not int or not 0 <= limit <= MAX_DEGREE:
        raise Hold("QSERIES_INPUT_INVALID")
    out = [0] * (limit + 1)
    inverse_pochhammer = [1] + [0] * limit
    for k in range(math.isqrt(limit) + 1):
        if k:
            # Coefficients of 1/((1-q)...(1-q^k)), using exact integer DP.
            for degree in range(k, limit + 1):
                inverse_pochhammer[degree] += inverse_pochhammer[degree - k]
        shift = k*k + (k if case == "RR2" else 0)
        if shift > limit:
            break
        for degree in range(limit - shift + 1):
            out[degree + shift] += inverse_pochhammer[degree]
    return tuple(out)


@lru_cache(maxsize=None)
def _gap(n: int, smallest: int) -> int:
    if n == 0:
        return 1
    if n < smallest:
        return 0
    return _gap(n, smallest + 1) + _gap(n - smallest, smallest + 2)


def gap_coefficients(case: str, limit: int) -> tuple[int, ...]:
    """Independent finite recurrence: parts differ by >=2."""
    if case not in REFERENCE_CASES or type(limit) is not int or not 0 <= limit <= MAX_DEGREE:
        raise Hold("GAP_INPUT_INVALID")
    minimum = REFERENCE_CASES[case]
    return tuple(_gap(n, minimum) for n in range(limit + 1))


def modular_coefficients(modulus: int, residues: tuple[int, ...], limit: int) -> tuple[int, ...]:
    """Independent unrestricted modular-product coefficient computation."""
    _validate("RR1", modulus, residues, limit)
    out = [1] + [0] * limit
    for part in range(1, limit + 1):
        if part % modulus in residues:
            for total in range(part, limit + 1):
                out[total] += out[total - part]
    return tuple(out)


def _gap_examples(n: int, minimum: int):
    if n == 0:
        yield []
        return
    for part in range(minimum, n + 1):
        for remaining in _gap_examples(n - part, part + 2):
            yield [part, *remaining]


def _mod_examples(n: int, minimum: int, modulus: int, residues: tuple[int, ...]):
    if n == 0:
        yield []
        return
    for part in range(minimum, n + 1):
        if part % modulus in residues:
            for remaining in _mod_examples(n - part, part, modulus, residues):
                yield [part, *remaining]


def falsify(
    case: str = "RR1", modulus: int = 5,
    residues: tuple[int, ...] = (1, 4), limit: int = 128,
) -> dict:
    """Check a *user-proposed* modular partition identity through bounded n.

    Match means only 'not refuted for n <= limit'. Mismatch with an integer
    counterexample refutes the proposed all-n equality, not HJO geometry.
    """
    _validate(case, modulus, residues, limit)
    qseries = qseries_coefficients(case, limit)
    gap = gap_coefficients(case, limit)
    if qseries != gap:
        first = next(i for i in range(limit + 1) if qseries[i] != gap[i])
        raise Hold(f"INDEPENDENT_ORACLE_DISAGREEMENT_N_{first}")
    target = modular_coefficients(modulus, residues, limit)
    first = next((i for i in range(limit + 1) if target[i] != gap[i]), None)
    counterexample = None
    if first is not None:
        counterexample = {
            "degree": first,
            "expected_gap_and_qseries_count": gap[first],
            "proposed_product_count": target[first],
        }
        if first <= 24:
            counterexample["gap_partition_examples_ascending"] = list(
                itertools.islice(_gap_examples(first, REFERENCE_CASES[case]), MAX_SAMPLES)
            )
            counterexample["proposed_modular_partition_examples_ascending"] = list(
                itertools.islice(_mod_examples(first, 1, modulus, residues), MAX_SAMPLES)
            )
            counterexample["examples_are_exhaustive"] = (
                gap[first] <= MAX_SAMPLES and target[first] <= MAX_SAMPLES
            )
    core = {
        "schema": SCHEMA,
        "case": case,
        "proposed_modulus": modulus,
        "proposed_residues": list(residues),
        "finite_limit": limit,
        "coefficients_checked": limit + 1,
        "status": "FINITE_COUNTEREXAMPLE" if first is not None else "FINITE_MATCH_NOT_A_PROOF",
        "first_counterexample": counterexample,
        "qseries_and_gap_oracles_agree": True,
        "two_independent_reference_methods": [
            "classical q-series sum / finite Pochhammer DP",
            "gap >= 2 partition recursion",
        ],
        "proposed_modular_product_sha256": hashlib.sha256(canonical(target)).hexdigest(),
        "reference_coefficients_sha256": hashlib.sha256(canonical(gap)).hexdigest(),
        "historical_khipu_claim": "NOT_ESTABLISHED",
        "hjo_general_torus_knot_theorem_tested": False,
        "lean_proof_replayed": False,
        "infinite_identity_proved_here": False,
        "model_training_performed": False,
        "independent_replication": False,
        "signature_verified": False,
        "production_qualification": "NOT_ASSESSED",
    }
    return {**core, "sha256": hashlib.sha256(DOMAIN + canonical(core)).hexdigest()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=list(REFERENCE_CASES), default="RR1")
    parser.add_argument("--modulus", type=int, default=5)
    parser.add_argument("--residues", default="1,4")
    parser.add_argument("--limit", type=int, default=128)
    args = parser.parse_args()
    try:
        report = falsify(args.case, args.modulus, parse_residues(args.residues), args.limit)
        print(json.dumps(report, sort_keys=True, indent=2))
        return 0
    except Hold as exc:
        print(json.dumps({"status": "HOLD", "reason": str(exc)}, sort_keys=True))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
