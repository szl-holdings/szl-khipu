"""Exact serialized research data identity across Git checkout platforms.

For signed/pinned artifacts, a model SHA binds BYTES, not a normalized JSON
object. A Windows checkout with core.autocrlf=true must not rewrite LF to
CRLF and make a correct SHA-bound model appear corrupt. No model training,
provider network calls, or publication occurs in these tests.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "model" / "training_receipt.json"
RULES = ROOT / ".gitattributes"


class ExactBytePortabilityTests(unittest.TestCase):
    def test_all_receipted_bytes_match_pinned_sha_and_size(self):
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(
            set(receipt["data"]),
            {"model/yachay_nb_v0.json", "data/synthetic_train.jsonl",
             "data/synthetic_eval.jsonl"},
        )
        for name, identity in receipt["data"].items():
            with self.subTest(path=name):
                raw = (ROOT / name).read_bytes()
                self.assertEqual(len(raw), identity["bytes"])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), identity["sha256"])
                self.assertNotIn(b"\r\n", raw)

    def test_byte_exact_files_are_exempt_from_git_eol_filters(self):
        rules = [
            line.strip() for line in RULES.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        self.assertEqual(
            set(rules),
            {"model/*.json -text", "data/*.json -text", "data/*.jsonl -text"},
        )

    def test_canonical_receipt_is_not_automatically_rewritten(self):
        raw = RECEIPT.read_bytes()
        self.assertTrue(raw.endswith(b"\n"))
        self.assertNotIn(b"\r\n", raw)
        self.assertIs(json.loads(raw)["production_qualified"], False)

    def test_data_and_provenance_arrays_are_not_promoted(self):
        receipt = json.loads(RECEIPT.read_bytes())
        self.assertEqual(receipt["training_mode"], "LOCAL_CPU_TEXT_ROUTER")
        self.assertEqual(receipt["training_examples"], 540)
        self.assertEqual(receipt["evaluation_examples"], 80)
        self.assertFalse(receipt["deployment_verified"])
        self.assertFalse(receipt["public_model_published"])
        self.assertFalse(receipt["final_model_is_1_5B"])


if __name__ == "__main__":
    unittest.main()
