#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Offline, exact tests for the HJO Loom engine and holographic GLB writer."""
import hashlib
import json
import math
import subprocess
import sys
import unittest
from fractions import Fraction
from pathlib import Path

from szl_khipu import hjo_loom as h
from szl_khipu import holo_glb as g

ROOT = Path(__file__).resolve().parents[1]
CERT = ROOT / "research" / "hjo_loom" / "hjo_certificate_v1.json"


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


if __name__ == "__main__":
    unittest.main()
