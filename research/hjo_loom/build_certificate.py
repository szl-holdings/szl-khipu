#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Build or re-check the sealed HJO Loom finite certificates.

    python research/hjo_loom/build_certificate.py --write research/hjo_loom/hjo_certificate_v1.json
    python research/hjo_loom/build_certificate.py --check research/hjo_loom/hjo_certificate_v1.json
    python research/hjo_loom/build_certificate.py --v2 --jobs 4 --check research/hjo_loom/hjo_certificate_v2.json

--check recomputes every number from scratch and requires byte-identical output.
--v2 selects the multi-field census (V7) and q-polynomial recovery (V8); --jobs
only spreads its series over processes and does not change a byte of the output.
The certificates replay PUBLISHED theorems on finite ranges; they prove nothing new.
"""
import argparse
import json
import math
import importlib.util
import multiprocessing
import sys
import time
from fractions import Fraction
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

SCHEMA_V2 = "szl.khipu.hjo-certificate/v2"
CENSUS_SERIES = list(dict.fromkeys((a, b, rank) for a, b, rank, _q, _m in QUOT_PLAN))
# Recursion steps per (pair, rank, field) series: half of V5's cap, so that all
# 112 series fit in about 25 minutes on a 4-vCPU container (see METHOD.md).
CENSUS_WORK_CAP = 3_000_000
CENSUS_COLENGTH_CEILING = 8
FORMULA_EXTRA_POINTS = 3


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


def census_row(a: int, b: int, rank: int, q: int) -> dict:
    """V7 for one series: brute force over GF(q) as far as the work cap allows,
    against the formula at the same q, colength by colength."""
    run = h.quot_bruteforce_census(a, b, rank, q, CENSUS_COLENGTH_CEILING, budget=CENSUS_WORK_CAP)
    counts = run["counts"]
    if not counts:
        raise h.HjoHold(f"V7_NO_COLENGTH_COMPLETED_{a}_{b}_{rank}_{q}")
    formula = h.quot_formula_counts(a, b, rank, q, len(counts) - 1)
    agree = [x == y for x, y in zip(counts, formula)]
    if not all(agree):
        raise h.HjoHold(f"V7_MISMATCH_{a}_{b}_{rank}_{q}")
    return {"pair": [a, b], "rank": rank, "field": q, "colength_max": len(counts) - 1,
            "bruteforce": counts, "formula": formula, "agree": agree,
            "stop": run["stop"], "work_steps": run["work_steps"],
            "cumulative_work_steps": run["cumulative_work"]}


def _census_task(indexed: tuple[int, tuple[int, int, int, int]]) -> tuple[int, dict, float]:
    start = time.perf_counter()
    row = census_row(*indexed[1])
    return indexed[0], row, time.perf_counter() - start


def recovery_rows(a: int, b: int, rank: int, census: list[dict]) -> list[dict]:
    """V8 for one (pair, rank) from its V7 rows, one per field."""
    if sorted(row["field"] for row in census) != sorted(h.CENSUS_FIELDS):
        raise h.HjoHold(f"V8_CENSUS_INCOMPLETE_{a}_{b}_{rank}")
    square = rank * rank * h.gap_poset(a, b).delta
    top = max(row["colength_max"] for row in census)
    polys = h.quot_formula_polynomials(a, b, rank, top, extra=FORMULA_EXTRA_POINTS)
    formula_points = square + (rank - 1) * top + 1 + FORMULA_EXTRA_POINTS
    out = []
    for m, poly in enumerate(polys):
        reached = [row for row in census if row["colength_max"] >= m]
        if any(h._eval(poly, Fraction(row["field"])) != row["formula"][m] for row in reached):
            raise h.HjoHold(f"V8_POLYNOMIAL_OFF_FORMULA_{a}_{b}_{rank}_{m}")
        # Interpolate the brute-force counts alone: the formula only says how many
        # points are needed (its degree) and what the result must equal.
        points = [(row["field"], row["bruteforce"][m]) for row in reached]
        degree = len(poly) - 1
        recovered = len(points) >= degree + 1
        interpolant = None
        if recovered:
            fit = h._interpolate(points)
            if fit != poly:
                raise h.HjoHold(f"V8_INTERPOLANT_MISMATCH_{a}_{b}_{rank}_{m}")
            interpolant = [int(c) for c in fit]
        out.append({"pair": [a, b], "rank": rank, "colength": m,
                    "formula_polynomial": poly, "degree": degree,
                    "degree_bound": square + (rank - 1) * m, "formula_points": formula_points,
                    "bruteforce_fields": [q for q, _ in points], "bruteforce_points": len(points),
                    "bruteforce_interpolant": interpolant,
                    "status": "RECOVERED" if recovered else "UNDERDETERMINED",
                    "extra_checks": max(0, len(points) - degree - 1),
                    "points_short": max(0, degree + 1 - len(points))})
    return out


def build_v2(jobs: int = 1, verbose: bool = False) -> dict:
    tasks = [(a, b, rank, q) for a, b, rank in CENSUS_SERIES for q in h.CENSUS_FIELDS]
    # Costliest series first so a pool does not end on one long tail; the rows
    # are put back in plan order, so the output does not depend on jobs.
    order = sorted(range(len(tasks)), key=lambda i: (-tasks[i][2], -h.gap_poset(*tasks[i][:2]).delta,
                                                     -tasks[i][3], i))
    indexed = [(i, tasks[i]) for i in order]
    rows: dict[int, dict] = {}

    def collect(results) -> None:
        for k, (i, row, seconds) in enumerate(results, 1):
            rows[i] = row
            if verbose:   # stderr only: timings never enter the certificate
                print(f"[{k}/{len(tasks)}] {tuple(row['pair'])} N={row['rank']} q={row['field']} "
                      f"colengths 0..{row['colength_max']} {row['stop']} steps={row['work_steps']} "
                      f"{seconds:.1f}s", file=sys.stderr, flush=True)

    if jobs > 1:
        with multiprocessing.Pool(jobs) as pool:
            collect(pool.imap_unordered(_census_task, indexed, chunksize=1))
    else:
        collect(map(_census_task, indexed))
    v7 = [rows[i] for i in range(len(tasks))]
    v8 = []
    for a, b, rank in CENSUS_SERIES:
        v8 += recovery_rows(a, b, rank, [r for r in v7 if r["pair"] == [a, b] and r["rank"] == rank])
    fields = [h.galois_field(q) for q in h.CENSUS_FIELDS]
    record = {
        "schema": SCHEMA_V2,
        "statements": {
            "V7": "brute-force #R-submodules of F_q[[T]]^N of colength m == HJO Thm 1.2 at L=q, "
                  "for every prime power q <= 9 and every (pair, rank) of V5",
            "V8": "the colength-m count of HJO Thm 1.2 as a polynomial in q, interpolated exactly "
                  "from the formula at integer L; RECOVERED when the brute-force counts alone, at "
                  "prime powers, number at least degree+1 and interpolate to the same polynomial",
        },
        "fields": [{"q": f.q, "p": f.p, "modulus_low_to_high": list(f.modulus)} for f in fields],
        "census": {
            "series": [list(s) for s in CENSUS_SERIES],
            "fields": list(h.CENSUS_FIELDS),
            "work_cap_steps_per_series": CENSUS_WORK_CAP,
            "work_unit": "one call of the echelon recursion, the unit of V5's budget",
            "colength_ceiling": CENSUS_COLENGTH_CEILING,
            "over_cap_colength": "abandoned and not recorded; no partial count is kept",
        },
        "interpolation": {
            "formula_nodes": "L = 2, 3, ..., formula_points + 1",
            "degree_bound": "N^2 delta + (N-1) m",
            "formula_extra_points": FORMULA_EXTRA_POINTS,
        },
        "V7": v7,
        "V8": v8,
        "summary": {
            "series": len(v7),
            "colength_counts_compared": sum(len(r["bruteforce"]) for r in v7),
            "stopped_by_work_cap": sum(r["stop"] == "WORK_CAP" for r in v7),
            "stopped_by_colength_ceiling": sum(r["stop"] == "COLENGTH_CEILING" for r in v7),
            "recovered": sum(r["status"] == "RECOVERED" for r in v8),
            "underdetermined": sum(r["status"] == "UNDERDETERMINED" for r in v8),
        },
        "sources": {"paper": h.PAPER, "hjo": h.HJO_PAPER, "lean_repo": h.LEAN_REPO,
                    "lean_revision_observed": h.LEAN_REVISION_OBSERVED},
        "lean_certificate_replayed": False,
        "new_theorem_proved": False,
        "finite_check_only": True,
        "independent_replication": False,
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
    ap.add_argument("--v2", action="store_true", help="the V7/V8 census certificate")
    ap.add_argument("--jobs", type=int, default=1, help="worker processes for --v2")
    args = ap.parse_args()
    start = time.time()
    if args.jobs < 1:
        print(json.dumps({"status": "HOLD", "reason": "JOBS_INVALID"}))
        return 3
    if args.write and args.write.exists():
        print(json.dumps({"status": "HOLD", "reason": "REFUSE_OVERWRITE"}))
        return 3
    if args.check:
        # The rebuilt bytes always declare `expected`; a file that does not cannot
        # match them, so refuse it before a rebuild that can take many minutes.
        expected = SCHEMA_V2 if args.v2 else SCHEMA
        try:
            raw = args.check.read_bytes()
        except OSError:
            print(json.dumps({"status": "HOLD", "reason": "CHECK_FILE_UNREADABLE"}))
            return 3
        try:
            declared = json.loads(raw).get("schema")
        except (ValueError, AttributeError):
            declared = None
        if declared != expected:
            print(json.dumps({"status": "HOLD", "reason": "SCHEMA_MISMATCH", "expected": expected}))
            return 3
    body = render(build_v2(args.jobs, verbose=True) if args.v2 else build())
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
