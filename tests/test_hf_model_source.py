# SPDX-License-Identifier: Apache-2.0
"""The software mirror must not leave an old admission kernel on the Hub."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("model_publisher", ROOT / "scripts/publish_hf.py")
PUBLISH = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PUBLISH)


class ModelSoftwareMirrorTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "core.autocrlf", "false")
        for name in PUBLISH.MODEL_ROOT_FILES:
            (self.root / name).write_bytes(f"{name}\n".encode())
        package = self.root / "szl_khipu/train"
        package.mkdir(parents=True)
        (package.parent / "__init__.py").write_bytes(b"")
        self.source = (ROOT / "szl_khipu/train/receipt_agent.py").read_bytes()
        (package / "receipt_agent.py").write_bytes(self.source)
        (self.root / "unrelated.txt").write_bytes(b"must not be uploaded")
        self.git("add", ".")
        self.commit()
        self.patch_root = mock.patch.object(PUBLISH, "ROOT", self.root)
        self.patch_root.start()
        self.addCleanup(self.patch_root.stop)
        self.environment = mock.patch.dict(os.environ, {
            "GITHUB_SHA": self.sha, "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.receipt = self.root / "receipt.json"
        patch_receipt = mock.patch.object(PUBLISH, "MODEL_RECEIPT_NAME", str(self.receipt))
        patch_receipt.start()
        self.addCleanup(patch_receipt.stop)

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args],
                                       stderr=subprocess.STDOUT).decode().strip()

    def commit(self):
        self.git("-c", "commit.gpgsign=false", "commit", "-qm", "fixture")
        self.sha = self.git("rev-parse", "HEAD")

    def stage(self):
        staging, manifest = PUBLISH._stage_model_source()
        self.addCleanup(shutil.rmtree, staging)
        return staging, manifest

    def test_untracked_and_dirty_files_cannot_change_immutable_mirror(self):
        (self.root / "szl_khipu/train/receipt_agent.py").write_bytes(b"unreviewed")
        cache = self.root / "szl_khipu/__pycache__"
        cache.mkdir()
        (cache / "kernel.pyc").write_bytes(b"untracked")
        staging, manifest = self.stage()
        self.assertEqual((staging / "szl_khipu/train/receipt_agent.py").read_bytes(), self.source)
        self.assertFalse((staging / "unrelated.txt").exists())
        self.assertFalse((staging / "szl_khipu/__pycache__").exists())
        self.assertEqual(manifest["source_commit"], self.sha)
        self.assertEqual(manifest["source_tree"], self.git("rev-parse", "HEAD^{tree}"))
        self.assertFalse(manifest["trained_checkpoint_claimed"])

    def test_actual_staged_kernel_rejects_nonfinite_features(self):
        staging, _manifest = self.stage()
        spec = importlib.util.spec_from_file_location(
            "mirrored_receipt_agent", staging / "szl_khipu/train/receipt_agent.py")
        agent = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agent)
        allowed = np.ones(agent.FEATURE_DIM)
        allowed[1] = allowed[8] = 0
        self.assertEqual(agent.rule_check(allowed), agent.ALLOW)
        for invalid in (np.nan, np.inf, -np.inf):
            for index in range(agent.FEATURE_DIM):
                with self.subTest(invalid=invalid, index=index):
                    features = allowed.copy()
                    features[index] = invalid
                    self.assertEqual(agent.rule_check(features), agent.BLOCKED)
                    self.assertEqual(agent.decide(features, {})["decision"], "BLOCKED")

    def test_source_head_drift_fails_before_staging(self):
        with mock.patch.dict(os.environ, {"GITHUB_SHA": "b" * 40}):
            with self.assertRaisesRegex(RuntimeError, "HEAD"):
                PUBLISH._stage_model_source()

    def test_missing_required_package_fails_closed(self):
        self.git("rm", "szl_khipu/train/receipt_agent.py")
        self.commit()
        with mock.patch.dict(os.environ, {"GITHUB_SHA": self.sha}):
            with self.assertRaisesRegex(RuntimeError, "required"):
                PUBLISH._stage_model_source()

    def test_tracked_symlink_or_cache_is_not_published(self):
        blob = self.git("hash-object", "-w", "README.md")
        for mode, name in (("120000", "szl_khipu/link"),
                           ("100644", "szl_khipu/__pycache__/old.pyc")):
            with self.subTest(name=name):
                self.git("update-index", "--add", "--cacheinfo", f"{mode},{blob},{name}")
                self.commit()
                with mock.patch.dict(os.environ, {"GITHUB_SHA": self.sha}):
                    with self.assertRaisesRegex(RuntimeError, "unsafe"):
                        PUBLISH._stage_model_source()
                self.git("update-index", "--force-remove", name)

    def fake_provider(self, *, extra=False, tamper=False, drift=False):
        files = {}
        api = mock.Mock(token="not-a-real-token")
        api.model_info.side_effect = [SimpleNamespace(sha="b" * 40),
                                     SimpleNamespace(sha=("d" if drift else "c") * 40)]

        def upload(**kwargs):
            self.assertEqual(kwargs["parent_commit"], "b" * 40)
            self.assertEqual(kwargs["repo_type"], "model")
            self.assertEqual(kwargs["delete_patterns"], ["szl_khipu/*", "szl_khipu/**"])
            root = Path(kwargs["folder_path"])
            files.update({p.relative_to(root).as_posix(): p.read_bytes()
                          for p in root.rglob("*") if p.is_file()})
            return SimpleNamespace(oid="c" * 40)

        api.upload_folder.side_effect = upload
        api.list_repo_files.side_effect = lambda *a, **k: [
            *files, "lambda_gate.npz", "artifacts/tiny_khipu.npz",
            *( ["szl_khipu/stale.py"] if extra else []),
        ]

        def download(**kwargs):
            self.assertEqual(kwargs["revision"], "c" * 40)
            self.assertEqual(kwargs["repo_type"], "model")
            name = kwargs["filename"]
            target = Path(kwargs["local_dir"]) / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"tampered" if tamper else files[name])
            return str(target)

        return api, download

    def test_atomic_package_upload_and_immutable_byte_readback(self):
        api, download = self.fake_provider()
        receipt = PUBLISH._publish_model_source(api, download)
        self.assertTrue(receipt["byte_parity_verified"])
        self.assertEqual(receipt["hf_revision"], "c" * 40)
        self.assertFalse(receipt["trained_checkpoint_claimed"])
        self.assertEqual(json.loads(self.receipt.read_text()), receipt)
        api.list_repo_files.assert_called_once_with(
            PUBLISH.HF_REPOSITORY, repo_type="model", revision="c" * 40)

    def test_stale_file_or_tampered_bytes_or_head_drift_cannot_write_success(self):
        for corruption, message in (("extra", "file set"), ("tamper", "byte mismatch"),
                                    ("drift", "head changed")):
            with self.subTest(corruption=corruption):
                api, download = self.fake_provider(**{corruption: True})
                with self.assertRaisesRegex(RuntimeError, message):
                    PUBLISH._publish_model_source(api, download)
                self.assertFalse(self.receipt.exists())

    def test_model_scope_validates_before_any_provider_workflow_step(self):
        workflow = (ROOT / ".github/workflows/publish-hf.yml").read_text()
        self.assertLess(workflow.index("--validate-model-source"), workflow.index("HF_TOKEN:"))
        self.assertIn("hf-model-source-receipt.json", workflow)


if __name__ == "__main__":
    unittest.main()
