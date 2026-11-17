"""Khipu metadata index integrity and nonpromotion tests."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.flagship55 import public_catalog as catalog

INDEX = ROOT / "research/flagship55/public_dataset_index.v1.json"


class PublicDatasetIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source, cls.sha256, cls.metrics = catalog.read_public_catalog(INDEX)

    def altered(self):
        return copy.deepcopy(self.source)

    def deny(self, document):
        with self.assertRaises(ValueError):
            catalog.validate_public_catalog(document)

    def test_observed_public_count_and_scope(self):
        self.assertEqual(self.metrics["public_refs"], 91)
        self.assertEqual(self.metrics["status"], "PUBLIC_METADATA_REFERENCES_VALIDATED_ONLY")
        self.assertEqual(self.metrics["training_admitted"], 0)
        self.assertEqual(self.metrics["private_names_emitted"], 0)
        self.assertFalse(self.metrics["provider_revision_reobserved"])
        self.assertEqual(len(self.sha256), 64)

    def test_every_reference_is_metadata_only_and_not_admitted(self):
        for entry in self.source["all_references"]:
            self.assertEqual(entry["rights_state"], "NOT_REVIEWED")
            self.assertFalse(entry["training_admitted"])
            self.assertFalse(entry["data_bytes_inspected"])
            self.assertEqual(entry["eval_holdout_safe"], "UNVERIFIED")

    def test_public_source_lookups_never_grant_training_authority(self):
        item = catalog.find_reference(self.source, "SZLHOLDINGS/axiom-invariant-corpus-v1")
        self.assertEqual(item["revision"], "235d9c41384a627fae290aa89792ae079103b3ab")
        self.assertEqual(item["rights_state"], "NOT_REVIEWED")
        self.assertFalse(item["training_admitted"])

    def test_unknown_dataset_returns_none(self):
        self.assertIsNone(catalog.find_reference(self.source, "SZLHOLDINGS/does-not-exist"))

    def test_source_index_does_not_contain_raw_rows(self):
        self.assertEqual(set(self.source) - {
            "schema", "census_observed_at_utc", "source_private_census_sha256",
            "provider", "owner", "public_count", "private_names_emitted",
            "inaccessible_sources_inferred", "source_metadata_only",
            "scope", "approval_authority", "all_references",
        }, set())

    def test_corrupted_count_denied(self):
        d = self.altered()
        d["public_count"] += 1
        self.deny(d)

    def test_private_visibility_denied(self):
        d = self.altered()
        d["all_references"][0]["source_visibility"] = "PRIVATE"
        self.deny(d)

    def test_disallowed_training_admission_denied(self):
        d = self.altered()
        d["all_references"][1]["training_admitted"] = True
        self.deny(d)

    def test_rights_clearance_without_review_denied(self):
        d = self.altered()
        d["all_references"][0]["rights_state"] = "APPROVED"
        self.deny(d)

    def test_revision_alias_denied(self):
        d = self.altered()
        d["all_references"][0]["source_revision"] = "main"
        self.deny(d)

    def test_duplicate_id_denied(self):
        d = self.altered()
        d["all_references"][1]["id"] = d["all_references"][0]["id"]
        self.deny(d)

    def test_untrusted_extra_field_denied(self):
        d = self.altered()
        d["all_references"][0]["raw_row"] = "not for public index"
        self.deny(d)

    def test_changed_census_anchor_denied(self):
        d = self.altered()
        d["source_private_census_sha256"] = "0" * 64
        self.deny(d)

    def test_eval_holdout_claim_denied(self):
        d = self.altered()
        d["all_references"][0]["eval_holdout_safe"] = True
        self.deny(d)

    def test_source_only_public_scope_denied(self):
        d = self.altered()
        d["private_names_emitted"] = 1
        self.deny(d)


if __name__ == "__main__":
    unittest.main()
