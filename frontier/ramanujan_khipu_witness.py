#!/usr/bin/env python3
"""Bounded, exact Rogers--Ramanujan coefficient checks with digital cord witnesses.

Research-only: finite checks are NOT an infinite proof or ancient khipu decoding.
No filesystem writes, network, model loading, or provider side effects.
"""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache

SCHEMA = "szl.khipu.rr-finite-witness/v1"
DOMAIN = b"szl.khipu.rr-finite-witness/v1\0"
SOURCE = "https://arxiv.org/abs/2609.20567v2"
MAX_N = 128


class EvidenceHold(ValueError):
    """Invalid, contradictory or insufficient evidence; never silently correct it."""


def _bound(value: int) -> int:
    if type(value) is not int or not 0 <= value <= MAX_N:
        raise EvidenceHold("INVALID_FINITE_BOUND")
    return value


@lru_cache(maxsize=None)
def _gap_partitions(n: int, least: int) -> int:
    """Number of n-partitions with parts >= least and pairwise gaps >= 2."""
    if n == 0:
        return 1
    if n < least:
        return 0
    # Exclude least; or include it, then require all remaining parts >= least+2.
    return _gap_partitions(n, least + 1) + _gap_partitions(n - least, least + 2)


def gap_counts(limit: int, min_part: int) -> list[int]:
    _bound(limit)
    if type(min_part) is not int or min_part not in (1, 2):
        raise EvidenceHold("INVALID_MIN_PART")
    return [_gap_partitions(n, min_part) for n in range(limit + 1)]


def residue_counts(limit: int, residues: tuple[int, int]) -> list[int]:
    _bound(limit)
    if (type(residues) is not tuple or len(residues) != 2 or
            any(type(x) is not int or x not in (1, 2, 3, 4) for x in residues) or
            residues[0] >= residues[1]):
        raise EvidenceHold("INVALID_RESIDUE_CLASSES")
    ways = [1] + [0] * limit
    for part in range(1, limit + 1):
        if part % 5 in residues:
            for n in range(part, limit + 1):
                ways[n] += ways[n - part]
    return ways


def digital_cord(value: int) -> dict:
    """Lossless decimal place-value sketch, NOT a transcription of historic knots.

    Explicit present distinguishes an observed zero from an absent record.
    Digits are nonzero [decimal_exponent, digit] pairs, highest first.
    """
    if type(value) is not int or value < 0:
        raise EvidenceHold("INVALID_COUNT")
    digits = []
    for exp, digit in enumerate(str(value)[::-1]):
        if digit != "0":
            digits.append([exp, int(digit)])
    return {"present": True, "digits": digits[::-1]}


def read_digital_cord(cord: object) -> int:
    if type(cord) is not dict or set(cord) != {"present", "digits"}:
        raise EvidenceHold("INVALID_DIGITAL_CORD")
    if cord["present"] is not True:
        raise EvidenceHold("MISSING_NOT_ZERO")
    digits = cord["digits"]
    if type(digits) is not list or len(digits) > 100:
        raise EvidenceHold("INVALID_DIGITAL_CORD")
    last_exp = 101
    value = 0
    for cell in digits:
        if (type(cell) is not list or len(cell) != 2 or
                type(cell[0]) is not int or type(cell[1]) is not int):
            raise EvidenceHold("INVALID_DIGITAL_CORD")
        exp, digit = cell
        if not (0 <= exp < last_exp and 1 <= digit <= 9):
            raise EvidenceHold("INVALID_DIGITAL_CORD")
        value += digit * 10 ** exp
        last_exp = exp
    return value


def canonical_bytes(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def build_witness(limit: int = 64) -> dict:
    _bound(limit)
    modes = (
        ("RR1", 1, (1, 4)),
        ("RR2", 2, (2, 3)),
    )
    rows = []
    for label, min_part, residues in modes:
        left = gap_counts(limit, min_part)
        right = residue_counts(limit, residues)
        if left != right:
            raise EvidenceHold("FINITE_IDENTITY_MISMATCH")
        rows.append({
            "identity": label,
            "min_part": min_part,
            "residues_mod_5": list(residues),
            "coefficients": [
                {"n": n, "gap_count": left[n], "residue_count": right[n],
                 "cord": digital_cord(left[n])} for n in range(limit + 1)
            ],
        })
    payload = {
        "schema": SCHEMA,
        "source": SOURCE,
        "max_coefficient": limit,
        "status": "FINITE_MATCH",
        "proof_of_infinite_identity": False,
        "claims_historical_khipu_decipherment": False,
        "signature_verified": False,
        "model_qualification": "NOT_ASSESSED",
        "scope": "exact coefficient identities 0..max_coefficient; digital cords are modern abstractions",
        "checks": rows,
    }
    return {**payload, "sha256": hashlib.sha256(DOMAIN + canonical_bytes(payload)).hexdigest()}


def verify_witness(manifest: object) -> bool:
    if type(manifest) is not dict or type(manifest.get("max_coefficient")) is not int:
        raise EvidenceHold("INVALID_WITNESS")
    expected = build_witness(manifest["max_coefficient"])
    if canonical_bytes(manifest) != canonical_bytes(expected):
        raise EvidenceHold("WITNESS_NOT_REPRODUCIBLE")
    return True


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=64, help="exact finite bound (0..128)")
    args = parser.parse_args()
    try:
        result = build_witness(args.n)
        verify_witness(result)
    except EvidenceHold as exc:
        print(json.dumps({"schema": SCHEMA, "status": "HOLD", "reason": str(exc)}, sort_keys=True))
        return 3
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
