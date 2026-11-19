# SPDX-License-Identifier: Apache-2.0
"""Build or check the HJO Thm 1.2 finite-field census (hjo_census_gfq_v1.json).

  python3 research/hjo_census_gfq/build_census.py --write OUT.json [--jobs 6]
  python3 research/hjo_census_gfq/build_census.py --check research/hjo_census_gfq/hjo_census_gfq_v1.json [--jobs 6]
  python3 research/hjo_census_gfq/build_census.py --check-quick research/hjo_census_gfq/hjo_census_gfq_v1.json

--check recomputes every brute-force count and requires byte-identical output.
--check-quick recomputes only rows whose largest count is <= 20000 and compares them to the file.
Standard library only. Does not modify hjo_certificate_v1.json or any Theorem 1.2 claim.
"""
from __future__ import annotations
import argparse, hashlib, json, sys, time
from fractions import Fraction
from multiprocessing import Pool
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hjo_census_gfq as c

SCHEMA = "szl.khipu.hjo-census-gfq/v1"
DOMAIN = b"szl-khipu-hjo-census-gfq-v1\0"
FIELDS = (2, 3, 4, 5, 7, 8, 9)
NEW_FIELDS = (4, 5, 7, 8, 9)
# (a, b, N): largest colength m (q = 9 brute force kept to minutes on 8 vCPU; Thm 1.2 degree <= 6 throughout)
CONFIGS = {(2, 3, 1): 8, (2, 3, 2): 4, (2, 5, 1): 8, (2, 5, 2): 2, (3, 4, 1): 8, (3, 4, 2): 1,
           (3, 5, 1): 8, (3, 5, 2): 1, (2, 7, 1): 8, (2, 7, 2): 2, (4, 5, 1): 5, (4, 5, 2): 0,
           (3, 7, 1): 5, (3, 7, 2): 1, (4, 7, 1): 3, (5, 6, 1): 2}
BUDGET = 2 * 10**9

def _task(args):
    (a, b, n), m, q = args
    counts, _ = c.brute_counts(a, b, n, q, m, budget=BUDGET)
    return (a, b, n, q), counts

def brute_all(jobs: int, only=None):
    tasks = [(k, m, q) for k, m in CONFIGS.items() for q in FIELDS if only is None or only(k, m, q)]
    tasks.sort(key=lambda t: -c.peval(c.thm12_polys(*t[0], t[1])[-1], t[2]))
    with Pool(jobs) as pool:
        return dict(pool.imap_unordered(_task, tasks))

def frac(x: Fraction) -> str:
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"

def analyse(brute: dict) -> dict:
    rows, summary = [], {"cells": 0, "brute_eq_thm12": 0, "interp5_determined": 0, "interp5_eq_thm12": 0,
                         "interp5_underdetermined": 0, "interp7_determined": 0, "interp7_eq_thm12": 0,
                         "interp7_underdetermined": 0, "mismatches": []}
    for (a, b, n), mmax in CONFIGS.items():
        thm = c.thm12_polys(a, b, n, mmax)
        for m in range(mmax + 1):
            ys = {q: brute[(a, b, n, q)][m] for q in FIELDS}
            poly = thm[m]; deg = len(poly) - 1
            agree = all(ys[q] == c.peval(poly, q) for q in FIELDS)
            i5 = c.interpolate(list(NEW_FIELDS), [ys[q] for q in NEW_FIELDS])
            i7 = c.interpolate(list(FIELDS), [ys[q] for q in FIELDS])
            eq5 = [Fraction(x) for x in poly] == i5
            eq7 = [Fraction(x) for x in poly] == i7
            det5, det7 = deg <= len(NEW_FIELDS) - 1, deg <= len(FIELDS) - 1
            summary["cells"] += 1
            summary["brute_eq_thm12"] += agree
            if det5:
                summary["interp5_determined"] += 1; summary["interp5_eq_thm12"] += eq5
            else:
                summary["interp5_underdetermined"] += 1
            if det7:
                summary["interp7_determined"] += 1; summary["interp7_eq_thm12"] += eq7
            else:
                summary["interp7_underdetermined"] += 1
            if not agree or (det5 and not eq5) or (det7 and not eq7):
                summary["mismatches"].append([a, b, n, m])
            rows.append({"pair": [a, b], "rank": n, "colength": m,
                         "brute_counts": {str(q): ys[q] for q in FIELDS},
                         "thm12_poly_in_L_low_to_high": poly, "thm12_degree": deg,
                         "brute_eq_thm12_all_fields": agree,
                         "interp_new5_low_to_high": [frac(x) for x in i5],
                         "interp_new5_status": ("DETERMINED_EQ_THM12" if eq5 else "DETERMINED_MISMATCH") if det5
                                               else ("UNDERDETERMINED_DEG_GT_4"),
                         "interp_all7_low_to_high": [frac(x) for x in i7],
                         "interp_all7_status": ("DETERMINED_EQ_THM12" if eq7 else "DETERMINED_MISMATCH") if det7
                                               else ("UNDERDETERMINED_DEG_GT_6")})
    return {"rows": rows, "summary": summary}

def build(brute: dict) -> dict:
    an = analyse(brute)
    record = {
        "schema": SCHEMA,
        "statement": "#R-submodules of F_q[[T]]^N of colength m, R = F_q[[T^a,T^b]], counted by brute force over "
                     "GF(q) for q in {2,3,4,5,7,8,9}, compared with HJO Thm 1.2 (arXiv:2608.16086v1) at L = q; "
                     "counts interpolated as polynomials in q",
        "fields": list(FIELDS), "new_fields": list(NEW_FIELDS),
        "field_models": {"4": "F2[x]/(x^2+x+1)", "8": "F2[x]/(x^3+x+1)", "9": "F3[x]/(x^2+1)", "prime": "Z/qZ"},
        "configs": [[a, b, n, m] for (a, b, n), m in CONFIGS.items()],
        "interpolation_note": "5 points (q=4,5,7,8,9) determine a polynomial only up to degree 4; 7 points "
                              "(q=2..9) up to degree 6. Rows with higher Thm 1.2 degree are flagged UNDERDETERMINED; "
                              "for them only the pointwise equality brute == Thm1.2(q) is evidence.",
        "rows": an["rows"], "summary": an["summary"],
        "finite_check_only": True, "new_theorem_proved": False, "thm12_claims_modified": False,
        "certificate_v1_modified": False, "signature_verified": False,
        "sources": {"hjo": c.h.HJO_PAPER, "hlo": c.h.PAPER, "lean_repo": c.h.LEAN_REPO},
    }
    body = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    record["sha256"] = hashlib.sha256(DOMAIN + body).hexdigest()
    return record

def render(record: dict) -> bytes:
    return (json.dumps(record, indent=1, sort_keys=True, ensure_ascii=True) + "\n").encode("ascii")

def brute_from_file(path: Path) -> dict:
    rec = json.loads(path.read_text())
    out = {}
    for (a, b, n), mmax in CONFIGS.items():
        for q in FIELDS:
            out[(a, b, n, q)] = [r["brute_counts"][str(q)] for r in rec["rows"]
                                 if r["pair"] == [a, b] and r["rank"] == n][: mmax + 1]
    return out

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", type=Path); g.add_argument("--check", type=Path); g.add_argument("--check-quick", type=Path)
    g.add_argument("--from-jsonl", nargs=2, type=Path, metavar=("RAW", "OUT"), help=argparse.SUPPRESS)
    ap.add_argument("--jobs", type=int, default=4)
    args = ap.parse_args(); t0 = time.time()
    if args.check_quick:
        stored = brute_from_file(args.check_quick)
        small = lambda k, m, q: max(stored[(*k, q)]) <= 20000
        fresh = brute_all(args.jobs, small)
        bad = [k for k, v in fresh.items() if v != stored[k]]
        if bad:
            print(json.dumps({"status": "HOLD", "reason": "QUICK_CHECK_MISMATCH", "series": bad})); return 3
        if render(build(stored)) != args.check_quick.read_bytes():
            print(json.dumps({"status": "HOLD", "reason": "ANALYSIS_REPLAY_MISMATCH"})); return 3
        print(json.dumps({"status": "QUICK_MATCH", "series_rechecked": len(fresh), "seconds": round(time.time() - t0, 1)}))
        return 0
    if args.from_jsonl:
        raw, out = args.from_jsonl
        brute = {}
        for line in raw.read_text().splitlines():
            r = json.loads(line)
            if r["status"] != "OK":
                print(json.dumps({"status": "HOLD", "reason": "RAW_ROW_NOT_OK", "row": r})); return 3
            key = (*r["pair"], r["rank"]); brute[(*key, r["field"])] = r["brute"][: CONFIGS[key] + 1]
        target = out
    else:
        brute = brute_all(args.jobs); target = args.write or args.check
    body = render(build(brute))
    if args.check:
        if args.check.read_bytes() != body:
            print(json.dumps({"status": "HOLD", "reason": "CENSUS_REPLAY_MISMATCH"})); return 3
        status = "REPLAY_MATCH"
    else:
        if target.exists():
            print(json.dumps({"status": "HOLD", "reason": "REFUSE_OVERWRITE"})); return 3
        target.write_bytes(body); status = "WRITTEN"
    rec = json.loads(body)
    print(json.dumps({"status": status, "sha256": rec["sha256"], "summary": {k: v for k, v in rec["summary"].items()},
                      "seconds": round(time.time() - t0, 1)}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
