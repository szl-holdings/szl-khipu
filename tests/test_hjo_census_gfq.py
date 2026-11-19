#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact tests for the HJO Thm 1.2 finite-field census over GF(2..9) (standard library only)."""
import importlib.util
import json
import sys
import unittest
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "research" / "hjo_census_gfq"
CENSUS = DIR / "hjo_census_gfq_v1.json"
CERT = ROOT / "research" / "hjo_loom" / "hjo_certificate_v1.json"
sys.path.insert(0, str(DIR))
import hjo_census_gfq as c  # noqa: E402
import build_census as bc  # noqa: E402


class FieldTables(unittest.TestCase):
    def test_fields_are_fields(self):
        for q in (2, 3, 4, 5, 7, 8, 9):
            F = c.GF(q)  # constructor asserts commutativity, associativity, distributivity
            for x in range(1, q):
                self.assertEqual(F.mul[x][F.inv[x]], 1)
                self.assertEqual(F.add[x][F.neg[x]], 0)
            # multiplicative group is cyclic of order q-1
            orders = []
            for x in range(1, q):
                e, y = 1, x
                while y != 1:
                    y = F.mul[y][x]; e += 1
                orders.append(e)
            self.assertEqual(max(orders), q - 1)

    def test_characteristic(self):
        for q, p in ((4, 2), (8, 2), (9, 3)):
            F = c.GF(q)
            for x in range(q):
                acc = 0
                for _ in range(p):
                    acc = F.add[acc][x]
                self.assertEqual(acc, 0)


class AgreesWithExistingEngine(unittest.TestCase):
    def test_prime_fields_match_hjo_loom_bruteforce(self):
        for (a, b, n, q, m) in [(2, 3, 1, 2, 4), (2, 3, 2, 2, 3), (3, 4, 1, 3, 3), (2, 5, 2, 3, 2), (4, 5, 1, 2, 3)]:
            self.assertEqual(c.brute_counts(a, b, n, q, m)[0], c.h.quot_bruteforce_counts(a, b, n, q, m, budget=6_000_000))

    def test_symbolic_thm12_matches_certificate_v5(self):
        cert = json.loads(CERT.read_text())
        for row in cert["V5"]:
            a, b = row["pair"]; m = len(row["colengths"]) - 1
            polys = c.thm12_polys(a, b, row["rank"], m)
            self.assertEqual([c.peval(p, row["field"]) for p in polys], row["submodule_counts"])
            self.assertEqual(c.h.quot_formula_counts(a, b, row["rank"], row["field"], m), row["submodule_counts"])

    def test_small_prime_power_cases_match_thm12(self):
        for (a, b, n, q, m) in [(2, 3, 1, 4, 4), (2, 3, 2, 4, 2), (3, 4, 1, 8, 2), (2, 5, 1, 9, 3), (3, 5, 1, 4, 3)]:
            polys = c.thm12_polys(a, b, n, m)
            self.assertEqual(c.brute_counts(a, b, n, q, m)[0], [c.peval(p, q) for p in polys])


class Negative(unittest.TestCase):
    def test_wrong_irreducible_is_rejected(self):
        saved = c.IRRED[4]
        try:
            c.IRRED[4] = (2, [1, 0, 1])  # x^2+1 = (x+1)^2 is reducible over F2
            with self.assertRaises(Exception):
                c.GF(4)
        finally:
            c.IRRED[4] = saved

    def test_budget_refuses(self):
        with self.assertRaises(c.Budget):
            c.brute_counts(3, 4, 2, 9, 1, budget=1000)

    def test_interpolation_flags_underdetermined(self):
        xs = [4, 5, 7, 8, 9]
        p = [1, 1, 1, 1, 1, 1]  # degree 5: five points cannot recover it
        got = c.interpolate(xs, [c.peval(p, x) for x in xs])
        self.assertNotEqual(got, [Fraction(v) for v in p])


class CensusArtifact(unittest.TestCase):
    def test_census_summary_and_seal(self):
        rec = json.loads(CENSUS.read_text())
        s = rec["summary"]
        self.assertEqual(s["mismatches"], [])
        self.assertEqual(s["brute_eq_thm12"], s["cells"])
        self.assertEqual(s["interp5_eq_thm12"], s["interp5_determined"])
        self.assertEqual(s["interp7_eq_thm12"], s["interp7_determined"])
        self.assertFalse(rec["thm12_claims_modified"]); self.assertFalse(rec["certificate_v1_modified"])
        # analysis replays byte-for-byte from the stored counts
        self.assertEqual(bc.render(bc.build(bc.brute_from_file(CENSUS))), CENSUS.read_bytes())

    def test_stored_counts_equal_thm12_pointwise(self):
        rec = json.loads(CENSUS.read_text())
        for r in rec["rows"]:
            poly = c.thm12_polys(*r["pair"], r["rank"], r["colength"])[r["colength"]]
            self.assertEqual(poly, r["thm12_poly_in_L_low_to_high"])
            for q, v in r["brute_counts"].items():
                self.assertEqual(v, c.peval(poly, int(q)))


if __name__ == "__main__":
    unittest.main()
