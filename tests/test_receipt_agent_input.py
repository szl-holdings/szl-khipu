# SPDX-License-Identifier: Apache-2.0
"""Malformed features must never turn the advisory receipt classifier into ALLOW."""
import unittest
from unittest.mock import patch

import numpy as np

from szl_khipu.train import receipt_agent as agent


class ReceiptFeatureAdmissionTests(unittest.TestCase):
    @staticmethod
    def allowed():
        features = np.ones(agent.FEATURE_DIM, dtype=np.float64)
        features[1] = 0.0
        features[8] = 0.0
        return features

    def test_valid_features_keep_existing_rule_labels(self):
        features = self.allowed()
        self.assertEqual(agent.rule_check(features), agent.ALLOW)
        for index, expected in ((7, agent.WARN), (2, agent.ESCALATE), (9, agent.BLOCKED)):
            modified = features.copy()
            modified[index] = 0.0
            self.assertEqual(agent.rule_check(modified), expected)

    def test_every_nonfinite_feature_is_blocked_even_when_finite_flag_claims_true(self):
        for value in (np.nan, np.inf, -np.inf):
            for index in range(agent.FEATURE_DIM):
                with self.subTest(value=value, index=index):
                    features = self.allowed()
                    features[index] = value
                    self.assertEqual(agent.rule_check(features), agent.BLOCKED)

    def test_non_numeric_and_wrong_size_inputs_are_blocked(self):
        for features in (None, [], [1.0] * 23, [1.0] * 25, ["not-a-number"] * 24,
                         [[1.0], [1.0, 2.0]], [10**1000] * 24):
            with self.subTest(kind=type(features).__name__):
                self.assertEqual(agent.rule_check(features), agent.BLOCKED)

    def test_complex_features_are_rejected_before_lossy_float_conversion(self):
        for imaginary in (0.0, 1.0, np.nan, np.inf, -np.inf):
            with self.subTest(imaginary=imaginary):
                features = self.allowed().astype(np.complex128)
                features[0] = complex(1.0, imaginary)
                self.assertEqual(agent.rule_check(features), agent.BLOCKED)
                with patch.object(agent, "predict", side_effect=AssertionError("advisory must not run")):
                    self.assertEqual(agent.decide(features, {})["decision"], "BLOCKED")

    def test_invalid_features_never_invoke_advisory_model(self):
        features = self.allowed()
        features[0] = np.nan
        for invalid in (features, None, [1.0] * 23, ["invalid"] * 24):
            with self.subTest(kind=type(invalid).__name__):
                with patch.object(agent, "predict", side_effect=AssertionError("advisory must not run")):
                    result = agent.decide(invalid, weights={})
                self.assertEqual(result["kernel"], "BLOCKED")
                self.assertEqual(result["decision"], "BLOCKED")
                self.assertTrue(result["advisory"])
                self.assertIsNone(result["surrogate"])
                self.assertIsNone(result["agree"])
                self.assertIn("invalid", result["reason"])

    def test_valid_features_preserve_advisory_but_kernel_wins(self):
        features = self.allowed()
        with patch.object(agent, "predict", return_value=agent.BLOCKED) as predict:
            result = agent.decide(features, weights={})
        predict.assert_called_once()
        self.assertEqual(result["decision"], "ALLOW")
        self.assertEqual(result["surrogate"], "BLOCKED")
        self.assertFalse(result["agree"])


if __name__ == "__main__":
    unittest.main()
