"""Adversarial source, metadata and parent-CAS publication contracts."""
from __future__ import annotations
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("reference_publisher", ROOT / "scripts/publish_reference_card.py")
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)
PARENT, SOURCE, REVISION = "a" * 40, "b" * 40, "c" * 40
OLD = b"---\nlicense: apache-2.0\ntags: [test-fixture]\nszl:\n  publication_eligible: false\n---\nold\n"
NEW = OLD.replace(b"old", b"new")


class FakeAPI:
    token = False
    def __init__(self):
        self.head = PARENT
        self.files = {"README.md": "old", "fixture.npz": "fixture", "TRAINING_RECEIPT.json": "receipt"}
        self.calls = []
        self.optimized = self.conflict = self.tamper = self.unmanaged = self.concurrent = False
        self.oversized_before = self.oversized_after = False
    def model_info(self, repo, **kwargs):
        names = dict(self.files)
        if kwargs.get("revision") == REVISION:
            names["README.md"] = "new"
            if self.unmanaged:
                names["fixture.npz"] = "tampered"
        size = publisher.MAX_CARD_BYTES + 1 if (self.oversized_after and kwargs.get("revision") == REVISION) or self.oversized_before else 4
        return SimpleNamespace(sha=kwargs.get("revision") or self.head, siblings=[SimpleNamespace(rfilename=k, blob_id=v, size=size if k == "README.md" else 4, lfs=None) for k, v in names.items()])
    def create_commit(self, **kwargs):
        self.calls.append(kwargs)
        if self.conflict:
            raise RuntimeError("provider parent conflict")
        if not self.optimized:
            kwargs["operations"][0]._is_committed = True
        self.head = "d" * 40 if self.concurrent else REVISION
        return SimpleNamespace(oid=REVISION)


class ReferenceCardPublisherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.api = FakeAPI()
        self.receipts = []
        self.downloads = []
    def tearDown(self):
        self.temp.cleanup()
    def download(self, **kwargs):
        self.downloads.append(dict(kwargs))
        self.assertEqual(kwargs["repo_id"], "SZLHOLDINGS/chakana")
        self.assertEqual(kwargs["filename"], "README.md")
        self.assertEqual(kwargs["endpoint"], "https://huggingface.co")
        path = Path(self.temp.name) / kwargs["revision"]
        raw = OLD if kwargs["revision"] == PARENT else NEW
        if self.api.tamper and kwargs["revision"] == REVISION:
            raw += b"tampered"
        path.write_bytes(raw)
        return path
    def publish(self, **changes):
        options = dict(model="chakana", source_sha=SOURCE, expected_parent=PARENT,
                       expected_readme_sha256=publisher.digest(OLD), card=NEW,
                       checkpoint=lambda row: self.receipts.append(dict(row)),
                       freshness=lambda sha: None)
        options.update(changes)
        return publisher.publish_one(self.api, self.download,
            lambda **kwargs: SimpleNamespace(_is_committed=False, **kwargs), **options)
    def test_conditional_commit_and_exact_readback_preserve_unmanaged_files(self):
        result = self.publish()
        self.assertEqual(result["state"], "PUBLISHED_AND_READ_BACK")
        call = self.api.calls[0]
        self.assertEqual(call["parent_commit"], PARENT)
        self.assertEqual(call["revision"], "main")
        self.assertIs(call["create_pr"], False)
        self.assertEqual([op.path_in_repo for op in call["operations"]], ["README.md"])
        self.assertTrue(result["unmanaged_files_preserved"])
        self.assertFalse(result["model_admission_changed"])
    def test_reviewed_parent_change_blocks_before_mutation(self):
        self.api.head = REVISION
        with self.assertRaisesRegex(ValueError, "head changed"):
            self.publish()
        self.assertFalse(self.api.calls)
    def test_reviewed_readme_change_blocks_before_mutation(self):
        with self.assertRaisesRegex(ValueError, "README bytes changed"):
            self.publish(expected_readme_sha256="f" * 64)
        self.assertFalse(self.api.calls)
    def test_foreign_environment_endpoint_cannot_receive_download_token(self):
        self.api.token = "synthetic-credential"
        with patch.dict(os.environ, {"HF_ENDPOINT": "https://foreign.invalid"}):
            self.publish()
        self.assertEqual(len(self.downloads), 2)
        self.assertTrue(all(call["endpoint"] == "https://huggingface.co" for call in self.downloads))
        self.assertTrue(all(call["token"] == "synthetic-credential" for call in self.downloads))
    def test_oversized_parent_readme_blocks_before_download_and_write(self):
        self.api.oversized_before = True
        with self.assertRaisesRegex(ValueError, "oversized"):
            self.publish()
        self.assertFalse(self.downloads)
        self.assertFalse(self.api.calls)
    def test_oversized_returned_readme_blocks_before_readback_download(self):
        self.api.oversized_after = True
        with self.assertRaisesRegex(ValueError, "oversized"):
            self.publish()
        self.assertEqual(len(self.downloads), 1)
        self.assertEqual(self.receipts[-1]["hf_revision"], REVISION)
    def test_noop_client_shortcut_fails_closed(self):
        self.api.optimized = True
        with self.assertRaisesRegex(ValueError, "not confirmed"):
            self.publish()
        self.assertEqual(self.receipts[-1]["hf_revision"], REVISION)
        self.assertFalse(self.receipts[-1]["mutation_confirmed"])
    def test_parent_conflict_is_not_retried(self):
        self.api.conflict = True
        with self.assertRaises(RuntimeError):
            self.publish()
        self.assertEqual(len(self.api.calls), 1)
        self.assertEqual(self.receipts[-1]["state"], "MUTATION_ATTEMPTED")
    def test_readback_tamper_fails_after_recording_accepted_commit(self):
        self.api.tamper = True
        with self.assertRaisesRegex(ValueError, "immutable bytes"):
            self.publish()
        self.assertEqual(self.receipts[-1]["hf_revision"], REVISION)
        self.assertTrue(self.receipts[-1]["mutation_confirmed"])
    def test_unmanaged_file_change_fails_readback(self):
        self.api.unmanaged = True
        with self.assertRaisesRegex(ValueError, "unmanaged"):
            self.publish()
    def test_concurrent_followup_writer_blocks_success(self):
        self.api.concurrent = True
        with self.assertRaisesRegex(ValueError, "current provider head"):
            self.publish()
    def test_matching_card_has_no_mutation_and_rechecks_head(self):
        result = self.publish(card=OLD)
        self.assertEqual(result["state"], "ALREADY_MATCHED")
        self.assertFalse(self.api.calls)
    def test_unknown_target_and_mutable_inputs_are_rejected(self):
        for options in (dict(model="unknown"), dict(source_sha="main"),
                        dict(expected_parent="main"), dict(expected_readme_sha256="bad")):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.publish(**options)
        self.assertFalse(self.api.calls)
    def test_stale_canonical_source_never_writes(self):
        def fail(sha):
            raise ValueError("stale source")
        with self.assertRaisesRegex(ValueError, "stale source"):
            self.publish(freshness=fail)
        self.assertFalse(self.api.calls)
    def test_duplicate_metadata_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            publisher.metadata(b"---\nlicense: apache-2.0\nlicense: mit\n---\n")
    def test_metadata_loss_and_promotion_are_rejected(self):
        before = publisher.metadata(OLD)
        for after in ({}, dict(before, license="mit"), dict(before, tags=[]),
                      dict(before, szl={"publication_eligible": True})):
            with self.subTest(after=after), self.assertRaises(ValueError):
                publisher.preserve_metadata(before, after)
    def test_all_cards_retain_provider_metadata_and_verified_fixture_boundaries(self):
        evidence = json.loads((ROOT / "docs/reference-fixture-verification-20261002.json").read_text("utf-8"))
        for row in evidence["fixtures"]:
            name = row["model"].split("/")[1]
            card = (ROOT / "atelier/hf" / (name + ".md")).read_bytes()
            self.assertEqual(card, (ROOT / "atelier-space/cards" / (name + ".md")).read_bytes())
            meta = publisher.metadata(card)
            self.assertEqual(meta["szl"]["canonical_source"], "https://github.com/szl-holdings/szl-forge")
            self.assertEqual(str(meta["szl"]["card_resync"]), "2026-09-25")
            self.assertFalse(meta["szl"]["publication_eligible"])
            self.assertIn(row["archive_sha256"].encode(), card)
            self.assertIn(row["hf_revision"].encode(), card)
            self.assertTrue(all(arr["finite"] for arr in row["arrays"].values()))
            self.assertEqual(row["archive_sha256"], row["TRAINING_RECEIPT.json"]["artifacts"][name + ".npz"]["sha256"])
            self.assertIn(b"copyright ownership and relicensing authority UNKNOWN", card)
    def test_exact_sdk_confirms_commit_and_noop_marker_semantics(self):
        # Optional Hub dependency is pinned only for the explicit apply route.
        try:
            import huggingface_hub
            from huggingface_hub import CommitOperationAdd
        except ImportError as error:
            raise unittest.SkipTest("optional Hub dependency is absent") from error
        if huggingface_hub.__version__ != publisher.CLIENT_VERSION:
            self.skipTest("explicit publication uses its reviewed pinned client")
        operation = CommitOperationAdd(path_in_repo="README.md", path_or_fileobj=NEW)
        self.assertIs(operation._is_committed, False)
        api = huggingface_hub.HfApi(token=False)
        def preupload(**kwargs):
            for addition in kwargs["additions"]:
                addition._upload_mode = "regular"
        with patch.object(api, "_validate_yaml"), patch.object(api, "preupload_lfs_files", side_effect=preupload), \
             patch.object(api, "_duplicate_lfs_files"), \
             patch("huggingface_hub.hf_api._fetch_files_to_copy", return_value={}), \
             patch("huggingface_hub.hf_api._send_commit", return_value=SimpleNamespace(oid=REVISION)) as send:
            api.create_commit(repo_id="SZLHOLDINGS/chakana", repo_type="model", revision="main",
                              create_pr=False, parent_commit=PARENT,
                              operations=[operation], commit_message="offline contract")
        self.assertIs(operation._is_committed, True)
        self.assertEqual(send.call_args.kwargs["parent_commit"], PARENT)
        operation = CommitOperationAdd(path_in_repo="README.md", path_or_fileobj=NEW)
        def noop_preupload(**kwargs):
            preupload(**kwargs)
            for addition in kwargs["additions"]:
                addition._remote_oid = addition._local_oid
        with patch.object(api, "_validate_yaml"), patch.object(api, "preupload_lfs_files", side_effect=noop_preupload), \
             patch.object(api, "_duplicate_lfs_files"), patch.object(api, "repo_info", return_value=SimpleNamespace(sha=REVISION)), \
             patch("huggingface_hub.hf_api._fetch_files_to_copy", return_value={}), \
             patch("huggingface_hub.hf_api._send_commit") as send:
            api.create_commit(repo_id="SZLHOLDINGS/chakana", repo_type="model", revision="main",
                              create_pr=False, parent_commit=PARENT,
                              operations=[operation], commit_message="offline contract")
        self.assertFalse(send.called)
        self.assertIs(operation._is_committed, False)


if __name__ == "__main__":
    unittest.main()
