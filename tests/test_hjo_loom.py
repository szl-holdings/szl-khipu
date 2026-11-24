#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Offline, exact tests for the HJO Loom engine and holographic GLB writer."""
import copy
import hashlib
import importlib.util
import itertools
import json
import math
import random
import subprocess
import sys
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock

from szl_khipu import hjo_loom as h
from szl_khipu import holo_glb as g

ROOT = Path(__file__).resolve().parents[1]
CERT = ROOT / "research" / "hjo_loom" / "hjo_certificate_v1.json"
CERT2 = ROOT / "research" / "hjo_loom" / "hjo_certificate_v2.json"
BUILDER = ROOT / "research" / "hjo_loom" / "build_certificate.py"


class GoldenValues(unittest.TestCase):
    """Numbers transcribed from arXiv:2609.20567v2 §1.1, §1.2 and §10."""

    def test_gap_sets_profiles_and_quadratic_form(self):
        p = h.gap_poset(4, 5)
        self.assertEqual(list(p.gaps), h.GOLDEN["gaps(4,5)"])
        self.assertEqual((p.delta, p.f, p.d), (6, 11, 9))
        self.assertEqual(list(h.balanced_profile(4, 5)), [1, 1, 1, 2])
        self.assertEqual(list(h.balanced_profile(5, 7)), [1, 1, 2, 1, 2])
        self.assertEqual(sorted(h.cover_relations(4, 5)),
                         [(1, 6), (2, 6), (2, 7), (3, 7), (6, 11), (7, 11)])
        q34 = h.gap_poset(3, 4)
        for n1, n2, n5 in [(0, 0, 0), (1, 0, 1), (1, 1, 2), (2, 3, 4)]:
            self.assertEqual(h._q_form(q34, (n1, n2, n5)),
                             n1 * n1 + n2 * n2 + n5 * n5 + n1 * n2 - n1 * n5)

    def test_published_polynomials(self):
        self.assertEqual(h.f_polynomial(2, 3, 2), h.GOLDEN["F_2(2,3)"])
        self.assertEqual(h.f_polynomial(4, 5, 1), h.GOLDEN["F_1(4,5)"])
        self.assertEqual(h.f_polynomial(4, 5, 2), h.GOLDEN["F_2(4,5)"])
        self.assertEqual(sum(h.f_polynomial(4, 5, 2)), 196)
        self.assertEqual(h.order_filters(4, 5), 14)

    def test_bivariate_rank_one_cusp(self):
        self.assertEqual(h.n_bivariate(2, 3, 1), {0: [1], 1: [0, 1]})

    def test_finite_rogers_ramanujan_cylinder(self):
        D = 16
        cyl = h.cylindric_series((1, 2), 2, D)
        self.assertEqual(h._mul(h._poch(2), cyl, D)[:6], [1, 1, 1, 0, 1, 0])
        self.assertFalse(any(h._mul(h._poch(2), cyl, D)[5:]))


class Identities(unittest.TestCase):
    PAIRS = [(2, 3), (2, 5), (3, 4), (3, 5), (2, 7), (4, 5), (3, 7), (2, 9), (3, 8), (4, 7), (5, 6)]

    def test_v1_z_equals_product(self):
        for a, b in self.PAIRS:
            with self.subTest(pair=(a, b)):
                self.assertEqual(h.z_series(a, b, 20), h.p_series(a, b, 20))

    def test_rogers_ramanujan_and_andrews_gordon_specialisations(self):
        D = 30
        rr = [1] + [0] * D
        for m in range(1, D + 1):
            if m % 5 in (1, 4):
                rr = h._over_1mqk(rr, m, D)
        self.assertEqual(h.p_series(2, 3, D), rr)
        ag = [1] + [0] * D               # (2,5): k = i = 3, modulus 7
        for m in range(1, D + 1):
            if m % 7 not in (0, 3, 4):
                ag = h._over_1mqk(ag, m, D)
        self.assertEqual(h.z_series(2, 5, D), ag)

    def test_v2_finite_identity_and_v4_catalan(self):
        for a, b in self.PAIRS:
            for rank in (1, 2):
                with self.subTest(pair=(a, b), rank=rank):
                    f = h.f_polynomial(a, b, rank)
                    D = min(h.MAX_DEGREE, len(f) + 3)
                    cyl = h.cylindric_series(h.balanced_profile(a, b), rank, D)
                    self.assertEqual(h._mul(h._poch(rank), cyl, D), (f + [0] * (D + 1))[:D + 1])
                    self.assertEqual(sum(f), h.rational_catalan(a, b) ** rank)

    def test_pruned_walk_equals_unpruned_reference(self):
        for a, b in [(3, 4), (4, 5), (3, 7)]:
            with self.subTest(pair=(a, b)):
                self.assertEqual(h.z_series(a, b, 16), h._z_series_bruteforce(a, b, 16))

    def test_v5_quot_bruteforce_matches_formula(self):
        cases = [(2, 3, 1, 2, 4), (2, 3, 2, 2, 3), (2, 3, 2, 3, 2), (3, 4, 1, 3, 3), (3, 4, 2, 2, 2)]
        for a, b, rank, q, mm in cases:
            with self.subTest(case=(a, b, rank, q)):
                self.assertEqual(h.quot_bruteforce_counts(a, b, rank, q, mm),
                                 h.quot_formula_counts(a, b, rank, q, mm))
        self.assertEqual(h.quot_formula_counts(2, 3, 1, 2, 3), [1, 3, 3, 3])   # 1 + q

    def test_v6_two_by_two_count_by_hand(self):
        terms = h.nilpotent_pair_terms(2, 3, 2, 2)
        # 10 commuting nilpotent pairs in M_2(F_2); |GL_2(F_2)| = 6.
        self.assertEqual(terms, [Fraction(1), Fraction(1), Fraction(10, 6)])
        self.assertLess(float(sum(terms)), h.groupoid_prediction(2, 3, 2))


class IndependentImplementationAgreement(unittest.TestCase):
    """research/hjo_profile/cylindric.py was written separately from the Lean
    challenge's definitions with two enumerators of its own; the level-vector
    count here must agree with it wherever both are defined."""

    def test_cylindric_counts_match_hjo_profile_lab(self):
        import importlib.util
        path = ROOT / "research" / "hjo_profile" / "cylindric.py"
        spec = importlib.util.spec_from_file_location("hjo_profile_cylindric", path)
        lab = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lab)
        checked = 0
        for a, b in [(2, 3), (2, 5), (3, 4), (3, 5), (4, 5), (3, 7), (4, 7), (2, 9)]:
            for rank in (1, 2, 3):
                with self.subTest(pair=(a, b), rank=rank):
                    theirs = lab.witness(a, b, rank, 8)
                    self.assertEqual(list(theirs["profile"]), list(h.balanced_profile(a, b)))
                    self.assertEqual(theirs["cylindric_coefficients_by_volume"],
                                     h.cylindric_series(h.balanced_profile(a, b), rank, 8))
                    checked += 1
        self.assertEqual(checked, 24)


class NegativeControls(unittest.TestCase):
    def test_wrong_product_exponent_is_detected(self):
        z = h.z_series(3, 4, 20)
        p = [1] + [0] * 20
        for m in range(1, 21):
            for _ in range(h.rho(3, 4, m) + (1 if m == 5 else 0)):
                p = h._over_1mqk(p, m, 20)
        self.assertNotEqual(z, p)

    def test_wrong_profile_breaks_finite_identity(self):
        f = h.f_polynomial(4, 5, 2)
        D = len(f) + 3
        wrong = h.cylindric_series((2, 1, 1, 1), 2, D)
        right = h.cylindric_series((1, 1, 1, 2), 2, D)
        self.assertEqual(h._mul(h._poch(2), right, D), (f + [0] * (D + 1))[:D + 1])
        # A rotated profile is an equivalent cylinder; a non-balanced one is not.
        self.assertEqual(wrong, right)
        bad = h.cylindric_series((0, 1, 2, 2), 2, D)
        self.assertNotEqual(h._mul(h._poch(2), bad, D), (f + [0] * (D + 1))[:D + 1])

    def test_inexact_division_refused(self):
        with self.assertRaisesRegex(h.HjoHold, "NON_EXACT"):
            h._exact_div_1mqk([1, 1], 2)

    def test_inputs_fail_closed(self):
        for bad in [(2, 4), (3, 3), (1, 2), (True, 3), (2.0, 3), (6, 13)]:
            with self.subTest(bad=bad), self.assertRaises(h.HjoHold):
                h.verify(*bad)
        with self.assertRaises(h.HjoHold):
            h.z_series(2, 3, h.MAX_DEGREE + 1)
        with self.assertRaises(h.HjoHold):
            h.quot_bruteforce_counts(2, 3, 2, 5, 2)
        with self.assertRaisesRegex(h.HjoHold, "BUDGET"):
            h.quot_bruteforce_counts(3, 4, 2, 3, 3, budget=500)


class SealedRecord(unittest.TestCase):
    def test_verify_record_claims_and_digest(self):
        r = h.verify(2, 3, degree=16, rank=2, field=2, quot_m=2, nil_n=2)
        body = {k: v for k, v in r.items() if k != "sha256"}
        raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        self.assertEqual(r["sha256"], hashlib.sha256(h.DOMAIN + raw).hexdigest())
        self.assertFalse(r["lean_certificate_replayed"])
        self.assertFalse(r["new_theorem_proved"])
        self.assertTrue(r["finite_check_only"])
        self.assertEqual(r["historical_claim"], "NOT_ESTABLISHED")
        ids = [c["id"] for c in r["checks"]]
        self.assertEqual(ids, ["V1", "V2", "V4", "V3", "V5.N1", "V5.N2", "V6"])
        self.assertEqual(r["checks"][-1]["status"], "CONSISTENT")

    def test_budget_is_reported_not_faked(self):
        r = h.verify(2, 3, degree=8, rank=1, field=3, quot_m=3, nil_n=1, budget=40)
        v5 = [c for c in r["checks"] if c["id"].startswith("V5")]
        self.assertTrue(any(c["status"] == "NOT_RUN_BUDGET" and c["bruteforce"] is None for c in v5))

    @unittest.skipUnless(CERT.is_file(), "certificate not built")
    def test_shipped_certificate_seal_and_claims(self):
        cert = json.loads(CERT.read_text())
        self.assertEqual(h.seal(cert)["sha256"], cert["sha256"])
        self.assertFalse(cert["new_theorem_proved"])
        self.assertFalse(cert["lean_certificate_replayed"])
        self.assertEqual(len(cert["pairs"]), 17)
        self.assertTrue(all(cert["V3"].values()))
        self.assertTrue(all(row["status"] == "CONSISTENT_NOT_VERIFIED" for row in cert["V6"]))


class HoloGlb(unittest.TestCase):
    def test_hjo_scene_structure(self):
        rows = h.sample_cylindric(h.balanced_profile(4, 5), 2, 12, seed=3)
        data = g.hjo_scene(4, 5, h.gap_poset(4, 5).gaps, h.cover_relations(4, 5), rows,
                           h.balanced_profile(4, 5))
        man = g.parse_glb(data)
        names = [m["name"] for m in man["materials"]]
        self.assertIn("torus-knot-T(a,b)", names)
        self.assertIn("cylinder-cell", names)
        self.assertLess(len(data), g.MAX_BYTES)

    def test_sample_cylindric_satisfies_definition(self):
        for a, b in [(2, 3), (3, 4), (4, 5)]:
            c = h.balanced_profile(a, b)
            rows = h.sample_cylindric(c, 2, 10, seed=11)
            self.assertEqual(sum(map(sum, rows)), 10)
            for i in range(a):
                nxt = rows[(i + 1) % a]
                for j in range(1, 12):
                    left = rows[i][j - 1] if j - 1 < len(rows[i]) else 0
                    right = nxt[j - 1 + c[i]] if j - 1 + c[i] < len(nxt) else 0
                    self.assertGreaterEqual(left, right)

    def test_tamper_and_budget(self):
        data = bytearray(g.hjo_scene(2, 3, (1,), [], [[1]], (1, 2)))
        data[8] ^= 1
        with self.assertRaises(g.HoloHold):
            g.parse_glb(bytes(data))
        s = g.Scene("t")
        with self.assertRaises(g.HoloHold):
            s.tube([(0, 0, 0)], 0.1, s.material("m", (1, 1, 1)))
        with self.assertRaises(g.HoloHold):
            s.tube([(0, 0, 0), (math.inf, 0, 0)], 0.1, 0)


class CertificateCli(unittest.TestCase):
    def test_write_refuses_overwrite(self):
        if not CERT.is_file():
            self.skipTest("certificate not built")
        out = subprocess.run([sys.executable, str(ROOT / "research/hjo_loom/build_certificate.py"),
                              "--write", str(CERT)], capture_output=True, text=True, timeout=1800)
        self.assertEqual(out.returncode, 3)
        self.assertIn("REFUSE_OVERWRITE", out.stdout)


def _poly_mul_mod_p(f: list[int], g_: list[int], p: int) -> list[int]:
    out = [0] * (len(f) + len(g_) - 1)
    for i, x in enumerate(f):
        for j, y in enumerate(g_):
            out[i + j] = (out[i + j] + x * y) % p
    return out


class FiniteFields(unittest.TestCase):
    """The GF(q) tables behind the V7 census, checked exhaustively for every q."""

    def test_moduli_are_irreducible(self):
        # A monic f of degree k over F_p is reducible iff f = g h with g, h monic of
        # degrees d and k - d, 1 <= d <= k // 2. Every such product is formed here.
        for q, (p, modulus) in sorted(h.GF_MODULI.items()):
            k = len(modulus) - 1
            with self.subTest(q=q):
                self.assertEqual((p ** k, modulus[-1]), (q, 1))
                products = set()
                for d in range(1, k // 2 + 1):
                    for g_low in itertools.product(range(p), repeat=d):
                        for h_low in itertools.product(range(p), repeat=k - d):
                            products.add(tuple(_poly_mul_mod_p(list(g_low) + [1], list(h_low) + [1], p)))
                self.assertIn((0,) * k + (1,), products)        # x^k is caught, so the sweep bites
                self.assertNotIn(tuple(modulus), products)
                # Degree <= 3: irreducible iff no root in F_p, a second route to the same fact.
                self.assertTrue(all(sum(c * r ** i for i, c in enumerate(modulus)) % p for r in range(p)))

    def test_field_axioms_exhaustive(self):
        for q in h.CENSUS_FIELDS:
            f = h.galois_field(q)
            add, sub, mul, inv = f.add, f.sub, f.mul, f.inv
            with self.subTest(q=q):
                for x in range(q):
                    self.assertEqual((add[x][0], mul[x][1], mul[x][0]), (x, x, 0))
                    self.assertEqual(add[x][sub[0][x]], 0)
                    if x:
                        self.assertEqual(mul[x][inv[x]], 1)
                    power = 1
                    for _ in range(q):
                        power = mul[power][x]
                    self.assertEqual(power, x)                  # every element is a root of X^q - X
                    for y in range(q):
                        self.assertEqual(add[x][y], add[y][x])
                        self.assertEqual(mul[x][y], mul[y][x])
                        self.assertEqual(add[sub[x][y]][y], x)
                        for z in range(q):
                            self.assertEqual(add[add[x][y]][z], add[x][add[y][z]])
                            self.assertEqual(mul[mul[x][y]][z], mul[x][mul[y][z]])
                            self.assertEqual(mul[x][add[y][z]], add[mul[x][y]][mul[x][z]])

    def test_prime_fields_are_plain_modular_arithmetic(self):
        # The F_2 / F_3 path of V5 used (x - c*y) % q and pow(x, q-2, q); the tables
        # must be exactly that arithmetic for the v1 certificate to replay unchanged.
        for q in (2, 3, 5, 7):
            f = h.galois_field(q)
            for x in range(q):
                for y in range(q):
                    self.assertEqual((f.add[x][y], f.sub[x][y], f.mul[x][y]),
                                     ((x + y) % q, (x - y) % q, (x * y) % q))
                if x:
                    self.assertEqual(f.inv[x], pow(x, q - 2, q))

    def test_reducible_modulus_is_refused(self):
        h._galois_field.cache_clear()
        try:
            with mock.patch.dict(h.GF_MODULI, {4: (2, (1, 0, 1))}):   # x^2 + 1 = (x + 1)^2 over F_2
                with self.assertRaisesRegex(h.HjoHold, "REDUCIBLE"):
                    h._galois_field(4)
            for spec in ((2, (1, 1, 0, 1)), (2, (1, 1, 2)), (3, (1, 0, 1))):   # 2^3 != 4, not monic, 3^2 != 4
                h._galois_field.cache_clear()
                with self.subTest(spec=spec), mock.patch.dict(h.GF_MODULI, {4: spec}):
                    with self.assertRaisesRegex(h.HjoHold, "^FIELD_MODULUS_INVALID$"):
                        h._galois_field(4)
        finally:
            h._galois_field.cache_clear()
        self.assertEqual(h.galois_field(4).mul[2][2], 3)              # x * x = x + 1

    def test_unsupported_orders_fail_closed(self):
        for q in (0, 1, 6, 10, 16, True, 4.0, "4"):
            with self.subTest(q=q), self.assertRaises(h.HjoHold):
                h.galois_field(q)

    def test_linear_solver_yields_exactly_the_solutions(self):
        # Every census replay in this file still passes with a solver that returns wrong
        # solutions (a sign error in back-substitution, a pivot row left unscaled), so
        # _solve_affine is checked on its own: over every field it must yield each x
        # with rows @ x = rhs exactly once, and nothing else.
        rng = random.Random(20261124)
        for q in h.CENSUS_FIELDS:
            f = h.galois_field(q)

            def apply(rows, x):
                out = []
                for row in rows:
                    acc = 0
                    for c, v in zip(row, x):
                        acc = f.add[acc][f.mul[c][v]]
                    out.append(acc)
                return out

            with self.subTest(q=q):
                for trial in range(40):
                    nvars, nrows = rng.randint(1, 3), rng.randint(1, 3)
                    rows = [[rng.randrange(q) for _ in range(nvars)] for _ in range(nrows)]
                    if trial % 2:      # half consistent by construction, half arbitrary
                        rhs = apply(rows, [rng.randrange(q) for _ in range(nvars)])
                    else:
                        rhs = [rng.randrange(q) for _ in range(nrows)]
                    want = [list(x) for x in itertools.product(range(q), repeat=nvars)
                            if apply(rows, x) == rhs]
                    got = sorted(h._solve_affine(rows, rhs, nvars, f))
                    self.assertEqual(got, want, (rows, rhs))


class MultiFieldCensus(unittest.TestCase):
    def test_bruteforce_matches_formula_over_gf4_and_gf5(self):
        cases = [(2, 3, 1, 4, 4), (2, 3, 2, 4, 2), (3, 4, 1, 4, 3), (2, 5, 1, 4, 3),
                 (2, 3, 1, 5, 4), (2, 3, 2, 5, 2), (3, 4, 1, 5, 3)]
        for a, b, rank, q, mm in cases:
            with self.subTest(case=(a, b, rank, q)):
                run = h.quot_bruteforce_census(a, b, rank, q, mm, budget=200_000)
                self.assertEqual(run["stop"], "COLENGTH_CEILING")
                self.assertEqual(run["counts"], h.quot_formula_counts(a, b, rank, q, mm))
        # (2,3), rank 1: 1 + q submodules in every positive colength.
        self.assertEqual(h.quot_bruteforce_census(2, 3, 1, 4, 3, budget=10_000)["counts"], [1, 5, 5, 5])

    def test_census_equals_interactive_counts_on_prime_fields(self):
        for a, b, rank, q, mm in [(2, 3, 2, 3, 3), (3, 4, 1, 2, 5)]:
            with self.subTest(case=(a, b, rank, q)):
                run = h.quot_bruteforce_census(a, b, rank, q, mm, budget=6_000_000)
                self.assertEqual(run["counts"], h.quot_bruteforce_counts(a, b, rank, q, mm, budget=6_000_000))

    def test_work_cap_keeps_only_completed_colengths(self):
        full = h.quot_bruteforce_census(2, 3, 2, 4, 3, budget=10 ** 7)
        capped = h.quot_bruteforce_census(2, 3, 2, 4, 3, budget=6_000)
        self.assertEqual(full["stop"], "COLENGTH_CEILING")
        self.assertEqual(capped["stop"], "WORK_CAP")
        self.assertLess(len(capped["counts"]), len(full["counts"]))
        self.assertEqual(capped["counts"], full["counts"][:len(capped["counts"])])
        self.assertLessEqual(capped["work_steps"], 6_000)

    def test_work_cap_boundary_is_exact(self):
        # (2,3), N = 1 over F_2 takes exactly 601 steps for colengths 0..8. A cap equal
        # to that completes every colength; one step less abandons colength 8 only.
        full = h.quot_bruteforce_census(2, 3, 1, 2, 8, budget=10 ** 6)
        self.assertEqual((full["stop"], full["work_steps"]), ("COLENGTH_CEILING", 601))
        self.assertEqual(h.quot_bruteforce_census(2, 3, 1, 2, 8, budget=601), full)
        short = h.quot_bruteforce_census(2, 3, 1, 2, 8, budget=600)
        self.assertEqual(short["stop"], "WORK_CAP")
        self.assertEqual(short["counts"], full["counts"][:-1])
        self.assertEqual(short["cumulative_work"], full["cumulative_work"][:-1])
        self.assertEqual(short["work_steps"], full["cumulative_work"][-2])

    def test_odd_characteristic_sign_is_seen_at_colength_5(self):
        # Solving for +r0 instead of -r0 is harmless in characteristic 2 and changes no
        # count below colength 5 here; at colength 5 it gave 6502 instead of 7960
        # (mutation run). Every other replay in this file passed with that error.
        run = h.quot_bruteforce_census(2, 3, 2, 3, 5, budget=200_000)
        self.assertEqual(run["stop"], "COLENGTH_CEILING")
        self.assertEqual(run["counts"], h.quot_formula_counts(2, 3, 2, 3, 5))
        self.assertEqual(run["counts"][5], 7960)

    def test_census_inputs_fail_closed(self):
        bad = [dict(q=6), dict(q=10), dict(q=True), dict(rank=3), dict(rank=0),
               dict(colength_ceiling=9), dict(colength_ceiling=-1), dict(budget=0), dict(budget=1.5)]
        for override in bad:
            args = {"q": 4, "rank": 1, "colength_ceiling": 2, "budget": 1_000, **override}
            with self.subTest(**override), self.assertRaises(h.HjoHold):
                h.quot_bruteforce_census(2, 3, args["rank"], args["q"], args["colength_ceiling"],
                                         budget=args["budget"])
        # The interactive entry points keep their F_2 / F_3 contract.
        with self.assertRaises(h.HjoHold):
            h.quot_bruteforce_counts(2, 3, 1, 4, 2)
        with self.assertRaisesRegex(h.HjoHold, "FIELD_INVALID"):
            h.verify(2, 3, degree=8, rank=1, field=4, quot_m=1, nil_n=1)

    def test_census_counts_do_not_test_the_field_tables(self):
        # Negative control (METHOD.md): tables that are not a field give the same counts.
        # Over Z/6 the recursion returns the Thm 1.2 polynomial at L = 6, and with a GF(4)
        # product where x * x = x (not associative) it returns the real q = 4 counts in
        # the same steps. So V7 agreement at q = 4, 8, 9 is no evidence for the tables;
        # FiniteFields is.
        def table(op):
            return tuple(tuple(op(u, v) % 6 for v in range(6)) for u in range(6))

        z6 = h.GaloisField(6, 6, (0, 1), table(int.__add__), table(int.__sub__), table(int.__mul__),
                           tuple(next((v for v in range(1, 6) if u * v % 6 == 1), 0) for u in range(6)))
        self.assertEqual(z6.mul[2][3], 0)                     # zero divisors
        for (a, b, rank, mm), want in {(2, 3, 2, 2): [1, 259, 3103], (3, 4, 1, 4): [1, 43, 79, 295, 295]}.items():
            delta, work = h.gap_poset(a, b).delta, [0]
            with self.subTest(case=(a, b, rank)):
                got = [h._echelon_count(a, b, rank, z6, m, 2 * delta, work, 10 ** 6) for m in range(mm + 1)]
                self.assertEqual(got, want)
                self.assertEqual(got, h._quot_formula_at(h.n_bivariate(a, b, rank), delta, rank, 6, mm))
        gf4 = h.galois_field(4)
        mul = [list(row) for row in gf4.mul]
        mul[2][2] = 2                                          # x * x = x instead of x + 1
        bad = h.GaloisField(4, 2, gf4.modulus, gf4.add, gf4.sub, tuple(map(tuple, mul)), gf4.inv)
        self.assertNotEqual(bad.mul[bad.mul[2][2]][3], bad.mul[2][bad.mul[2][3]])
        real = h.quot_bruteforce_census(3, 4, 1, 4, 8, budget=10 ** 6)
        with mock.patch.object(h, "_galois_field", return_value=bad):
            self.assertEqual(h.quot_bruteforce_census(3, 4, 1, 4, 8, budget=10 ** 6), real)
        self.assertEqual((real["stop"], real["work_steps"]), ("COLENGTH_CEILING", 19_497))


class QPolynomials(unittest.TestCase):
    def test_interpolation_is_exact(self):
        pts = [(x, 3 - 2 * x + x ** 3) for x in (2, 3, 5, 7)]
        self.assertEqual(h._interpolate(pts), [3, -2, 0, 1])
        self.assertEqual(h._interpolate(pts + [(11, 3 - 22 + 1331)]), [3, -2, 0, 1])
        self.assertEqual(h._interpolate([(2, 1), (4, 2)]), [0, Fraction(1, 2)])
        with self.assertRaises(h.HjoHold):
            h._interpolate([(2, 1), (2, 3)])

    def test_formula_polynomials_known_cases(self):
        self.assertEqual(h.quot_formula_polynomials(2, 3, 1, 3), [[1], [1, 1], [1, 1], [1, 1]])
        self.assertEqual(h.quot_formula_polynomials(2, 3, 2, 1)[1], [1, 1, 1, 1])   # (q^4 - 1)/(q - 1)
        polys = h.quot_formula_polynomials(3, 4, 2, 2)
        for q in h.CENSUS_FIELDS:
            with self.subTest(q=q):
                self.assertEqual([h._eval(p, Fraction(q)) for p in polys], h.quot_formula_counts(3, 4, 2, q, 2))

    def test_too_few_points_do_not_recover(self):
        poly = h.quot_formula_polynomials(2, 3, 2, 2)[2]
        self.assertEqual(len(poly) - 1, 4)
        pts = [(q, int(h._eval(poly, Fraction(q)))) for q in (2, 3, 4, 5)]
        self.assertNotEqual(h._interpolate(pts), poly)
        self.assertEqual(h._interpolate(pts + [(7, int(h._eval(poly, Fraction(7))))]), poly)

    def test_degree_precondition_fails_closed(self):
        # An n_s of degree 3 > N^2 delta = 1 would leave negative powers of L: the
        # interpolation refuses it up front, and the count at L = 2 is not an integer.
        with mock.patch.object(h, "n_bivariate", return_value={0: [1], 1: [0, 1, 0, 1]}):
            with self.assertRaisesRegex(h.HjoHold, "^FORMULA_DEGREE_PRECONDITION_FAILED$"):
                h.quot_formula_polynomials(2, 3, 1, 2)
            with self.assertRaisesRegex(h.HjoHold, "^FORMULA_NOT_INTEGRAL$"):
                h.quot_formula_counts(2, 3, 1, 2, 2)

    def test_surplus_points_catch_values_off_a_polynomial_within_the_bound(self):
        # The formula is evaluated at B + 1 + extra nodes L = 2, 3, ... (METHOD.md).
        # Add to one colength the integer polynomial that vanishes at every node but
        # the last: only the last surplus point sees it, and the degree bound must
        # then refuse the interpolant.
        a, b, rank, m_max, extra = 2, 3, 2, 2, 3
        bound = rank * rank * h.gap_poset(a, b).delta + (rank - 1) * m_max
        nodes = list(range(2, bound + extra + 3))
        real = h._quot_formula_at
        for m in range(m_max + 1):
            def off(biv, delta, rank_, L, top, m=m):
                values = real(biv, delta, rank_, L, top)
                values[m] += math.prod(L - x for x in nodes[:-1])
                return values

            with self.subTest(m=m), mock.patch.object(h, "_quot_formula_at", off):
                with self.assertRaisesRegex(h.HjoHold, "^FORMULA_NOT_A_POLYNOMIAL_WITHIN_BOUND$"):
                    h.quot_formula_polynomials(a, b, rank, m_max, extra=extra)
        self.assertEqual(len(h.quot_formula_polynomials(a, b, rank, m_max, extra=extra)), m_max + 1)


def _load_builder():
    spec = importlib.util.spec_from_file_location("hjo_build_certificate_under_test", BUILDER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CensusCertificate(unittest.TestCase):
    """The sealed v2 certificate: seal, claims, internal consistency, and a replay
    of a cheap subset (the full --v2 --check takes many minutes, see METHOD.md)."""

    @classmethod
    def setUpClass(cls):
        if not CERT2.is_file():
            raise unittest.SkipTest("v2 certificate not built")
        cls.cert = json.loads(CERT2.read_text())

    def test_seal_claims_and_plan(self):
        cert = self.cert
        self.assertEqual(cert["schema"], "szl.khipu.hjo-certificate/v2")
        self.assertEqual(h.seal(cert)["sha256"], cert["sha256"])
        self.assertFalse(cert["new_theorem_proved"])
        self.assertFalse(cert["lean_certificate_replayed"])
        self.assertFalse(cert["independent_replication"])
        self.assertTrue(cert["finite_check_only"])
        self.assertEqual(cert["census"]["fields"], list(h.CENSUS_FIELDS))
        self.assertEqual(len(cert["V7"]), len(cert["census"]["series"]) * len(h.CENSUS_FIELDS))
        moduli = {f["q"]: (f["p"], tuple(f["modulus_low_to_high"])) for f in cert["fields"]}
        for q, spec in h.GF_MODULI.items():
            self.assertEqual(moduli[q], spec)

    def test_rows_are_internally_consistent(self):
        cap = self.cert["census"]["work_cap_steps_per_series"]
        v7 = {(tuple(r["pair"]), r["rank"], r["field"]): r for r in self.cert["V7"]}
        for row in self.cert["V7"]:
            with self.subTest(v7=(row["pair"], row["rank"], row["field"])):
                self.assertEqual(row["bruteforce"], row["formula"])
                self.assertEqual(row["agree"], [True] * (row["colength_max"] + 1))
                self.assertEqual(len(row["bruteforce"]), row["colength_max"] + 1)
                self.assertIn(row["stop"], ("WORK_CAP", "COLENGTH_CEILING"))
                self.assertLessEqual(row["work_steps"], cap)
                steps = row["cumulative_work_steps"]
                self.assertEqual(len(steps), row["colength_max"] + 1)
                self.assertEqual(steps, sorted(steps))
                self.assertEqual(steps[-1], row["work_steps"])
        for row in self.cert["V8"]:
            with self.subTest(v8=(row["pair"], row["rank"], row["colength"])):
                poly, m = row["formula_polynomial"], row["colength"]
                pts = [(q, v7[(tuple(row["pair"]), row["rank"], q)]["bruteforce"][m])
                       for q in row["bruteforce_fields"]]
                self.assertEqual(row["degree"], len(poly) - 1)
                self.assertLessEqual(row["degree"], row["degree_bound"])
                self.assertEqual(row["bruteforce_points"], len(pts))
                for q, count in pts:
                    self.assertEqual(h._eval(poly, Fraction(q)), count)
                if len(pts) >= len(poly):
                    self.assertEqual(row["status"], "RECOVERED")
                    self.assertEqual(row["bruteforce_interpolant"], poly)
                    self.assertEqual(h._interpolate(pts), poly)
                    self.assertEqual(row["extra_checks"], len(pts) - len(poly))
                else:
                    self.assertEqual(row["status"], "UNDERDETERMINED")
                    self.assertIsNone(row["bruteforce_interpolant"])
                    self.assertEqual(row["points_short"], len(poly) - len(pts))

    def test_cheap_subset_replays_from_scratch(self):
        builder = _load_builder()
        v7 = {(tuple(r["pair"]), r["rank"], r["field"]): r for r in self.cert["V7"]}
        for q in h.CENSUS_FIELDS:
            with self.subTest(q=q):
                self.assertEqual(builder.census_row(2, 3, 1, q), v7[((2, 3), 1, q)])
        for (a, b), rank, q in [((3, 4), 1, 4), ((2, 5), 1, 5)]:
            with self.subTest(case=(a, b, rank, q)):
                self.assertEqual(builder.census_row(a, b, rank, q), v7[((a, b), rank, q)])
        rows = builder.recovery_rows(2, 3, 1, [v7[((2, 3), 1, q)] for q in h.CENSUS_FIELDS])
        self.assertEqual(rows, [r for r in self.cert["V8"] if r["pair"] == [2, 3] and r["rank"] == 1])

    def test_v8_and_summary_replay_from_the_v7_rows(self):
        # V8 needs no enumeration, so all of it is rebuilt here from the sealed V7 rows:
        # a changed RECOVERED rule or degree bound cannot pass on (2,3) rank 1 alone.
        builder = _load_builder()
        v7, v8 = self.cert["V7"], []
        for a, b, rank in builder.CENSUS_SERIES:
            v8 += builder.recovery_rows(a, b, rank, [r for r in v7 if r["pair"] == [a, b] and r["rank"] == rank])
        self.assertEqual(v8, self.cert["V8"])
        self.assertEqual(self.cert["summary"], {
            "series": len(v7),
            "colength_counts_compared": sum(len(r["bruteforce"]) for r in v7),
            "stopped_by_work_cap": sum(r["stop"] == "WORK_CAP" for r in v7),
            "stopped_by_colength_ceiling": sum(r["stop"] == "COLENGTH_CEILING" for r in v7),
            "recovered": sum(r["status"] == "RECOVERED" for r in v8),
            "underdetermined": sum(r["status"] == "UNDERDETERMINED" for r in v8),
        })

    def test_builder_constants_match_the_certificate(self):
        # The cheap replays finish far below the cap, so they cannot see a changed cap,
        # ceiling or point count; the certificate records all three.
        builder = _load_builder()
        census, interpolation = self.cert["census"], self.cert["interpolation"]
        self.assertEqual(builder.CENSUS_WORK_CAP, census["work_cap_steps_per_series"])
        self.assertEqual(builder.CENSUS_COLENGTH_CEILING, census["colength_ceiling"])
        self.assertEqual(builder.FORMULA_EXTRA_POINTS, interpolation["formula_extra_points"])
        self.assertEqual([list(s) for s in builder.CENSUS_SERIES], census["series"])
        self.assertEqual(list(builder.h.CENSUS_FIELDS), census["fields"])

    def test_builder_guards_fail_closed(self):
        builder = _load_builder()
        hold = builder.h.HjoHold          # the builder loads its own copy of the module
        real = builder.h.quot_formula_counts

        def off_by_one(*args):
            counts = real(*args)
            return counts[:-1] + [counts[-1] + 1]

        with mock.patch.object(builder.h, "quot_formula_counts", off_by_one):
            with self.assertRaisesRegex(hold, "^V7_MISMATCH_2_3_1_2$"):
                builder.census_row(2, 3, 1, 2)
        with mock.patch.object(builder, "CENSUS_WORK_CAP", 1):
            with self.assertRaisesRegex(hold, "^V7_NO_COLENGTH_COMPLETED_2_3_1_2$"):
                builder.census_row(2, 3, 1, 2)
        rows = [r for r in self.cert["V7"] if r["pair"] == [2, 3] and r["rank"] == 1]
        for key, code in (("bruteforce", "V8_INTERPOLANT_MISMATCH_2_3_1_1"),
                          ("formula", "V8_POLYNOMIAL_OFF_FORMULA_2_3_1_1")):
            tampered = copy.deepcopy(rows)
            next(r for r in tampered if r["field"] == 2)[key][1] += 1
            with self.subTest(key=key), self.assertRaisesRegex(hold, f"^{code}$"):
                builder.recovery_rows(2, 3, 1, tampered)
        with self.assertRaisesRegex(hold, "^V8_CENSUS_INCOMPLETE_2_3_1$"):
            builder.recovery_rows(2, 3, 1, rows[1:])

    def test_check_refuses_wrong_schema_without_rebuilding(self):
        out = subprocess.run([sys.executable, str(BUILDER), "--v2", "--check", str(CERT)],
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 3)
        self.assertIn("SCHEMA_MISMATCH", out.stdout)
        out = subprocess.run([sys.executable, str(BUILDER), "--v2", "--write", str(CERT2)],
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 3)
        self.assertIn("REFUSE_OVERWRITE", out.stdout)


def _flat(text: str) -> str:
    return " ".join(text.split())


class CensusDocs(unittest.TestCase):
    """README.md, METHOD.md and the module docstring must say what the v2 certificate
    shows, and no more."""

    @classmethod
    def setUpClass(cls):
        if not CERT2.is_file():
            raise unittest.SkipTest("v2 certificate not built")
        cls.cert = json.loads(CERT2.read_text())
        cls.readme = _flat((CERT2.parent / "README.md").read_text(encoding="utf-8"))
        cls.method = _flat((CERT2.parent / "METHOD.md").read_text(encoding="utf-8"))
        cls.docs = (("README", cls.readme), ("METHOD", cls.method), ("module", _flat(h.__doc__)))

    def test_withdrawn_claims_stay_withdrawn(self):
        # RECOVERED takes its degree from the formula, so nothing may say the enumeration
        # fixes the polynomial by itself. Measured wall times live in METHOD.md only.
        for name, text in self.docs:
            for phrase in ("recovered from brute force alone", "brute-force counts alone",
                           "enumeration data alone fix", "without using the formula"):
                with self.subTest(doc=name, phrase=phrase):
                    self.assertNotIn(phrase, text)
        self.assertNotRegex(BUILDER.read_text(encoding="utf-8"), r"\d\s*minutes")

    def test_census_is_not_read_as_a_test_of_the_field_tables(self):
        for name, text in self.docs:
            with self.subTest(doc=name):
                self.assertIn("Z/6", text)
        for name, text in self.docs[:2]:
            with self.subTest(doc=name):
                self.assertIn("is not evidence that the GF(p", text)
                self.assertIn("1, 259, 3103", text)    # the Z/6 control in MultiFieldCensus

    def test_headline_counts_separate_colength_0(self):
        v7, v8 = self.cert["V7"], self.cert["V8"]
        total = sum(len(r["bruteforce"]) for r in v7)
        self.assertTrue(all(r["bruteforce"][0] == r["formula"][0] == 1 for r in v7))
        only0 = [r for r in v7 if r["colength_max"] == 0]
        self.assertEqual({(tuple(r["pair"]), r["rank"]) for r in only0}, {((4, 5), 2)})
        fields = [str(r["field"]) for r in only0]
        recovered = [r for r in v8 if r["status"] == "RECOVERED"]
        at0 = sum(r["colength"] == 0 for r in recovered)
        for name, text in self.docs[:2]:
            with self.subTest(doc=name):
                self.assertIn(f"{total} colength counts", text)
                self.assertIn(f"{len(v7)} are colength 0, where both sides are 1 by construction, "
                              f"so {total - len(v7)} are non-trivial", text)
                self.assertIn(f"(4,5) with N = 2 compares nothing else at q = {', '.join(fields[:-1])} "
                              f"and {fields[-1]}", text)
                self.assertIn(f"{len(recovered)} are RECOVERED ({at0} of them the constant 1 at "
                              f"colength 0, so {len(recovered) - at0} beyond colength 0)", text)

    def test_rows_that_need_the_formula_degree_are_said_and_marked(self):
        # Given only the bound N^2 delta + (N-1) m, the points fix a polynomial only when
        # there are bound + 1 of them. For every other RECOVERED row a second polynomial
        # within the bound, formula + prod (q - q_i), has the same values at its fields.
        v7 = {(tuple(r["pair"]), r["rank"], r["field"]): r for r in self.cert["V7"]}
        recovered = [r for r in self.cert["V8"] if r["status"] == "RECOVERED"]
        short = [r for r in recovered if r["bruteforce_points"] <= r["degree_bound"]]
        fixed = [r for r in recovered if r not in short]
        for r in short:
            with self.subTest(row=(r["pair"], r["rank"], r["colength"])):
                vanish = [1]
                for q in r["bruteforce_fields"]:
                    vanish = h._mul(vanish, [-q, 1])
                other = [x + y for x, y in itertools.zip_longest(r["formula_polynomial"], vanish, fillvalue=0)]
                self.assertNotEqual(other, r["formula_polynomial"])
                self.assertLessEqual(len(other) - 1, r["degree_bound"])
                for q in r["bruteforce_fields"]:
                    count = v7[(tuple(r["pair"]), r["rank"], q)]["bruteforce"][r["colength"]]
                    self.assertEqual(h._eval(other, Fraction(q)), count)

        def beyond_0(rows):
            return sum(r["colength"] > 0 for r in rows)

        for name, text in self.docs[:2]:
            with self.subTest(doc=name):
                self.assertIn("given the degree of the formula's polynomial, the brute-force points "
                              "determine its coefficients", text)
                self.assertIn(f"{len(fixed)} of the {len(recovered)} RECOVERED rows "
                              f"({beyond_0(fixed)} beyond colength 0)", text)
                self.assertIn(f"other {len(short)} ({beyond_0(short)} beyond colength 0)", text)
        for a, b, rank in self.cert["census"]["series"]:
            rows = [r for r in self.cert["V8"] if r["pair"] == [a, b] and r["rank"] == rank]
            done = ", ".join(f"{r['colength']} ({r['degree']})" + ("†" if r in short else "")
                             for r in rows if r["status"] == "RECOVERED")
            left = ", ".join(f"{r['colength']} ({r['degree']}; {r['bruteforce_points']})"
                             for r in rows if r["status"] == "UNDERDETERMINED")
            with self.subTest(series=(a, b, rank)):
                self.assertIn(f"| ({a},{b}) | {rank} | {done} | {left or '—'} |", self.readme)


if __name__ == "__main__":
    unittest.main()
