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


ROOT = Path(__file__).resolve().parents[1]


class BenchmarkTests(unittest.TestCase):
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
