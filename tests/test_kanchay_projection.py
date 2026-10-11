"""The accepted brand bundle and each installed presentation subset are distinct."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = ('docs/szl', 'szl_khipu/szl')
BUNDLE_REVISION = "4309f6fce89179331b0b3ed8c99494e76c5be256"
MANIFEST_SHA256 = "967a77235227f1d75852fb61873e46336e67403cbc0e7e12b141e31c83fbd93d"


class KanchayProjectionTests(unittest.TestCase):
    def test_exact_upstream_and_complete_installed_subset(self):
        for folder in FOLDERS:
            with self.subTest(folder=folder):
                root = ROOT / folder
                source_bytes = (root / "SOURCE.json").read_bytes()
                source = json.loads(source_bytes)
                projection = json.loads((root / "VENDORED.json").read_bytes())
                self.assertEqual(hashlib.sha256(source_bytes).hexdigest(), MANIFEST_SHA256)
                self.assertEqual(source["source_commit"], "27d12e77fc0f9f1a0e5fae8b34adf2380d51d070")
                self.assertEqual(projection["schema"], "szl.kanchay-vendored-subset/v1")
                self.assertEqual(projection["scope"], "STATIC_PRESENTATION_ASSETS_ONLY")
                self.assertEqual(projection["upstream"], {
                    "repository": "szl-holdings/szl-brand",
                    "revision": BUNDLE_REVISION,
                    "manifest_path": "kanchay/SOURCE.json",
                    "manifest_sha256": MANIFEST_SHA256,
                })
                installed = {name for name in source["sha256"] if (root / name).is_file()}
                self.assertEqual(set(projection["files"]), installed)
                self.assertTrue(installed)
                for name, digest in projection["files"].items():
                    self.assertEqual(digest, source["sha256"][name], name)
                    self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), digest, name)


if __name__ == "__main__":
    unittest.main()
