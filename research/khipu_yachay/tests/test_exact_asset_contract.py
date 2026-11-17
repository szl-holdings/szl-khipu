"""Exact-byte release verification, including CRLF and source-registry tampering."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.asset_contract import ASSET_PINS, AssetBindingError, verify_assets
from space.app import load_state
from scripts.stage_release import stage


class YachayByteContract(unittest.TestCase):
    def test_all_seven_release_assets_are_exact_git_bound_bytes(self):
        observed = verify_assets(ROOT)
        self.assertEqual(set(observed), set(ASSET_PINS))
        for name, (expected_size, sha) in ASSET_PINS.items():
            data = (ROOT/name).read_bytes()
            with self.subTest(name=name):
                self.assertEqual(len(data), expected_size)
                self.assertEqual(hashlib.sha256(data).hexdigest(), sha)
                self.assertNotIn(b"\r\n", data)

    def test_existing_model_source_binding_still_works(self):
        state = load_state(ROOT)
        self.assertEqual(
            state["model_sha256"], ASSET_PINS["model/yachay_nb_v0.json"][1]
        )
        self.assertEqual(len(state["kh_ids"]), 702)
        self.assertEqual(len(state["sources"]), 14)

    def test_every_release_asset_tamper_denies_startup_and_staging(self):
        # Each test has distinct path and fresh copy: never modify pinned repo
        # bytes, and never coerce changed values into 'unknown' defaults.
        for relative in ASSET_PINS:
            with self.subTest(file=relative), tempfile.TemporaryDirectory() as folder:
                target = Path(folder)/"project"
                target.mkdir()
                shutil.copytree(ROOT/"model", target/"model")
                shutil.copytree(ROOT/"data", target/"data")
                source = target/relative
                data = bytearray(source.read_bytes())
                self.assertGreater(len(data), 10)
                data[3] = data[3] ^ 1
                source.write_bytes(bytes(data))
                with self.assertRaises(AssetBindingError):
                    verify_assets(target)
                with self.assertRaises(AssetBindingError):
                    load_state(target)
                staged = Path(folder)/"new-stage"
                with self.assertRaises(AssetBindingError):
                    stage(target, staged, "b16cc3e3f8ffdb776ebb7b0b46263e58a77b6929")
                self.assertFalse(staged.exists())

    def test_missing_asset_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/"project"
            target.mkdir()
            shutil.copytree(ROOT/"model", target/"model")
            shutil.copytree(ROOT/"data", target/"data")
            (target/"data/sources.jsonl").unlink()
            with self.assertRaisesRegex(AssetBindingError, "ASSET"):
                load_state(target)

    def test_hf_staging_is_local_and_does_not_promote_or_mutate_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)/"hf-staging"
            result = stage(ROOT, out, "b16cc3e3f8ffdb776ebb7b0b46263e58a77b6929")
            self.assertTrue(result["dry_run_only"])
            self.assertFalse(result["released"])
            self.assertIsNone(result["provider_commits"])
            self.assertFalse(result["runtime_verified"])
            for name in ("data/synthetic_train.jsonl",
                         "data/synthetic_eval.jsonl",
                         "data/sources.jsonl",
                         "data/okr_kh_index.jsonl",
                         "data/okr_registry_provenance.json"):
                self.assertEqual((out/"dataset"/Path(name).name).read_bytes(),
                                 (ROOT/name).read_bytes())
            # Reviewer-authored OOD stress prompts are never silently copied
            # into the hosted Space or distribution dataset.
            expected_public = {
                "synthetic_train.jsonl", "synthetic_eval.jsonl",
                "sources.jsonl", "okr_kh_index.jsonl",
                "okr_registry_provenance.json",
            }
            self.assertEqual(
                {x.name for x in (out/"space/data").iterdir()},
                expected_public
            )
            self.assertEqual(
                {x.name for x in (out/"dataset").iterdir() if x.is_file()
                 and x.name not in {"README.md", "SOURCE_BINDING.json"}},
                expected_public
            )
            self.assertFalse((out/"space/data/posthoc_ood_v0.jsonl").exists())
            self.assertFalse((out/"dataset/posthoc_ood_v0.jsonl").exists())
            self.assertEqual(
                (out/"model/yachay_nb_v0.json").read_bytes(),
                (ROOT/"model/yachay_nb_v0.json").read_bytes()
            )
            self.assertEqual(
                (out/"space/model/yachay_nb_v0.json").read_bytes(),
                (ROOT/"model/yachay_nb_v0.json").read_bytes()
            )
            with self.assertRaises(ValueError):
                stage(ROOT, out, "b16cc3e3f8ffdb776ebb7b0b46263e58a77b6929")


if __name__ == "__main__":
    unittest.main()
