"""Hermetic HJO-source-profile and bounded cylindric dual-enumerator tests."""
from __future__ import annotations

import hashlib
import math
import unittest
from unittest.mock import patch

from research.hjo_profile import cylindric as h


class HJOCylindricDefinitionTests(unittest.TestCase):
    def test_exact_profile_matches_pinned_challenge_formula(self):
        targets = {
            (2, 3): (1, 2),
            (3, 4): (1, 1, 2),
            (3, 5): (1, 2, 2),
            (3, 7): (2, 2, 3),
            (4, 5): (1, 1, 1, 2),
            (4, 7): (1, 2, 2, 2),
        }
        for (a, b), expected in targets.items():
            with self.subTest(a=a, b=b):
                self.assertEqual(h.profile(a, b), expected)
                self.assertEqual(sum(expected), b)
                for i in range(a * 3):
                    v = ((i+1)*b)//a - (i*b)//a
                    self.assertEqual(v, expected[i % a])

    def test_zero_rank_and_zero_volume_no_missing_data(self):
        zero_rank = h.witness(3, 5, 0, 8)
        self.assertEqual(zero_rank["cylindric_coefficients_by_volume"], [1]+[0]*8)
        self.assertIsNone(zero_rank["example_cylindric_rows"])
        zero_volume = h.witness(3, 5, 2, 0)
        self.assertEqual(zero_volume["cylindric_coefficients_by_volume"], [1])
        self.assertIsNone(zero_volume["example_cylindric_rows"])
        self.assertTrue(zero_rank["two_finite_enumerators_agree"])

    def test_small_exact_independently_counted_controls(self):
        self.assertEqual(
            h.witness(2, 3, 1, 4)["cylindric_coefficients_by_volume"],
            [1, 2, 2, 2, 2],
        )
        self.assertEqual(
            h.witness(3, 5, 2, 6)["cylindric_coefficients_by_volume"],
            [1, 3, 8, 14, 25, 36, 52],
        )
        self.assertEqual(
            h.witness(4, 7, 3, 8)["cylindric_coefficients_by_volume"],
            [1, 4, 13, 33, 75, 152, 288, 508, 854],
        )

    def test_all_admitted_pairs_two_algorithms_agree(self):
        for a in range(2, h.MAX_A + 1):
            for b in range(a+1, h.MAX_B + 1):
                if math.gcd(a, b) != 1:
                    continue
                with self.subTest(a=a, b=b):
                    r = h.witness(a, b, 2, 6)
                    self.assertEqual(len(r["cylindric_coefficients_by_volume"]), 7)
                    self.assertEqual(r["profile_sum_equals_b"], True)
                    self.assertTrue(r["profile_period_a_checked"])
                    self.assertTrue(r["two_finite_enumerators_agree"])
                    self.assertEqual(r["cylindric_coefficients_by_volume"][0], 1)

    def test_lean_source_and_qualification_scope_are_exact(self):
        r = h.witness(3, 5, 2, 6)
        self.assertEqual(r["source_revision"], "6a58dfa6ab98bd35d841cb2cf8fd9081f62fad03")
        self.assertEqual(r["challenge_git_blob_sha"], "f641f5432891737d7b8ad6b0bf21a663dcf32901")
        self.assertEqual(r["challenge_sha256"], "dc96a4b2f1bdeda0027968924ba480f8fc0e29e34eb56fb6cfbdbce2e235b48e")
        self.assertFalse(r["HJO_rank_N_polynomial_computed"])
        self.assertFalse(r["HJO_equality_verified_here"])
        self.assertFalse(r["Lean_kernel_replayed"])
        self.assertTrue(r["challenge_template_sorry_is_not_proof"])
        self.assertFalse(r["historical_khipu_encoding_inferred"])
        self.assertFalse(r["new_infinite_theorem_proved"])
        self.assertFalse(r["signature_verified"])
        self.assertEqual(r["production_qualification"], "NOT_ASSESSED")

    def test_domain_separated_sha256_is_reproducible(self):
        a, b = h.witness(3, 7, 2, 6), h.witness(3, 7, 2, 6)
        self.assertEqual(a, b)
        core = {k:v for k,v in a.items() if k != "sha256"}
        self.assertEqual(
            hashlib.sha256(h.DOMAIN + h.canonical(core)).hexdigest(), a["sha256"]
        )
        self.assertNotEqual(a["sha256"], h.witness(3, 5, 2, 6)["sha256"])

    def test_outgoing_is_truly_cylindric_not_unrestricted(self):
        # Under c_i=1, following row [2,2] has shifted second entry 2.
        self.assertFalse(h._outgoing_direct((), (2, 2), 1))
        self.assertFalse(h._transfer_allowed((), (2, 2), 1))
        self.assertTrue(h._outgoing_direct((2,), (2, 2), 1))
        self.assertTrue(h._transfer_allowed((2,), (2, 2), 1))
        self.assertTrue(h._outgoing_direct((1,), (), 1))
        self.assertTrue(h._transfer_allowed((1,), (), 1))

    def test_direct_transfer_mismatch_fails_closed(self):
        with patch.object(h, "_transfer_coefficients", return_value=(0, 0, 0)):
            with self.assertRaisesRegex(
                h.Hold, "INDEPENDENT_CYLINDRIC_COUNT_DISAGREEMENT_N_0"
            ):
                h.witness(2, 3, 1, 2)

    def test_bad_inputs_or_out_of_domain_hold_not_silent(self):
        invalid = [
            (1, 3, 1, 6), (5, 7, 1, 6), (2, 2, 1, 6),
            (3, 6, 1, 6), (2, 4, 1, 6), (3, 10, 1, 6),
            (True, 3, 1, 6), ("3", 5, 1, 6), (3, 5, True, 6),
            (3, 5, -1, 6), (3, 5, 4, 6), (3, 5, 1, 9),
            (3, 5, 1, -1), (3, 5, 1, 6.0),
        ]
        for args in invalid:
            with self.subTest(args=args), self.assertRaises(h.Hold):
                h.witness(*args)


if __name__ == "__main__":
    unittest.main()
