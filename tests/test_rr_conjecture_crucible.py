"""Hermetic, independent exact math and falsification admission tests."""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from research.rr_discovery import falsifier as f
from research.rr_discovery import learner as scout

ROOT = Path(__file__).resolve().parents[1]


class ConjectureCrucibleTests(unittest.TestCase):
    def test_three_classical_oracles_agree_to_256(self):
        for case, residues in (("RR1", (1, 4)), ("RR2", (2, 3))):
            with self.subTest(case=case):
                a = f.qseries_coefficients(case, 256)
                b = f.gap_coefficients(case, 256)
                c = f.modular_coefficients(5, residues, 256)
                self.assertEqual(a, b)
                self.assertEqual(b, c)
                self.assertEqual(a[:129], scout.reference_coefficients(case, 128))
                self.assertEqual(a[0], 1)
                r = f.falsify(case, 5, residues, 256)
                self.assertEqual(r["status"], "FINITE_MATCH_NOT_A_PROOF")
                self.assertEqual(r["coefficients_checked"], 257)
                self.assertIsNone(r["first_counterexample"])
                self.assertFalse(r["infinite_identity_proved_here"])
                self.assertFalse(r["hjo_general_torus_knot_theorem_tested"])

    def test_false_proposal_returns_specific_counterexample(self):
        r = f.falsify("RR1", 5, (1, 3), 256)
        self.assertEqual(r["status"], "FINITE_COUNTEREXAMPLE")
        self.assertEqual(r["first_counterexample"]["degree"], 3)
        self.assertEqual(r["first_counterexample"]["expected_gap_and_qseries_count"], 1)
        self.assertEqual(r["first_counterexample"]["proposed_product_count"], 2)
        self.assertEqual(
            r["first_counterexample"]["gap_partition_examples_ascending"], [[3]]
        )
        self.assertEqual(
            r["first_counterexample"]["proposed_modular_partition_examples_ascending"],
            [[1, 1, 1], [3]],
        )
        self.assertTrue(r["first_counterexample"]["examples_are_exhaustive"])

    def test_false_proposal_not_yet_refuted_must_not_claim_theorem(self):
        short = f.falsify("RR1", 5, (1, 3), 2)
        self.assertEqual(short["status"], "FINITE_MATCH_NOT_A_PROOF")
        self.assertIsNone(short["first_counterexample"])
        longer = f.falsify("RR1", 5, (1, 3), 3)
        self.assertEqual(longer["status"], "FINITE_COUNTEREXAMPLE")

    def test_domain_separated_receipt_digest(self):
        receipt = f.falsify("RR2", 5, (2, 3), 128)
        core = {k: v for k, v in receipt.items() if k != "sha256"}
        self.assertEqual(
            hashlib.sha256(f.DOMAIN + f.canonical(core)).hexdigest(), receipt["sha256"]
        )
        self.assertFalse(receipt["model_training_performed"])
        self.assertFalse(receipt["signature_verified"])
        self.assertFalse(receipt["lean_proof_replayed"])
        self.assertEqual(receipt["production_qualification"], "NOT_ASSESSED")

    def test_residue_string_strict_encoding(self):
        self.assertEqual(f.parse_residues("1,4"), (1, 4))
        self.assertEqual(f.parse_residues("2"), (2,))
        invalid = ["", "0", "1,1", "4,1", " 1,4", "1,4 ", "1;4", "01,4",
                   "1,04", "1,2,3,4,5", "\N{ZERO WIDTH JOINER}", None, 4, True]
        for x in invalid:
            with self.subTest(x=x), self.assertRaises(f.Hold):
                f.parse_residues(x)

    def test_parameter_budget_and_types_fail_closed(self):
        cases = [
            ("RR3", 5, (1, 4), 128),
            ([], 5, (1, 4), 128),
            ("RR1", True, (1, 4), 128),
            ("RR1", 1, (1,), 128),
            ("RR1", 13, (1,), 128),
            ("RR1", 5, (0, 4), 128),
            ("RR1", 5, (1, 1), 128),
            ("RR1", 5, (4, 1), 128),
            ("RR1", 5, (1, 5), 128),
            ("RR1", 5, (1, 2, 3, 4, 5), 128),
            ("RR1", 5, [1, 4], 128),
            ("RR1", 5, (1, 4), True),
            ("RR1", 5, (1, 4), 0),
            ("RR1", 5, (1, 4), 257),
            ("RR1", 5, (1, 4), 12.5),
        ]
        for args in cases:
            with self.subTest(args=args), self.assertRaises(f.Hold):
                f.falsify(*args)

    def test_oracle_disagreement_refuses_evidence(self):
        with patch.object(f, "qseries_coefficients", return_value=(99, 99)):
            with self.assertRaisesRegex(f.Hold, "INDEPENDENT_ORACLE_DISAGREEMENT"):
                f.falsify("RR1", 5, (1, 4), 1)

    def test_repeatability_and_cli_negative(self):
        a, b = f.falsify("RR1", 5, (1, 4), 192), f.falsify("RR1", 5, (1, 4), 192)
        self.assertEqual(a, b)
        script = ROOT / "research/rr_discovery/falsifier.py"
        result = subprocess.run(
            [sys.executable, str(script), "--case", "RR1", "--modulus", "5",
             "--residues", "1,3", "--limit", "256"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["first_counterexample"]["degree"], 3)
        denied = subprocess.run(
            [sys.executable, str(script), "--case", "RR1", "--modulus", "99",
             "--residues", "1", "--limit", "256"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(denied.returncode, 3)
        self.assertEqual(json.loads(denied.stdout)["status"], "HOLD")


if __name__ == "__main__":
    unittest.main()
