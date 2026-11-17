"""Credential-free admission tests for the one-shot Proof Loom Space publisher."""
import hashlib
import json
import os
import sys
import tempfile
import types
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
                             {"app.py", "README.md", "proof_loom.py",
                              "hypothesis.py", "sequence_scout_v1.json", "SOURCE.json"})
            self.assertEqual(len(manifest["files"]), 5)
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
        source, manifest = "a" * 40, "b" * 64
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self, _): return json.dumps({
                "title": "Khipu Proof Loom",
                "components": [
                    {"type": "model3d"},
                    {"type": "html", "props": {"value":
                        f'<div data-szl-source-sha="{source}" '
                        f'data-szl-manifest-sha256="{manifest}">PINNED</div>'}},
                ],
                "dependencies": [{"api_name": "discover"}],
            }).encode()
        with patch.object(pub.urllib.request, "urlopen", return_value=Response()):
            got = pub._runtime_readback(SimpleNamespace(
                get_space_runtime=lambda _: SimpleNamespace(stage="RUNNING")
            ), source, manifest)
        self.assertEqual(got["status"], "RUNTIME_SOURCE_VERIFIED")
        self.assertEqual(got["stage"], "RUNNING")
        self.assertEqual(got["source_commit"], source)
        self.assertEqual(got["manifest_sha256"], manifest)

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
                ), "a" * 40, "b" * 64)

    def test_runtime_without_scout_api_is_not_qualified(self):
        source, manifest = "a" * 40, "b" * 64
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self, _): return json.dumps({
                "title": "Khipu Proof Loom",
                "components": [
                    {"type": "model3d"},
                    {"type": "html", "props": {"value":
                        f'<div data-szl-source-sha="{source}" '
                        f'data-szl-manifest-sha256="{manifest}">PINNED</div>'}},
                ],
                "dependencies": [{"api_name": "recompute"}],
            }).encode()
        with patch.object(pub.urllib.request, "urlopen", return_value=Response()):
            with self.assertRaisesRegex(pub.AdmissionHold, "SPACE_DISCOVERY_API_UNOBSERVED"):
                pub._runtime_readback(
                    SimpleNamespace(get_space_runtime=lambda _: SimpleNamespace(stage="RUNNING")),
                    source, manifest,
                )

    def test_running_stale_source_is_not_qualified(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self, _): return json.dumps({
                "title": "Khipu Proof Loom",
                "components": [
                    {"type": "model3d"},
                    {"type": "html", "props": {"value":
                        '<div data-szl-source-sha="' + "c" * 40 +
                        '" data-szl-manifest-sha256="' + "b" * 64 + '"></div>'}},
                ],
            }).encode()
        with patch.object(pub.urllib.request, "urlopen", return_value=Response()):
            with self.assertRaisesRegex(pub.AdmissionHold, "SPACE_RUNTIME_SOURCE_MISMATCH"):
                pub._runtime_readback(SimpleNamespace(
                    get_space_runtime=lambda _: SimpleNamespace(stage="RUNNING")
                ), "a" * 40, "b" * 64)

    def test_space_card_short_description_fails_before_provider(self):
        original = (pub.ROOT / "spaces/proof-loom/README.md").read_bytes()
        pub._validate_space_card(original)
        long_card = original.replace(
            b"short_description: Exact finite mathematics in Python 3D",
            b"short_description: " + b"X" * 61,
        )
        with self.assertRaisesRegex(pub.AdmissionHold, "SPACE_CARD_SHORT_DESCRIPTION_INVALID"):
            pub._validate_space_card(long_card)

    def test_recovery_stub_requires_immutable_parent_and_exact_files(self):
        with tempfile.TemporaryDirectory() as temp:
            readme = Path(temp) / "README.md"
            readme.write_bytes(b"owner-created-only-test-fixture")
            expected = hashlib.sha256(readme.read_bytes()).hexdigest()
            mock_hub = types.ModuleType("huggingface_hub")
            mock_hub.hf_hub_download = lambda **_: str(readme)
            pinned = SimpleNamespace(
                sha="a" * 40, private=False, sdk="gradio",
                siblings=[SimpleNamespace(rfilename=".gitattributes"),
                          SimpleNamespace(rfilename="README.md")],
            )
            api = SimpleNamespace(space_info=lambda *a, **kw: pinned)
            with patch.dict(sys.modules, {"huggingface_hub": mock_hub}), (
                patch.object(pub, "OWNER_STUB_REVISION", "a" * 40)
            ), patch.object(pub, "OWNER_STUB_README_SHA256", expected), patch.object(pub, "_journal") as journal:
                pub._verify_owner_stub(api, "a" * 40, "configured-token")
                journal.assert_called_once()
                with self.assertRaisesRegex(pub.AdmissionHold, "OWNER_STUB_PARENT_CHANGED"):
                    pub._verify_owner_stub(api, "b" * 40, "configured-token")
                pinned.siblings.append(SimpleNamespace(rfilename="foreign.txt"))
                with self.assertRaisesRegex(pub.AdmissionHold, "OWNER_STUB_FILE_SET_OR_IDENTITY_CHANGED"):
                    pub._verify_owner_stub(api, "a" * 40, "configured-token")
                pinned.siblings.pop()
                readme.write_bytes(b"changed")
                with self.assertRaisesRegex(pub.AdmissionHold, "OWNER_STUB_README_BYTES_CHANGED"):
                    pub._verify_owner_stub(api, "a" * 40, "configured-token")


if __name__ == "__main__":
    unittest.main()
