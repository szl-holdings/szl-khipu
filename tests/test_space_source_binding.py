from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SERVER = _load("szl_khipu_space_server", ROOT / "space" / "server.py")
PUBLISH = _load("szl_khipu_publish_hf", ROOT / "scripts" / "publish_hf.py")
SOURCE_SHA = "a" * 40
HF_SHA = "c" * 40
IDENTITY_ENV = {
    "GITHUB_SHA": SOURCE_SHA,
    "GITHUB_RUN_ID": "123",
    "GITHUB_RUN_ATTEMPT": "1",
}


class SpaceSourceBindingTests(unittest.TestCase):
    def fixture(self, directory: str):
        root = Path(directory)
        (root / "server.py").write_text("print('bound')\n", encoding="utf-8")
        (root / "index.html").write_text("<h1>bound</h1>\n", encoding="utf-8")
        with mock.patch.dict(os.environ, IDENTITY_ENV, clear=True):
            manifest = PUBLISH._deployment_manifest(root)
        manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
        metadata = {
            "schema": "szl.hf-build-info/v2",
            **{key: manifest[key] for key in (
                "source_repository",
                "source_commit",
                "hf_repository",
                "workflow_name",
                "workflow_run_id",
                "workflow_run_attempt",
                "artifact_name",
            )},
            "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "tree_sha256": manifest["tree_sha256"],
        }
        receipt = {
            "schema": "szl.hf-deployment-receipt/v2",
            **{key: metadata[key] for key in (
                "source_repository",
                "source_commit",
                "hf_repository",
                "workflow_name",
                "workflow_run_id",
                "workflow_run_attempt",
                "artifact_name",
                "manifest_sha256",
                "tree_sha256",
            )},
            "hf_revision": HF_SHA,
        }
        provenance = root / "hf-deployment-provenance.json"
        build_info = root / "build-info.json"
        provenance.write_bytes(manifest_bytes)
        build_info.write_text(json.dumps(metadata), encoding="utf-8")
        return root, provenance, build_info, manifest_bytes, metadata, receipt

    def resolve(
        self,
        *,
        mutate=None,
        github_error: Exception | None = None,
        running_revision: str | None = HF_SHA,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root, provenance, build_info, _manifest_bytes, metadata, receipt = self.fixture(directory)
            if mutate is not None:
                mutate(root, provenance, build_info, metadata)
            github = (
                mock.Mock(side_effect=github_error)
                if github_error is not None
                else mock.Mock(return_value=(receipt, "b" * 64))
            )
            with (
                mock.patch.object(SERVER, "ROOT", root),
                mock.patch.object(SERVER, "BUILD_INFO", build_info),
                mock.patch.object(SERVER, "PROVENANCE", provenance),
                mock.patch.object(SERVER, "_github_evidence", github),
                mock.patch.object(
                    SERVER,
                    "_running_hf_revision",
                    return_value=running_revision,
                ),
            ):
                return SERVER._source_document("szl.build-info/v1")

    def test_exact_source_run_artifact_tree_and_hf_revision_are_bound(self):
        payload, error = self.resolve()
        self.assertIsNone(error)
        self.assertEqual(payload["state"], "SOURCE_BOUND_DEPLOYMENT")
        self.assertEqual(payload["source"]["commit"], SOURCE_SHA)
        self.assertEqual(payload["deployment"]["hf_revision"], HF_SHA)
        self.assertEqual(payload["deployment"]["artifact_sha256"], "b" * 64)
        self.assertRegex(payload["deployment"]["runtime_tree_sha256"], r"^[0-9a-f]{64}$")

    def test_missing_malformed_or_divergent_evidence_fails_closed(self):
        mutations = [
            lambda _root, _provenance, build, _metadata: build.unlink(),
            lambda _root, _provenance, build, metadata: build.write_text(
                json.dumps({**metadata, "source_commit": "main"}), encoding="utf-8"
            ),
            lambda root, _provenance, _build, _metadata: (root / "server.py").write_text(
                "print('tampered')\n", encoding="utf-8"
            ),
            lambda _root, provenance, _build, _metadata: provenance.write_text(
                "{}\n", encoding="utf-8"
            ),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                payload, error = self.resolve(mutate=mutation)
                self.assertEqual(payload["state"], "UNKNOWN")
                self.assertIsNotNone(error)

        payload, error = self.resolve(github_error=ValueError("forged artifact"))
        self.assertEqual(payload["state"], "UNKNOWN")
        self.assertIn("forged artifact", error)

        payload, error = self.resolve(running_revision=None)
        self.assertEqual(payload["state"], "UNKNOWN")
        self.assertIn("does not match", error)

    def test_mutable_hf_head_never_substitutes_for_the_expected_revision(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(
                SERVER,
                "_url_json",
                return_value={"sha": "d" * 40, "runtime": {"stage": "RUNNING"}},
            ):
                self.assertIsNone(SERVER._running_hf_revision(HF_SHA, SERVER.HF_REPOSITORY))
            with mock.patch.object(
                SERVER,
                "_url_json",
                return_value={"sha": HF_SHA, "runtime": {"stage": "RUNNING"}},
            ):
                self.assertEqual(
                    SERVER._running_hf_revision(HF_SHA, SERVER.HF_REPOSITORY),
                    HF_SHA,
                )
        with mock.patch.dict(os.environ, {"SPACE_COMMIT": "malformed"}, clear=True):
            with mock.patch.object(SERVER, "_url_json") as lookup:
                self.assertIsNone(SERVER._running_hf_revision(HF_SHA, SERVER.HF_REPOSITORY))
                lookup.assert_not_called()

    def test_github_artifact_archive_is_downloaded_hashed_and_compared(self):
        with tempfile.TemporaryDirectory() as directory:
            _root, _provenance, _build, manifest_bytes, metadata, receipt = self.fixture(directory)
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("hf-deployment-provenance.json", manifest_bytes)
                archive.writestr(
                    "hf-deployment-receipt.json",
                    json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                )
            archive_bytes = stream.getvalue()
            archive_digest = hashlib.sha256(archive_bytes).hexdigest()
            run = {
                "id": 123,
                "head_sha": SOURCE_SHA,
                "head_branch": "main",
                "event": "push",
                "name": "publish-hf",
                "status": "completed",
                "conclusion": "success",
                "repository": {"full_name": "szl-holdings/szl-khipu"},
            }
            artifacts = {
                "artifacts": [{
                    "id": 456,
                    "name": "szl-khipu-hf-provenance",
                    "expired": False,
                    "digest": f"sha256:{archive_digest}",
                    "workflow_run": {"id": 123, "head_sha": SOURCE_SHA},
                }]
            }
            with (
                mock.patch.object(SERVER, "_url_json", side_effect=[run, artifacts]),
                mock.patch.object(SERVER, "_url_bytes", return_value=archive_bytes),
            ):
                resolved, digest = SERVER._github_evidence(metadata, manifest_bytes)
            self.assertEqual(resolved["hf_revision"], HF_SHA)
            self.assertEqual(digest, archive_digest)

            forged = copy.deepcopy(artifacts)
            forged["artifacts"][0]["digest"] = "sha256:" + ("0" * 64)
            with (
                mock.patch.object(SERVER, "_url_json", side_effect=[run, forged]),
                mock.patch.object(SERVER, "_url_bytes", return_value=archive_bytes),
                self.assertRaisesRegex(ValueError, "digest mismatch"),
            ):
                SERVER._github_evidence(metadata, manifest_bytes)

    def test_manifest_digest_changes_with_the_staged_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "server.py").write_text("one\n", encoding="utf-8")
            with mock.patch.dict(os.environ, IDENTITY_ENV, clear=True):
                before = PUBLISH._deployment_manifest(root)
                (root / "server.py").write_text("two\n", encoding="utf-8")
                after = PUBLISH._deployment_manifest(root)
            self.assertNotEqual(before["tree_sha256"], after["tree_sha256"])


if __name__ == "__main__":
    unittest.main()
