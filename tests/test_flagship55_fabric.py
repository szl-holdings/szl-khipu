"""Offline Flagship55 Khipu design boundary tests, no model/network execution."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "research" / "flagship55" / "validate_manifest.py"
MANIFEST = ROOT / "research" / "flagship55" / "manifest.v0.json"
spec = importlib.util.spec_from_file_location("flagship55_design_validator", SCRIPT)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class Flagship55DesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = validator.strict_loads(MANIFEST.read_bytes())

    def data(self):
        return copy.deepcopy(self.original)

    def rejected(self, data):
        with self.assertRaises(validator.ManifestHold):
            validator.check(data)

    def test_canonical_manifest_is_design_only(self):
        result = validator.check(self.data())
        self.assertEqual(result["status"], "DESIGN_STRUCTURE_VERIFIED_ONLY")
        self.assertFalse(result["train_launch_authorized"])
        self.assertFalse(result["model_weights_created"])
        self.assertEqual(result["roles"], 3)
        self.assertEqual(result["accessible_hf_dataset_count"], 136)

    def test_duplicate_json_members_rejected(self):
        with self.assertRaises(validator.ManifestHold):
            validator.strict_loads(b'{"schema":"one","schema":"two"}')

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(validator.ManifestHold):
            validator.strict_loads(b'{"x":NaN}')

    def test_byte_budget_enforced(self):
        with self.assertRaises(validator.ManifestHold):
            validator.strict_loads(b"a" * (validator.MAX_BYTES + 1))

    def test_training_claim_cannot_be_substituted(self):
        obj = self.data()
        obj["status"] = "TRAINED"
        self.rejected(obj)

    def test_three_experts_required(self):
        obj = self.data()
        obj["topology"]["experts"].pop()
        self.rejected(obj)

    def test_model_weights_cannot_be_claimed_present(self):
        obj = self.data()
        obj["topology"]["experts"][0]["weights_revision"] = "a" * 40
        self.rejected(obj)

    def test_proposed_expert_cannot_be_claimed_trained(self):
        obj = self.data()
        obj["topology"]["experts"][1]["trained"] = True
        self.rejected(obj)

    def test_external_referee_authority_is_mandatory(self):
        obj = self.data()
        obj["topology"]["proof_authority"] = "LEARNED_SKEPTIC"
        self.rejected(obj)

    def test_locked_set_cannot_expand(self):
        obj = self.data()
        obj["math"]["locked_ids"].append("F23")
        self.rejected(obj)

    def test_unconditional_uniqueness_cannot_be_proven(self):
        obj = self.data()
        obj["math"]["lambda_uniqueness"] = "PROVEN"
        self.rejected(obj)

    def test_guard_shutdown_must_remain_unobserved(self):
        obj = self.data()
        obj["baseline"]["actual_shutdown"] = "DONE"
        self.rejected(obj)

    def test_hf_metadata_census_counts_must_balance(self):
        obj = self.data()
        obj["dataset_census"]["private"] = 44
        self.rejected(obj)

    def test_empty_or_exhausted_census_cap_rejected(self):
        obj = self.data()
        obj["dataset_census"]["returned"] = 501
        self.rejected(obj)

    def test_no_claim_all_global_data(self):
        obj = self.data()
        obj["dataset_census"]["all_global_data_covered"] = True
        self.rejected(obj)

    def test_no_dataset_training_authority(self):
        obj = self.data()
        obj["public_dataset_examples"][0]["training_admitted"] = True
        self.rejected(obj)

    def test_blocklisted_quant_dataset_cannot_be_unblocked(self):
        obj = self.data()
        for item in obj["public_dataset_examples"]:
            if item["repo"] == "SZLHOLDINGS/szl-quant-sft-v1":
                item["role"] = "SFT_REVIEW"
        self.rejected(obj)

    def test_no_duplicate_dataset_ids(self):
        obj = self.data()
        obj["public_dataset_examples"].append(copy.deepcopy(obj["public_dataset_examples"][0]))
        self.rejected(obj)

    def test_unpinned_source_rejected(self):
        obj = self.data()
        obj["owner_roots"][0]["revision"] = "main"
        self.rejected(obj)

    def test_research_manifest_cannot_self_authorize(self):
        obj = self.data()
        obj["gates"]["auto_train"] = True
        self.rejected(obj)

    def test_publication_cannot_self_authorize(self):
        obj = self.data()
        obj["gates"]["auto_publish"] = True
        self.rejected(obj)

    def test_readonly_source_imports_no_model_or_network(self):
        text = SCRIPT.read_text(encoding="utf-8")
        for forbidden in ("torch.load(", "pickle.load(", "requests.", "HfApi(",
                          "subprocess.", "trust_remote_code=True", "model.generate("):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
