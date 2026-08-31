from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import shutil
import tempfile
import unittest
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
    "GITHUB_RUN_ATTEMPT": "2",
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
            "schema": "szl.hf-build-info/v3",
            **{
                key: manifest[key]
                for key in (
                    "source_repository",
                    "source_commit",
                    "hf_repository",
                    "workflow_name",
                    "workflow_run_id",
                    "workflow_run_attempt",
                    "artifact_name_prefix",
                )
            },
            "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "tree_sha256": manifest["tree_sha256"],
        }
        provenance = root / "hf-deployment-provenance.json"
        build_info = root / "build-info.json"
        provenance.write_bytes(manifest_bytes)
        build_info.write_text(json.dumps(metadata), encoding="utf-8")
        artifact_name = SERVER._deployment_artifact_name(metadata, HF_SHA)
        return root, provenance, build_info, metadata, artifact_name

    def resolve(
        self,
        *,
        mutate=None,
        github_error: Exception | None = None,
        running_revision: str | None = HF_SHA,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root, provenance, build_info, metadata, artifact_name = self.fixture(directory)
            if mutate is not None:
                mutate(root, provenance, build_info, metadata)
            github = (
                mock.Mock(side_effect=github_error)
                if github_error is not None
                else mock.Mock(return_value=(artifact_name, "b" * 64))
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

    def test_exact_source_attempt_artifact_tree_and_hf_revision_are_bound(self):
        payload, error = self.resolve()
        self.assertIsNone(error)
        self.assertEqual(payload["state"], "SOURCE_BOUND_DEPLOYMENT")
        self.assertEqual(payload["source"]["commit"], SOURCE_SHA)
        self.assertEqual(payload["deployment"]["hf_revision"], HF_SHA)
        self.assertEqual(payload["deployment"]["workflow_run_attempt"], 2)
        self.assertIn("-attempt-2-", payload["deployment"]["artifact_name"])
        self.assertIn(
            f"-manifest-{payload['deployment']['manifest_sha256']}-hf-{HF_SHA}",
            payload["deployment"]["artifact_name"],
        )
        self.assertEqual(payload["deployment"]["artifact_sha256"], "b" * 64)
        self.assertRegex(payload["deployment"]["runtime_tree_sha256"], r"^[0-9a-f]{64}$")

    def test_missing_malformed_or_divergent_evidence_fails_closed(self):
        mutations = [
            lambda _root, _provenance, build, _metadata: build.unlink(),
            lambda _root, _provenance, build, metadata: build.write_text(
                json.dumps({**metadata, "source_commit": "main"}), encoding="utf-8"
            ),
            lambda _root, _provenance, build, metadata: build.write_text(
                json.dumps({**metadata, "artifact_name_prefix": "forged"}), encoding="utf-8"
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

        payload, error = self.resolve(github_error=ValueError("forged artifact metadata"))
        self.assertEqual(payload["state"], "UNKNOWN")
        self.assertIn("forged artifact metadata", error)

        payload, error = self.resolve(running_revision=None)
        self.assertEqual(payload["state"], "UNKNOWN")
        self.assertIn("revision is unavailable", error)

    def test_mutable_hf_head_is_never_substituted_for_runtime_evidence(self):
        variable = SERVER.DEPLOYMENT_REVISION_VARIABLE
        for environment in ({}, {variable: "malformed"}, {"SPACE_COMMIT": HF_SHA}):
            with self.subTest(environment=environment):
                with (
                    mock.patch.dict(os.environ, environment, clear=True),
                    mock.patch.object(SERVER, "_url_json") as lookup,
                ):
                    self.assertIsNone(SERVER._running_hf_revision())
                    lookup.assert_not_called()
        with mock.patch.dict(os.environ, {variable: HF_SHA.upper()}, clear=True):
            self.assertEqual(SERVER._running_hf_revision(), HF_SHA)

    def test_publisher_sets_the_runtime_revision_variable(self):
        self.assertEqual(
            PUBLISH.DEPLOYMENT_REVISION_VARIABLE,
            SERVER.DEPLOYMENT_REVISION_VARIABLE,
        )
        api = mock.Mock()
        PUBLISH._publish_runtime_revision(
            api,
            "SZLHOLDINGS/szl-khipu",
            HF_SHA.upper(),
        )
        api.add_space_variable.assert_called_once_with(
            repo_id="SZLHOLDINGS/szl-khipu",
            key="SZL_DEPLOYED_HF_REVISION",
            value=HF_SHA,
        )

        api.reset_mock()
        with self.assertRaisesRegex(RuntimeError, "immutable"):
            PUBLISH._publish_runtime_revision(
                api,
                "SZLHOLDINGS/szl-khipu",
                "main",
            )
        api.add_space_variable.assert_not_called()

    def test_public_metadata_binds_exact_attempt_manifest_and_hf_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            _root, _provenance, _build, metadata, artifact_name = self.fixture(directory)
            artifact_digest = "d" * 64
            run = {
                "id": 123,
                "run_attempt": 2,
                "head_sha": SOURCE_SHA,
                "head_branch": "main",
                "event": "push",
                "name": "publish-hf",
                "path": ".github/workflows/publish-hf.yml",
                "status": "completed",
                "conclusion": "success",
                "repository": {"full_name": "szl-holdings/szl-khipu"},
            }
            artifacts = {
                "artifacts": [
                    {
                        "id": 456,
                        "name": artifact_name,
                        "expired": False,
                        "digest": f"sha256:{artifact_digest}",
                        "workflow_run": {
                            "id": 123,
                            "head_branch": "main",
                            "head_sha": SOURCE_SHA,
                        },
                    }
                ]
            }
            with (
                mock.patch.object(SERVER, "_url_json", side_effect=[run, artifacts]) as lookup,
                mock.patch.object(SERVER, "_url_bytes") as raw_download,
            ):
                resolved_name, digest = SERVER._github_evidence(metadata, HF_SHA)
            self.assertEqual(resolved_name, artifact_name)
            self.assertEqual(digest, artifact_digest)
            self.assertEqual(
                lookup.call_args_list[0].args[0],
                "https://api.github.com/repos/szl-holdings/szl-khipu/actions/runs/123/attempts/2",
            )
            self.assertIn(f"name={artifact_name}", lookup.call_args_list[1].args[0])
            self.assertNotIn("/zip", lookup.call_args_list[1].args[0])
            raw_download.assert_not_called()

            corruptions = []
            wrong_attempt = copy.deepcopy(run)
            wrong_attempt["run_attempt"] = 3
            corruptions.append((wrong_attempt, artifacts))
            failed_run = copy.deepcopy(run)
            failed_run["conclusion"] = "failure"
            corruptions.append((failed_run, artifacts))
            wrong_head = copy.deepcopy(run)
            wrong_head["head_sha"] = "e" * 40
            corruptions.append((wrong_head, artifacts))
            wrong_workflow = copy.deepcopy(run)
            wrong_workflow["path"] = ".github/workflows/other.yml"
            corruptions.append((wrong_workflow, artifacts))
            expired = copy.deepcopy(artifacts)
            expired["artifacts"][0]["expired"] = True
            corruptions.append((run, expired))
            wrong_name = copy.deepcopy(artifacts)
            wrong_name["artifacts"][0]["name"] = artifact_name.replace(HF_SHA, "e" * 40)
            corruptions.append((run, wrong_name))
            wrong_artifact_head = copy.deepcopy(artifacts)
            wrong_artifact_head["artifacts"][0]["workflow_run"]["head_sha"] = "e" * 40
            corruptions.append((run, wrong_artifact_head))
            malformed_digest = copy.deepcopy(artifacts)
            malformed_digest["artifacts"][0]["digest"] = "sha256:not-a-digest"
            corruptions.append((run, malformed_digest))

            for corrupt_run, corrupt_artifacts in corruptions:
                with self.subTest(run=corrupt_run, artifacts=corrupt_artifacts):
                    with (
                        mock.patch.object(
                            SERVER,
                            "_url_json",
                            side_effect=[corrupt_run, corrupt_artifacts],
                        ),
                        self.assertRaises(ValueError),
                    ):
                        SERVER._github_evidence(metadata, HF_SHA)

    def test_publisher_and_runtime_build_the_same_injection_safe_artifact_name(self):
        manifest_digest = "b" * 64
        metadata = {
            "workflow_run_attempt": 17,
            "manifest_sha256": manifest_digest,
        }
        expected = (
            f"{PUBLISH.ARTIFACT_PREFIX}-attempt-17"
            f"-manifest-{manifest_digest}-hf-{HF_SHA}"
        )
        self.assertEqual(
            PUBLISH._deployment_artifact_name(17, manifest_digest, HF_SHA),
            expected,
        )
        self.assertEqual(SERVER._deployment_artifact_name(metadata, HF_SHA), expected)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "github-output"
            PUBLISH._append_github_output(output, expected)
            self.assertEqual(output.read_text(encoding="utf-8"), f"artifact_name={expected}\n")
            with self.assertRaisesRegex(RuntimeError, "malformed"):
                PUBLISH._append_github_output(output, expected + "\nforged=true")

        malformed = [
            (0, manifest_digest, HF_SHA),
            (1, "not-a-digest", HF_SHA),
            (1, manifest_digest, "main"),
        ]
        for attempt, manifest_sha, hf_sha in malformed:
            with self.subTest(values=(attempt, manifest_sha, hf_sha)):
                with self.assertRaises(RuntimeError):
                    PUBLISH._deployment_artifact_name(attempt, manifest_sha, hf_sha)

    def test_attested_payload_and_runtime_image_file_set_are_aligned(self):
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory) / "staging"
            runtime = Path(directory) / "runtime-app"
            staging.mkdir()
            runtime.mkdir()
            (staging / "server.py").write_text("server\n", encoding="utf-8")
            (staging / "index.html").write_text("index\n", encoding="utf-8")
            (staging / "energy.py").write_text("energy\n", encoding="utf-8")
            (staging / "Dockerfile").write_text("build-only\n", encoding="utf-8")
            (staging / "README.md").write_text("build-only\n", encoding="utf-8")
            package = staging / "szl_khipu"
            package.mkdir()
            (package / "kernel.py").write_text("kernel\n", encoding="utf-8")
            artifacts = staging / "artifacts"
            artifacts.mkdir()
            (artifacts / "receipt.json").write_text("{}\n", encoding="utf-8")

            with mock.patch.dict(os.environ, IDENTITY_ENV, clear=True):
                manifest = PUBLISH._deployment_manifest(staging)
            for name in PUBLISH.RUNTIME_ROOT_FILES:
                shutil.copy2(staging / name, runtime / name)
            for name in PUBLISH.RUNTIME_ROOT_DIRECTORIES:
                shutil.copytree(staging / name, runtime / name)
            evidence_root = runtime / "szl_khipu"
            build_info = evidence_root / "build-info.json"
            provenance = evidence_root / "hf-deployment-provenance.json"
            build_info.write_text("{}\n", encoding="utf-8")
            provenance.write_text("{}\n", encoding="utf-8")
            with (
                mock.patch.object(SERVER, "BUILD_INFO", build_info),
                mock.patch.object(SERVER, "PROVENANCE", provenance),
            ):
                runtime_records = SERVER._payload_records(runtime)
            self.assertEqual(runtime_records, manifest["files"])
            paths = {record["path"] for record in manifest["files"]}
            self.assertNotIn("Dockerfile", paths)
            self.assertNotIn("README.md", paths)
            self.assertNotIn("szl_khipu/build-info.json", paths)
            self.assertNotIn("szl_khipu/hf-deployment-provenance.json", paths)

        dockerfile = (ROOT / "space" / "Dockerfile").read_text(encoding="utf-8")
        for instruction in (
            "COPY server.py ./server.py",
            "COPY index.html ./index.html",
            "COPY energy.py ./energy.py",
            "COPY szl_khipu ./szl_khipu",
            "COPY artifacts ./artifacts",
        ):
            self.assertIn(instruction, dockerfile)
        self.assertNotIn("COPY Dockerfile", dockerfile)
        self.assertNotIn("COPY README.md", dockerfile)

    def test_manifest_digest_changes_with_the_runtime_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "server.py").write_text("one\n", encoding="utf-8")
            (root / "Dockerfile").write_text("FROM python:3.12\n", encoding="utf-8")
            (root / "README.md").write_text("build metadata\n", encoding="utf-8")
            with mock.patch.dict(os.environ, IDENTITY_ENV, clear=True):
                before = PUBLISH._deployment_manifest(root)
                (root / "server.py").write_text("two\n", encoding="utf-8")
                after = PUBLISH._deployment_manifest(root)
            self.assertEqual([item["path"] for item in before["files"]], ["server.py"])
            self.assertNotEqual(before["tree_sha256"], after["tree_sha256"])

    def test_offline_validation_and_publication_policy_are_fail_honest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provenance = root / "provenance.json"
            output = root / "github-output"
            summary = root / "summary.md"
            with mock.patch.dict(os.environ, IDENTITY_ENV, clear=True):
                self.assertEqual(
                    PUBLISH.main(["--prepare-provenance", str(provenance)]),
                    0,
                )
                self.assertEqual(
                    PUBLISH.main(["--validate-provenance", str(provenance)]),
                    0,
                )

            push_environment = {
                "GITHUB_EVENT_NAME": "push",
                "GITHUB_STEP_SUMMARY": str(summary),
            }
            with mock.patch.dict(os.environ, push_environment, clear=True):
                self.assertEqual(
                    PUBLISH.main(
                        ["--publication-policy", "--github-output", str(output)]
                    ),
                    0,
                )
            self.assertEqual(
                output.read_text(encoding="utf-8"),
                "publish_enabled=false\n",
            )
            self.assertIn("NOT DEPLOYED", summary.read_text(encoding="utf-8"))

            output.unlink()
            with mock.patch.dict(
                os.environ,
                {"GITHUB_EVENT_NAME": "workflow_dispatch"},
                clear=True,
            ):
                self.assertEqual(
                    PUBLISH.main(
                        ["--publication-policy", "--github-output", str(output)]
                    ),
                    2,
                )
            self.assertFalse(output.exists())

            with mock.patch.dict(
                os.environ,
                {"GITHUB_EVENT_NAME": "workflow_dispatch", "HF_TOKEN": "present"},
                clear=True,
            ):
                self.assertEqual(
                    PUBLISH.main(
                        ["--publication-policy", "--github-output", str(output)]
                    ),
                    0,
                )
            self.assertEqual(
                output.read_text(encoding="utf-8"),
                "publish_enabled=true\n",
            )

            provenance.write_text("{}\n", encoding="utf-8")
            with (
                mock.patch.dict(os.environ, IDENTITY_ENV, clear=True),
                self.assertRaisesRegex(RuntimeError, "does not match"),
            ):
                PUBLISH.main(["--validate-provenance", str(provenance)])

    def test_publish_workflow_gates_every_provider_side_effect(self):
        workflow = (ROOT / ".github/workflows/publish-hf.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("--validate-provenance", workflow)
        self.assertIn("--publication-policy", workflow)
        self.assertIn("NOT DEPLOYED", workflow)
        self.assertEqual(
            workflow.count("if: steps.publication.outputs.publish_enabled == 'true'"),
            3,
        )
        self.assertLess(
            workflow.index("--validate-provenance"),
            workflow.index("Install provider dependencies"),
        )


if __name__ == "__main__":
    unittest.main()
