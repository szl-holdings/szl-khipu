#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Offline, exact tests for the HJO Loom engine and holographic GLB writer."""
import hashlib
import importlib.util
import itertools
import json
import math
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
        finally:
            h._galois_field.cache_clear()
        self.assertEqual(h.galois_field(4).mul[2][2], 3)              # x * x = x + 1

    def test_unsupported_orders_fail_closed(self):
        for q in (0, 1, 6, 10, 16, True, 4.0, "4"):
            with self.subTest(q=q), self.assertRaises(h.HjoHold):
                h.galois_field(q)


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

    def test_check_refuses_wrong_schema_without_rebuilding(self):
        out = subprocess.run([sys.executable, str(BUILDER), "--v2", "--check", str(CERT)],
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 3)
        self.assertIn("SCHEMA_MISMATCH", out.stdout)
        out = subprocess.run([sys.executable, str(BUILDER), "--v2", "--write", str(CERT2)],
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 3)
        self.assertIn("REFUSE_OVERWRITE", out.stdout)


if __name__ == "__main__":
    unittest.main()
