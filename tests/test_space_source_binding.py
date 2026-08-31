from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "szl_khipu_space_server", ROOT / "space" / "server.py"
)
assert SPEC and SPEC.loader
SERVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SERVER)


class SpaceSourceBindingTests(unittest.TestCase):
    def metadata(self) -> dict:
        return {
            "source_repository": "szl-holdings/szl-khipu",
            "source_commit": "a" * 40,
            "hf_repository": "SZLHOLDINGS/szl-khipu",
            "workflow_name": "publish-hf",
            "workflow_run_id": 123,
            "artifact_name": "szl-khipu-hf-provenance",
            "artifact_sha256": "b" * 64,
        }

    def resolve(self, metadata: dict | None, revision: str | None):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "build-info.json"
            if metadata is not None:
                path.write_text(json.dumps(metadata), encoding="utf-8")
            with (
                mock.patch.object(SERVER, "BUILD_INFO", path),
                mock.patch.object(SERVER, "_hf_revision", return_value=revision),
            ):
                return SERVER._source_document("szl.build-info/v1")

    def test_exact_source_run_artifact_and_hf_revision_are_bound(self):
        payload, error = self.resolve(self.metadata(), "c" * 40)
        self.assertIsNone(error)
        self.assertEqual(payload["state"], "SOURCE_BOUND_DEPLOYMENT")
        self.assertEqual(payload["source"]["commit"], "a" * 40)
        self.assertEqual(payload["deployment"]["hf_revision"], "c" * 40)
        self.assertEqual(payload["deployment"]["artifact_set_sha256"], "b" * 64)

    def test_missing_or_malformed_evidence_fails_closed(self):
        cases = [
            (None, "c" * 40),
            ({**self.metadata(), "source_commit": "main"}, "c" * 40),
            ({**self.metadata(), "artifact_sha256": "bad"}, "c" * 40),
            ({**self.metadata(), "workflow_run_id": 0}, "c" * 40),
            (self.metadata(), None),
        ]
        for metadata, revision in cases:
            with self.subTest(metadata=metadata, revision=revision):
                payload, error = self.resolve(metadata, revision)
                self.assertEqual(payload["state"], "UNKNOWN")
                self.assertIsNotNone(error)


if __name__ == "__main__":
    unittest.main()
