#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Build or re-check the sealed HJO Loom finite certificate.

    python research/hjo_loom/build_certificate.py --write research/hjo_loom/hjo_certificate_v1.json
    python research/hjo_loom/build_certificate.py --check research/hjo_loom/hjo_certificate_v1.json

--check recomputes every number from scratch and requires byte-identical output.
The certificate replays PUBLISHED theorems on finite ranges; it proves nothing new.
"""
import argparse
import json
import math
import importlib.util
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Load the module by path, not through the szl_khipu package: the package's
# __init__ imports numpy, and this check needs only the standard library.
_SPEC = importlib.util.spec_from_file_location("hjo_loom", ROOT / "szl_khipu" / "hjo_loom.py")
h = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = h  # dataclasses resolve string annotations through sys.modules
_SPEC.loader.exec_module(h)

SCHEMA = "szl.khipu.hjo-certificate/v1"
PAIRS = [(a, s - a) for s in range(5, 14) for a in range(2, s)
         if a < s - a and math.gcd(a, s - a) == 1]
V1_DEGREE = 40
QUOT_PLAN = [  # (a, b, rank, field, colength_max)
    (2, 3, 1, 2, 6), (2, 3, 1, 3, 6), (2, 3, 2, 2, 4), (2, 3, 2, 3, 3),
    (2, 5, 1, 2, 5), (2, 5, 1, 3, 5), (2, 5, 2, 2, 3), (2, 5, 2, 3, 3),
    (3, 4, 1, 2, 5), (3, 4, 1, 3, 5), (3, 4, 2, 2, 3), (3, 4, 2, 3, 3),
    (3, 5, 1, 2, 5), (3, 5, 1, 3, 4), (3, 5, 2, 2, 3),
    (2, 7, 1, 2, 5), (2, 7, 2, 2, 2),
    (4, 5, 1, 2, 4), (4, 5, 1, 3, 3), (4, 5, 2, 2, 1),
    (3, 7, 1, 2, 4), (3, 7, 2, 2, 1),
    (4, 7, 1, 2, 3), (5, 6, 1, 2, 3),
]
NIL_PLAN = [(2, 3, 2, 4), (2, 3, 3, 3), (3, 4, 2, 4), (3, 4, 3, 3), (2, 5, 2, 4), (4, 5, 2, 3)]


def build() -> dict:
    v1, v2 = [], []
    for a, b in PAIRS:
        z, p = h.z_series(a, b, V1_DEGREE), h.p_series(a, b, V1_DEGREE)
        if z != p:
            raise h.HjoHold(f"V1_MISMATCH_{a}_{b}")
        v1.append({"pair": [a, b], "degree": V1_DEGREE, "coefficients": z})
        delta = h.gap_poset(a, b).delta
        for rank in ((1, 2, 3) if delta <= 6 else (1, 2)):
            f = h.f_polynomial(a, b, rank)
            D = min(h.MAX_DEGREE, len(f) - 1 + 4)
            cyl = h.cylindric_series(h.balanced_profile(a, b), rank, D)
            if h._mul(h._poch(rank), cyl, D) != (f + [0] * (D + 1))[: D + 1]:
                raise h.HjoHold(f"V2_MISMATCH_{a}_{b}_{rank}")
            if sum(f) != h.rational_catalan(a, b) ** rank:
                raise h.HjoHold(f"V4_MISMATCH_{a}_{b}_{rank}")
            v2.append({"pair": [a, b], "rank": rank, "checked_through_degree": D,
                       "F_N": f, "F_N_at_1": sum(f), "catalan": h.rational_catalan(a, b)})
    v5 = []
    for a, b, rank, field, mm in QUOT_PLAN:
        formula = h.quot_formula_counts(a, b, rank, field, mm)
        brute = h.quot_bruteforce_counts(a, b, rank, field, mm, budget=6_000_000)
        if formula != brute:
            raise h.HjoHold(f"V5_MISMATCH_{a}_{b}_{rank}_{field}")
        v5.append({"pair": [a, b], "rank": rank, "field": field,
                   "colengths": list(range(mm + 1)), "submodule_counts": brute})
    v6 = []
    for a, b, field, n in NIL_PLAN:
        terms = h.nilpotent_pair_terms(a, b, field, n)
        partial = sum(terms)
        limit = h.groupoid_prediction(a, b, field)
        if not float(partial) < limit:
            raise h.HjoHold("V6_INCONSISTENT")
        v6.append({"pair": [a, b], "field": field,
                   "terms": [f"{t.numerator}/{t.denominator}" for t in terms],
                   "partial_sum": f"{partial.numerator}/{partial.denominator}",
                   "predicted_limit_float": round(limit, 12),
                   "status": "CONSISTENT_NOT_VERIFIED"})
    golden = {
        "F_1(4,5)": h.f_polynomial(4, 5, 1) == h.GOLDEN["F_1(4,5)"],
        "F_2(4,5)": h.f_polynomial(4, 5, 2) == h.GOLDEN["F_2(4,5)"],
        "F_2(2,3)": h.f_polynomial(2, 3, 2) == h.GOLDEN["F_2(2,3)"],
        "profile(5,7)": list(h.balanced_profile(5, 7)) == h.GOLDEN["profile(5,7)"],
    }
    if not all(golden.values()):
        raise h.HjoHold("V3_GOLDEN_MISMATCH")
    record = {
        "schema": SCHEMA,
        "statements": {
            "V1": "Z_{a,b}(q) == P_{a,b}(q) coefficientwise (HLO Cor 1.2 / HJO Conj 1.7)",
            "V2": "F_N(q) == (q;q)_N C_{c,<=N}(q) (HLO Thm 1.1), cylinders counted directly",
            "V3": "published golden values (HLO §1.2, §10) reproduced",
            "V4": "#order filters == rational Catalan; F_N(1) == Cat(a,b)^N",
            "V5": "brute-force #R-submodules of F_q[[T]]^N of colength m == HJO Thm 1.2 at L=q",
            "V6": "partial groupoid sums of nilpotent pairs < HJO Thm 1.4 limit (consistency only)",
        },
        "pairs": [list(p) for p in PAIRS],
        "V1": v1, "V2": v2, "V3": golden, "V5": v5, "V6": v6,
        "sources": {"paper": h.PAPER, "hjo": h.HJO_PAPER, "lean_repo": h.LEAN_REPO,
                    "lean_revision_observed": h.LEAN_REVISION_OBSERVED},
        "lean_certificate_replayed": False,
        "new_theorem_proved": False,
        "finite_check_only": True,
        "historical_claim": "NOT_ESTABLISHED",
        "signature_verified": False,
    }
    return h.seal(record)


def render(record: dict) -> bytes:
    return (json.dumps(record, indent=1, sort_keys=True, ensure_ascii=True) + "\n").encode("ascii")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", type=Path)
    g.add_argument("--check", type=Path)
    args = ap.parse_args()
    start = time.time()
    if args.write and args.write.exists():
        print(json.dumps({"status": "HOLD", "reason": "REFUSE_OVERWRITE"}))
        return 3
    body = render(build())
    if args.write:
        args.write.write_bytes(body)
        status = "WRITTEN"
    else:
        if args.check.read_bytes() != body:
            print(json.dumps({"status": "HOLD", "reason": "CERTIFICATE_REPLAY_MISMATCH"}))
            return 3
        status = "REPLAY_MATCH"
    sha = json.loads(body)["sha256"]
    print(json.dumps({"status": status, "sha256": sha, "seconds": round(time.time() - start, 1)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
