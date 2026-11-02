"""ReceiptAgent selection metrics must not masquerade as an independent test."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from szl_khipu.train import receipt_agent as agent


class ReceiptAgentEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.selection = np.zeros((800, agent.FEATURE_DIM))
        self.selection[:, 0] = np.arange(800) / 1000
        self.test = np.zeros((400, agent.FEATURE_DIM))
        self.test[:, 0] = 2 + np.arange(400) / 1000

    def synth(self, n, seed):
        rows = self.selection if n == 800 else self.test
        return rows.copy(), np.zeros(len(rows), dtype=np.int64)

    def run_instrumented(self, max_steps, target, test_score):
        events = []

        def update(weights, X, y, lr):
            events.append(("update", len(X)))
            weights["b1"][0] += 1
            return 0.0

        def score(weights, X, y):
            if len(X) == 400:
                events.append(("test", len(X)))
                return test_score
            events.append(("development", len(X)))
            return min(0.5 + float(weights["b1"][0]) / 40, 1.0)

        with patch.object(agent, "synth_features", side_effect=self.synth), patch.object(
            agent, "_step", side_effect=update
        ), patch.object(agent, "agree", side_effect=score):
            weights, metrics = agent.train(max_steps=max_steps, target_agree=target)
        return weights, metrics, events

    def test_early_stop_reports_test_only_after_selection(self):
        _, metrics, events = self.run_instrumented(40, 0.9, 0.125)
        self.assertEqual(events[-1], ("test", 400))
        self.assertEqual(sum(kind == "test" for kind, _ in events), 1)
        self.assertEqual(sum(kind == "update" for kind, _ in events), 16)
        self.assertEqual(metrics["development_agree"], 0.9)
        self.assertEqual(metrics["test_agree"], 0.125)
        self.assertEqual(metrics["agree"], metrics["development_agree"])
        self.assertEqual(metrics["n_held"], metrics["n_development"])
        self.assertEqual((metrics["n_train"], metrics["n_development"], metrics["n_test"]), (600, 200, 400))

    def test_final_test_does_not_select_weights_or_attempt_count(self):
        left_w, left_metrics, left_events = self.run_instrumented(3, 1.0, 0.0)
        right_w, right_metrics, right_events = self.run_instrumented(3, 1.0, 1.0)
        for name in left_w:
            np.testing.assert_array_equal(left_w[name], right_w[name])
        self.assertEqual(left_events, right_events)
        self.assertEqual(left_events[-1], ("test", 400))
        self.assertEqual(sum(kind == "test" for kind, _ in left_events), 1)
        self.assertEqual(sum(kind == "update" for kind, _ in left_events), 12)
        self.assertEqual(left_metrics["development_agree"], right_metrics["development_agree"])
        self.assertEqual(left_metrics["test_agree"], 0.0)
        self.assertEqual(right_metrics["test_agree"], 1.0)

    def test_feature_overlap_is_rejected_before_training(self):
        # Include within-split and every cross-split pair. Labels must not make
        # identical features distinct, and -0.0 is the same feature as +0.0.
        pairs = [(0, 1), (600, 601), (800, 801), (0, 600), (0, 800), (600, 800)]
        for source, dest in pairs:
            with self.subTest(source=source, dest=dest):
                all_rows = np.vstack((self.selection, self.test))
                all_rows[dest] = all_rows[source]
                all_rows[dest, 1] = -0.0
                def synth(n, seed):
                    rows = all_rows[:800] if n == 800 else all_rows[800:]
                    labels = np.zeros(len(rows), dtype=np.int64)
                    if (dest < 800) == (n == 800):
                        labels[dest if n == 800 else dest - 800] = 1
                    return rows.copy(), labels
                with patch.object(agent, "synth_features", side_effect=synth), patch.object(agent, "_step") as step:
                    with self.assertRaisesRegex(ValueError, "duplicate feature"):
                        agent.train(max_steps=1)
                    step.assert_not_called()

    def test_export_identifies_development_alias_and_synthetic_test(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "train_and_export.py"
        spec = importlib.util.spec_from_file_location("train_and_export", script)
        exporter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(exporter)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(exporter, "ROOT", root), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(exporter.main(), 0)
            receipt = json.loads((root / "artifacts" / "TRAINING_RECEIPT.json").read_text())
            record = receipt["artifacts"]["receipt_agent.npz"]
            self.assertEqual(record["agree_role"], "development_selection")
            self.assertEqual(record["test_role"], "synthetic_post_selection")
            self.assertEqual(record["agree"], record["development_agree"])
            self.assertTrue(0 <= record["test_agree"] <= 1)
            self.assertEqual((record["n_train"], record["n_development"], record["n_test"]), (600, 200, 400))
            self.assertFalse(receipt["proven_trust"])

    def test_real_cpu_run_is_repeatable_and_keeps_kernel_authority(self):
        left_w, left = agent.train(seed=7, max_steps=2)
        right_w, right = agent.train(seed=7, max_steps=2)
        self.assertEqual(left, right)
        for name in left_w:
            np.testing.assert_array_equal(left_w[name], right_w[name])
        self.assertTrue(0 <= left["test_agree"] <= 1)
        self.assertEqual(left["kernel_wins"], 1.0)
        self.assertEqual(agent.decide(np.zeros(agent.FEATURE_DIM), left_w)["decision"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
