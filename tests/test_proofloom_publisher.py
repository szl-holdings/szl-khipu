"""Credential-free admission tests for the one-shot Proof Loom Space publisher."""
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import publish_proofloom as pub


class ProofLoomPublisherTests(unittest.TestCase):
    def test_offline_stage_exact_allowlist(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            manifest = pub._stage(out, "f"*40)
            self.assertEqual(set(p.name for p in out.iterdir()),
                             {"app.py", "README.md", "proof_loom.py", "SOURCE.json"})
            self.assertEqual(len(manifest["files"]), 3)
            self.assertEqual(manifest["source_commit"], "f"*40)
            self.assertEqual(manifest["historical_claim"], "NOT_ESTABLISHED")
            for row in manifest["files"]:
                self.assertEqual(hashlib.sha256((out / row["dest"]).read_bytes()).hexdigest(),
                                 row["sha256"])
                self.assertEqual((pub.ROOT / row["source"]).read_bytes(),
                                 (out / row["dest"]).read_bytes())
            self.assertEqual(json.loads((out / "SOURCE.json").read_text()), manifest)

    def test_existing_destination_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root/"foreign.txt").write_text("leave unchanged")
            with self.assertRaisesRegex(pub.AdmissionHold, "DESTINATION_NOT_EMPTY"):
                pub._stage(root, "f"*40)
            self.assertEqual((root/"foreign.txt").read_text(), "leave unchanged")

    def test_untrusted_authority_fails_before_provider(self):
        with patch.dict(os.environ, {"GITHUB_SHA": "f"*40,
                                      "GITHUB_REPOSITORY": "another/repo"}, clear=True):
            with self.assertRaisesRegex(pub.AdmissionHold, "PROTECTED_SOURCE_AUTHORITY_MISMATCH"):
                pub._identity(publish=True)
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(pub.AdmissionHold, "SOURCE_SHA_UNOBSERVED"):
                pub._identity(publish=True)

    def test_protected_source_accepted_but_no_provider_mutation(self):
        values = {"GITHUB_SHA": "a"*40, "GITHUB_REPOSITORY": pub.SOURCE_REPO,
                  "GITHUB_REF": "refs/heads/main", "GITHUB_EVENT_NAME": "push",
                  "GITHUB_WORKFLOW": "publish-proof-loom", "GITHUB_WORKFLOW_SHA": "a"*40}
        with patch.dict(os.environ, values, clear=True):
            self.assertEqual(pub._identity(publish=True), "a"*40)

    def test_rendered_runtime_semantics(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self, _): return json.dumps(
                {"title": "Khipu Proof Loom", "components": [{"type": "model3d"}]}
            ).encode()
        with patch.object(pub.urllib.request, "urlopen", return_value=Response()):
            got = pub._runtime_readback(SimpleNamespace(
                get_space_runtime=lambda _: SimpleNamespace(stage="RUNNING")
            ))
        self.assertEqual(got["status"], "RUNTIME_CONFIG_OBSERVED")
        self.assertEqual(got["stage"], "RUNNING")

    def test_runtime_no_model3d_refused(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self, _): return json.dumps(
                {"title": "Khipu Proof Loom", "components": [{"type": "markdown"}]}
            ).encode()
        with patch.object(pub.urllib.request, "urlopen", return_value=Response()):
            with self.assertRaisesRegex(pub.AdmissionHold, "SPACE_RENDERED_SOURCE_MISMATCH"):
                pub._runtime_readback(SimpleNamespace(
                    get_space_runtime=lambda _: SimpleNamespace(stage="RUNNING")
                ))


if __name__ == "__main__":
    unittest.main()
