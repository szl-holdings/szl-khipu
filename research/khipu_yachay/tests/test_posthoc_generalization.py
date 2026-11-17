"""Quality and data-custody gates for the deliberately non-blind OOD challenge."""
from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest

from scripts.score_posthoc import (
    DATA,
    DATA_SHA256,
    measure,
    read_challenge,
)

ROOT = Path(__file__).resolve().parents[1]


class PosthocGeneralizationTests(unittest.TestCase):
    def test_fixture_is_exact_pinned_and_excluded_from_training(self):
        rows = read_challenge()
        self.assertEqual(len(rows), 52)
        self.assertEqual(len(DATA_SHA256), 64)
        self.assertTrue(all(x["model_training_admitted"] is False for x in rows))
        self.assertEqual(len([x for x in rows if x["label"] == "ABSTAIN"]), 12)

    def test_stress_probe_qualifies_no_release_claim(self):
        result = measure()
        self.assertEqual(result["in_domain"], {
            "n": 40, "correct": 24, "accuracy": .6})
        self.assertEqual(result["out_of_domain"], {
            "n": 12, "correct_abstentions": 5,
            "abstention_rate": .416667})
        self.assertEqual(result["decision"], "HOLD_GENERALIZATION_NOT_ESTABLISHED")
        self.assertIs(result["model_or_dataset_publication_authorized"], False)
        self.assertIs(result["production_eligible"], False)
        self.assertIs(result["not_independent_human_review"], True)
        self.assertIs(result["model_training_performed"], False)

    def test_posthoc_is_distinct_from_developer_tuned_template_score(self):
        receipt = json.loads((ROOT / "model/training_receipt.json").read_bytes())
        value = measure()
        self.assertEqual(receipt["metrics"]["correct"], 76)
        self.assertEqual(receipt["metrics"]["n"], 80)
        self.assertEqual(receipt["metrics"]["accuracy"], .95)
        self.assertLess(value["in_domain"]["accuracy"], .95)
        self.assertEqual(value["model_sha256"],
                         receipt["data"]["model/yachay_nb_v0.json"]["sha256"])

    def test_modified_challenge_bytes_cannot_be_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "posthoc_v0.jsonl"
            candidate.write_bytes(DATA.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "IDENTITY_MISMATCH"):
                read_challenge(candidate)


if __name__ == "__main__":
    unittest.main()
