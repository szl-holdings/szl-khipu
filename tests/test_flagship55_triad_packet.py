"""Failure-focused tests for the offline Flagship55 triad planning contract."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.flagship55 import triad_packet as t
MANIFEST = ROOT / "research/flagship55/manifest.v0.json"
EXAMPLE = ROOT / "research/flagship55/example-triad-request.json"


class TriadPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest, _ = t.read_json(MANIFEST)
        cls.manifest_digest = hashlib.sha256(t._canonical(cls.manifest)).hexdigest()
        cls.example, _ = t.read_json(EXAMPLE)

    def request(self):
        return copy.deepcopy(self.example)

    def manifest(self):
        return copy.deepcopy(self.manifest_data)

    def fail_request(self, request):
        with self.assertRaises((t.ContractHold, ValueError)):
            t.make_packet(self.manifest_data, self.manifest_digest, request)

    @property
    def manifest_data(self):
        return type(self).manifest

    def packet(self, req=None, manifest=None):
        return t.make_packet(
            manifest if manifest is not None else self.manifest_data,
            self.manifest_digest,
            req if req is not None else self.request(),
        )

    def test_canonical_packet_has_three_unexecuted_roles_and_zero_authority(self):
        result = self.packet()
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(len(result["roles"]), 3)
        self.assertEqual(
            [x["role"] for x in result["roles"]],
            ["YACHAY_TEACHER", "WILLAY_GUIDE", "KHIPU_SKEPTIC"],
        )
        for role in result["roles"]:
            self.assertIsNone(role["model_revision"])
            self.assertIsNone(role["output"])
            self.assertIn("NOT_EXECUTED", role["execution_status"])
        for key in ("training_authority", "inference_authority", "publication_authority"):
            self.assertEqual(result[key], "NONE")
        self.assertFalse(result["raw_source_rows_included"])
        self.assertEqual(result["independent_lean_referee"], "NOT_RUN")
        self.assertEqual(result["signing_status"], "UNSIGNED")

    def test_packet_is_repeatably_hashed_without_claiming_signature(self):
        one = self.packet()
        two = self.packet()
        self.assertEqual(one, two)
        self.assertRegex(one["packet_sha256"], r"^[0-9a-f]{64}$")

    def test_no_unreviewed_free_text_field_passes(self):
        request = self.request()
        request["raw_question"] = "private patient data"
        self.fail_request(request)

    def test_f23_counterexample_cannot_be_promoted_to_proof(self):
        request = self.request()
        request["claim_id"] = "F23"
        result = self.packet(request)
        self.assertEqual(
            result["claim_scope"], "UNCONDITIONAL_LAMBDA_UNIQUENESS_REFUTED_AS_STATED"
        )
        self.assertEqual(result["independent_lean_referee"], "NOT_RUN")

    def test_unknown_theorem_is_rejected(self):
        request = self.request()
        request["claim_id"] = "F99"
        self.fail_request(request)

    def test_unsupported_request_types_are_rejected(self):
        for bad in (None, [], "hello", 1):
            with self.subTest(bad=bad), self.assertRaises(t.ContractHold):
                t.make_packet(self.manifest_data, self.manifest_digest, bad)

    def test_source_must_be_exact_pinned_id(self):
        request = self.request()
        request["source_refs"][0]["revision"] = "main"
        self.fail_request(request)

    def test_source_head_drift_is_denied(self):
        request = self.request()
        request["source_refs"][0]["revision"] = "0" * 40
        self.fail_request(request)

    def test_source_unlisted_private_or_unknown_denied(self):
        request = self.request()
        request["source_refs"][0]["repo"] = "SZLHOLDINGS/unknown-private"
        self.fail_request(request)

    def test_blocklisted_quant_dataset_is_not_admitted(self):
        request = self.request()
        for row in self.manifest_data["public_dataset_examples"]:
            if row["repo"] == "SZLHOLDINGS/szl-quant-sft-v1":
                request["source_refs"] = [
                    {"repo": row["repo"], "revision": row["revision"]}
                ]
                break
        self.fail_request(request)

    def test_unreviewed_license_dataset_is_not_admitted(self):
        request = self.request()
        for row in self.manifest_data["public_dataset_examples"]:
            if row["role"] == "RIGHTS_UNKNOWN_REVIEW":
                request["source_refs"] = [
                    {"repo": row["repo"], "revision": row["revision"]}
                ]
                break
        self.fail_request(request)

    def test_duplicate_sources_are_rejected(self):
        request = self.request()
        request["source_refs"].append(copy.deepcopy(request["source_refs"][0]))
        self.fail_request(request)

    def test_empty_sources_are_unavailable(self):
        request = self.request()
        request["source_refs"] = []
        self.fail_request(request)

    def test_source_cap_is_enforced(self):
        request = self.request()
        request["source_refs"] = [copy.deepcopy(request["source_refs"][0])] * 9
        self.fail_request(request)

    def test_payload_with_unapproved_manifest_is_rejected(self):
        manifest = copy.deepcopy(self.manifest_data)
        manifest["gates"]["auto_train"] = True
        with self.assertRaises(ValueError):
            self.packet(manifest=manifest)

    def test_manifest_hash_required(self):
        with self.assertRaises(t.ContractHold):
            t.make_packet(self.manifest_data, "main", self.request())

    def test_spoofed_valid_digest_is_denied(self):
        with self.assertRaises(t.ContractHold):
            t.make_packet(self.manifest_data, "0" * 64, self.request())

    def test_packet_cannot_relabel_source_rights(self):
        request = self.request()
        request["source_refs"][0]["training_rights"] = "APPROVED"
        self.fail_request(request)

    def test_json_parser_rejects_duplicate_members(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root) / "x.json"
            p.write_bytes(b'{"schema":"a","schema":"b"}')
            with self.assertRaises(t.ContractHold):
                t.read_json(p)

    def test_json_parser_rejects_nan(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root) / "x.json"
            p.write_bytes(b'{"p":NaN}')
            with self.assertRaises(t.ContractHold):
                t.read_json(p)

    def test_json_parser_rejects_oversize(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root) / "x.json"
            p.write_bytes(b"x" * (t.MAX_INPUT_BYTES + 1))
            with self.assertRaises(t.ContractHold):
                t.read_json(p)

    def test_read_json_rejects_directory(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(t.ContractHold):
                t.read_json(Path(root))

    def test_empty_risk_denominator_is_unavailable_not_zero(self):
        result = t.synthetic_risk_coverage([
            {"id":"synthetic-abstain", "category":"OPEN_PROBLEM", "outcome":"ABSTAIN"},
        ])
        self.assertEqual(result["overall"]["coverage"], 0)
        self.assertIsNone(result["overall"]["selective_risk"])
        self.assertEqual(result["overall"]["selective_risk_status"],
                         "UNAVAILABLE_ZERO_ANSWERED")
        self.assertFalse(result["heldout_independent"])
        self.assertFalse(result["model_quality_qualified"])

    def test_mixed_risk_counts_and_category_denominators(self):
        rows = [
            {"id":"c1","category":"ANSWERABLE","outcome":"CORRECT"},
            {"id":"c2","category":"ANSWERABLE","outcome":"INCORRECT"},
            {"id":"c3","category":"ANSWERABLE","outcome":"ABSTAIN"},
            {"id":"c4","category":"REFUTED_AS_STATED","outcome":"ABSTAIN"},
        ]
        result = t.synthetic_risk_coverage(rows)
        self.assertEqual(result["overall"]["answered"], 2)
        self.assertEqual(result["overall"]["wrong"], 1)
        self.assertEqual(result["overall"]["coverage"], 0.5)
        self.assertEqual(result["overall"]["selective_risk"], 0.5)
        self.assertEqual(result["by_category"]["ANSWERABLE"]["total"], 3)
        self.assertIsNone(result["by_category"]["OPEN_PROBLEM"]["coverage"])

    def test_risk_empty_sample_is_unavailable(self):
        with self.assertRaises(t.ContractHold):
            t.synthetic_risk_coverage([])

    def test_risk_rejects_duplicate_cases(self):
        sample = {"id":"dup","category":"ANSWERABLE","outcome":"CORRECT"}
        with self.assertRaises(t.ContractHold):
            t.synthetic_risk_coverage([sample, sample])

    def test_risk_rejects_unsupported_categories_and_outcomes(self):
        sample = {"id":"x","category":"UNKNOWN","outcome":"ABSTAIN"}
        with self.assertRaises(t.ContractHold):
            t.synthetic_risk_coverage([sample])
        sample["category"] = "ANSWERABLE"
        sample["outcome"] = "PROVEN_BY_MODEL"
        with self.assertRaises(t.ContractHold):
            t.synthetic_risk_coverage([sample])

    def test_risk_rejects_raw_prompts(self):
        with self.assertRaises(t.ContractHold):
            t.synthetic_risk_coverage([{
                "id":"x","category":"ANSWERABLE","outcome":"CORRECT","prompt":"not allowed"
            }])

    def test_mirrored_hf_readme_links_to_canonical_github_only(self):
        # The Hub software publisher mirrors README, not research/ or docs/.
        card = (ROOT / "README.md").read_text(encoding="utf-8")
        for path in (
            "docs/FLAGSHIP55_KHIPU_FABRIC.md",
            "research/flagship55/manifest.v0.json",
            "research/flagship55/validate_manifest.py",
            "research/flagship55/triad_packet.py",
            "research/flagship55/public_dataset_index.v1.json",
        ):
            self.assertIn(
                "https://github.com/szl-holdings/szl-khipu/blob/main/" + path, card
            )

    def test_cli_outputs_no_secrets_and_no_side_effects(self):
        cp = subprocess.run(
            [sys.executable, "-m", "research.flagship55.triad_packet",
             "--manifest", str(MANIFEST), "--request", str(EXAMPLE)],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=10, check=False,
        )
        self.assertEqual(cp.returncode, 0, cp.stderr.decode(errors="replace"))
        packet = json.loads(cp.stdout)
        self.assertEqual(packet["status"], "REVIEW_REQUIRED")
        self.assertIn(b"F4", cp.stdout)
        self.assertNotIn(b"private patient data", cp.stdout)
        self.assertFalse(packet["raw_source_rows_included"])

    def test_cli_blocks_unlisted_fields_without_echoing_secrets(self):
        req = self.request()
        req["raw_question"] = "SENSITIVE_TEST_CANARY"
        with tempfile.TemporaryDirectory() as directory:
            inp = Path(directory) / "request.json"
            inp.write_text(json.dumps(req), encoding="utf-8")
            cp = subprocess.run(
                [sys.executable, "-m", "research.flagship55.triad_packet",
                 "--manifest", str(MANIFEST), "--request", str(inp)],
                cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=10, check=False,
            )
        self.assertEqual(cp.returncode, 2)
        self.assertNotIn(b"SENSITIVE_TEST_CANARY", cp.stdout + cp.stderr)
        self.assertEqual(json.loads(cp.stdout)["status"], "HOLD")


if __name__ == "__main__":
    unittest.main()
