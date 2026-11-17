"""No credentials, no GPUs: independent control and falsification tests."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

from research.rr_discovery import learner as subject

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "research/rr_discovery/receipts/sequence_scout_v1.json"


class SequenceScoutTests(unittest.TestCase):
    def test_actual_fitted_models_are_classical_modulo_five(self):
        result = subject.run_experiment()
        self.assertEqual(result["status"], "FINITE_RESEARCH_CONTROL_MATCH")
        rows = result["cases"]
        self.assertEqual([r["case"] for r in rows], ["RR1", "RR2"])
        for row, expected in zip(rows, [[1, 4], [2, 3]]):
            model = row["training"]["model"]
            self.assertEqual(model, {"modulus": 5, "residues": expected})
            self.assertEqual(row["training"]["status"], "TRAINING_FIT_EXACT")
            self.assertEqual(row["training"]["train_rows"], 33)
            self.assertEqual(row["training"]["candidate_hypotheses_tested"], 1573)
            # Multiple matching models are disclosed, not called unique.
            self.assertEqual(row["training"]["candidate_matches"], 2)
            score = row["evaluation"]
            self.assertEqual(score["status"], "FINITE_HOLDOUT_MATCH")
            self.assertEqual((score["exact_matches"], score["test_rows"]), (96, 96))
            self.assertLess(score["training_last_value_baseline_exact_matches"], 96)
            self.assertEqual(score["test_range"], [33, 128])

    def test_tampered_training_does_not_yield_any_hypothesis(self):
        train = list(subject.reference_coefficients("RR1", 32))
        train[6] += 1
        trained = subject.fit(tuple(train))
        self.assertEqual(trained["status"], "HOLD_NO_CANDIDATE")
        self.assertIsNone(trained["model"])
        self.assertEqual(
            subject.evaluate("RR1", trained)["status"], "NOT_EVALUATED"
        )

    def test_model_tamper_refused_prior_to_heldout(self):
        model = subject.fit(subject.reference_coefficients("RR1", 32))
        model["model"]["residues"] = [1, 3]
        with self.assertRaisesRegex(subject.EvidenceHold, "TRAINED_MODEL_DIGEST_MISMATCH"):
            subject.evaluate("RR1", model)

    def test_wrong_modular_prediction_is_falsified(self):
        model = subject.fit(subject.reference_coefficients("RR1", 32))
        model["model"] = {"modulus": 5, "residues": [1, 3]}
        model["model_sha256"] = __import__("hashlib").sha256(
            subject.DOMAIN + subject.canonical(model["model"])
        ).hexdigest()
        verdict = subject.evaluate("RR1", model)
        self.assertEqual(verdict["status"], "FINITE_HOLDOUT_MISMATCH")
        self.assertLess(verdict["exact_matches"], verdict["test_rows"])
        self.assertIsNotNone(verdict["first_mismatch_degree"])

    def test_invalid_and_underspecified_training_is_refused(self):
        samples = [
            (),
            (1,),
            tuple([1] + [0] * 31),
            tuple([0] * 33),
            tuple([1] + [0] * 31 + [-1]),
            tuple([1] + [0] * 31 + [True]),
            [1] * 33,
        ]
        for invalid in samples:
            with self.subTest(sample=repr(invalid)[:20]), self.assertRaises(subject.EvidenceHold):
                subject.fit(invalid)

    def test_invalid_parameter_family_is_bounded(self):
        invalid = [
            (1, (1, 2), 32),
            (13, (1, 2), 32),
            (5, (0, 1), 32),
            (5, (1, 1), 32),
            (5, (2, 1), 32),
            (5, (1, 2, 3, 4, 5), 32),
            (5, (1, 4), 129),
            (True, (1, 4), 32),
        ]
        for args in invalid:
            with self.subTest(args=args), self.assertRaises(subject.EvidenceHold):
                subject.product_coefficients(*args)

    def test_per_degree_oracles_match_finite_range(self):
        for case, residues in (("RR1", (1, 4)), ("RR2", (2, 3))):
            count = subject.reference_coefficients(case, 128)
            product = subject.product_coefficients(5, residues, 128)
            self.assertEqual(count, product)
            self.assertEqual(count[0], 1)

    def test_repeatability_and_explicit_nonclaims(self):
        one, two = subject.run_experiment(), subject.run_experiment()
        self.assertEqual(one, two)
        self.assertEqual(one["negative_control"]["result"], "HOLD_NO_CANDIDATE")
        self.assertFalse(one["historical_khipu_decipherment"])
        self.assertFalse(one["new_infinite_identity_proved"])
        self.assertFalse(one["external_Lean_replay_completed"])
        self.assertFalse(one["signature_verified"])
        self.assertEqual(one["production_qualification"], "NOT_ASSESSED")
        core = {k: v for k, v in one.items() if k != "sha256"}
        self.assertEqual(
            __import__("hashlib").sha256(
                subject.DOMAIN + subject.canonical(core)
            ).hexdigest(), one["sha256"]
        )

    def test_pinned_public_receipt_replays_byte_exactly(self):
        expected = (
            json.dumps(subject.run_experiment(), sort_keys=True, indent=2, ensure_ascii=True)
            + "\n"
        ).encode("ascii")
        self.assertEqual(RECEIPT.read_bytes(), expected)

    def test_cli_check_positive_and_corrupt_receipt_hold(self):
        script = ROOT / "research/rr_discovery/learner.py"
        result = subprocess.run(
            [sys.executable, str(script), "--check", str(RECEIPT)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue(json.loads(result.stdout)["receipt_checked"])
        with self.subTest("corruption"), __import__("tempfile").TemporaryDirectory() as td:
            corrupt = Path(td) / "receipt.json"
            corrupt.write_bytes(RECEIPT.read_bytes() + b"unexpected")
            negative = subprocess.run(
                [sys.executable, str(script), "--check", str(corrupt)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(negative.returncode, 3)
            self.assertEqual(
                json.loads(negative.stdout)["reason"], "RECEIPT_REPRODUCIBILITY_MISMATCH"
            )


if __name__ == "__main__":
    unittest.main()
