# SPDX-License-Identifier: Apache-2.0
"""Exercise the local measurement CLI without Hub access or large allocations."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


class BenchmarkTests(unittest.TestCase):
    def test_retained_cpu_receipt_is_complete_and_bound_to_this_implementation(self):
        receipt = ROOT / "benchmarks/results/yarqa-cpu-2026-09-19.json"
        report = json.loads(receipt.read_text(encoding="utf-8"))
        digest = report.pop("receipt_sha256")
        canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
        self.assertEqual(digest, hashlib.sha256(canonical.encode()).hexdigest())
        self.assertEqual(digest, "300283554146b09a6b4b7ecf8abd5d24a6c1491ae82e5b60694d3e4e5f61338d")
        self.assertEqual(report["source_revision"], "0e56e9a8451294e462160d64819add10e03f5dde")
        self.assertIs(report["tracked_worktree_dirty"], False)
        # These are the exact measured implementation and benchmark bytes;
        # a future source change needs its own receipt, not a relabeled old run.
        for name, expected in report["source_files_sha256"].items():
            self.assertEqual(expected, hashlib.sha256((ROOT / name).read_bytes()).hexdigest())
        expected_cases = {(s, c, seed) for s in (256, 1024, 4096)
                          for c in (1, 4, 16) for seed in (7, 17, 42)}
        cases = report["cases"]
        self.assertEqual(len(cases), len(expected_cases))
        self.assertEqual({(r["sequence"], r["canals"], r["seed"]) for r in cases}, expected_cases)
        self.assertEqual(report["protocol"]["warmup"], 1)
        self.assertEqual(report["protocol"]["samples"], 3)
        self.assertIsNone(report["protocol"]["energy_joules"])
        self.assertIsNone(report["protocol"]["peak_process_memory_bytes"])
        self.assertEqual(report["hardware"]["gpu"], "NOT_EXERCISED")
        for row in cases:
            self.assertEqual(set(row["methods"]),
                             {"legacy_diagnostics", "dense_masked_output", "block_local_output"})
            for metrics in row["methods"].values():
                self.assertIs(metrics["correctness_parity_pass"], True)
                self.assertEqual(len(metrics["samples_us"]), 3)
                self.assertTrue(all(np.isfinite(v) and v > 0 for v in metrics["samples_us"]))
                for percentile in (50, 95):
                    self.assertEqual(metrics[f"p{percentile}_us"],
                                     float(np.percentile(metrics["samples_us"], percentile)))
        slowdowns = [row for row in cases if row["methods"]["block_local_output"]["p50_us"]
                     > row["methods"]["dense_masked_output"]["p50_us"]]
        self.assertEqual([(r["sequence"], r["canals"], r["seed"]) for r in slowdowns],
                         [(1024, 1, 42)])

    def command(self, output):
        return [sys.executable, "-I", "-B", str(ROOT / "benchmarks/yarqa_cpu.py"),
                "--seq", "8", "--canals", "2", "--seeds", "7", "--dim", "4",
                "--warmup", "0", "--samples", "3", "--out", str(output)]

    def test_receipt_integrity_source_binding_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "receipt.json"
            result = subprocess.run(self.command(output), capture_output=True, text=True,
                                    check=False, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            original = output.read_bytes()
            report = json.loads(original)
            digest = report.pop("receipt_sha256")
            canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
            self.assertEqual(digest, hashlib.sha256(canonical.encode()).hexdigest())
            self.assertEqual(report["hardware"]["gpu"], "NOT_EXERCISED")
            self.assertIsNone(report["protocol"]["energy_joules"])
            self.assertEqual(len(report["cases"]), 1)
            for name, expected in report["source_files_sha256"].items():
                self.assertEqual(expected, hashlib.sha256((ROOT / name).read_bytes()).hexdigest())
            for metrics in report["cases"][0]["methods"].values():
                self.assertTrue(metrics["correctness_parity_pass"])
                self.assertEqual(len(metrics["samples_us"]), 3)
            again = subprocess.run(self.command(output), capture_output=True, text=True,
                                   check=False, timeout=30)
            self.assertNotEqual(again.returncode, 0)
            self.assertIn("output already exists", again.stderr)
            self.assertEqual(output.read_bytes(), original)

    def test_invalid_protocol_does_not_write_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "invalid.json"
            for extra in (["--samples", "2"], ["--seq", "8193"], ["--dim", "0"]):
                result = subprocess.run(self.command(output) + extra, capture_output=True,
                                        text=True, check=False, timeout=30)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
