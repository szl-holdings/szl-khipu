#!/usr/bin/env python3
"""Protected-main publisher for the independent Gradio Proof Loom Space.

Only the three allowlisted public Python/Markdown files and SOURCE.json are sent.
Existing unrelated files are preserved; parent-commit CAS protects other writers.
No retries across auth, quota, revision, visibility, source or runtime refusals.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_REPO = "szl-holdings/szl-khipu"
TARGET = "SZLHOLDINGS/khipu-proof-loom"
FILES = {
    "spaces/proof-loom/app.py": "app.py",
    "spaces/proof-loom/README.md": "README.md",
    "szl_khipu/proof_loom.py": "proof_loom.py",
}
SHA40 = re.compile(r"[0-9a-f]{40}\Z")


class AdmissionHold(RuntimeError):
    """A reported hold, not permission to bypass or retry by another identity."""


def _identity(*, publish: bool):
    sha = os.getenv("GITHUB_SHA", "").lower()
    if not SHA40.fullmatch(sha):
        if publish:
            raise AdmissionHold("SOURCE_SHA_UNOBSERVED")
        sha = "UNOBSERVED_LOCAL_CHECK"
    if publish:
        expected = {
            "GITHUB_REPOSITORY": SOURCE_REPO,
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_WORKFLOW": "publish-proof-loom",
            "GITHUB_WORKFLOW_SHA": sha,
        }
        for key, value in expected.items():
            if os.getenv(key) != value:
                raise AdmissionHold("PROTECTED_SOURCE_AUTHORITY_MISMATCH")
    return sha


def _stage(destination: Path, sha: str) -> dict:
    if destination.exists() and any(destination.iterdir()):
        raise AdmissionHold("DESTINATION_NOT_EMPTY")
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    for source, name in FILES.items():
        path = ROOT / source
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 150_000:
            raise AdmissionHold("SOURCE_FILE_INVALID")
        raw = path.read_bytes()
        (destination / name).write_bytes(raw)
        records.append({
            "source": source, "dest": name, "size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        })
    payload = {
        "schema": "szl.khipu.proof-loom-publication/v1",
        "source_repository": SOURCE_REPO, "source_commit": sha,
        "target_space": TARGET, "files": records,
        "historical_claim": "NOT_ESTABLISHED",
        "quality_qualification": "NOT_ASSESSED",
    }
    (destination / "SOURCE.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def _readback(api, revision: str, manifest: dict, token: str):
    from huggingface_hub import hf_hub_download

    if not SHA40.fullmatch(str(revision)):
        raise AdmissionHold("PROVIDER_COMMIT_NOT_IMMUTABLE")
    for row in manifest["files"]:
        path = Path(hf_hub_download(
            repo_id=TARGET, filename=row["dest"], revision=revision,
            repo_type="space", token=token,
        ))
        raw = path.read_bytes()
        if len(raw) != row["size"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise AdmissionHold("PROVIDER_IMMUTABLE_BYTE_MISMATCH")
    path = Path(hf_hub_download(
        repo_id=TARGET, filename="SOURCE.json", revision=revision,
        repo_type="space", token=token,
    ))
    if json.loads(path.read_text(encoding="utf-8")) != manifest:
        raise AdmissionHold("PROVIDER_SOURCE_BINDING_MISMATCH")


def _runtime_readback(api) -> dict:
    # One bounded post-publication observation: no extra GPU, schedulers or secrets.
    for _ in range(18):
        state = api.get_space_runtime(TARGET)
        stage = str(getattr(state, "stage", "UNOBSERVED")).upper()
        if stage in {"ERROR", "BUILD_ERROR", "RUNTIME_ERROR", "CONFIG_ERROR", "PAUSED"}:
            raise AdmissionHold("SPACE_RUNTIME_" + stage)
        if stage == "RUNNING":
            url = "https://szlholdings-khipu-proof-loom.hf.space/config"
            try:
                with urllib.request.urlopen(
                    urllib.request.Request(
                        url, headers={"User-Agent": "szl-proof-loom-source-readback/1"}
                    ), timeout=12,
                ) as response:
                    if response.status != 200:
                        raise AdmissionHold("SPACE_CONFIG_HTTP_NOT_OK")
                    raw = response.read(512_001)
                if len(raw) > 512_000:
                    raise AdmissionHold("SPACE_CONFIG_SIZE_EXCEEDED")
                config = json.loads(raw)
                if (
                    config.get("title") != "Khipu Proof Loom"
                    or not any(x.get("type") == "model3d" for x in config.get("components", []))
                ):
                    raise AdmissionHold("SPACE_RENDERED_SOURCE_MISMATCH")
                return {
                    "status": "RUNTIME_CONFIG_OBSERVED", "stage": stage,
                    "config_url": url,
                    "config_sha256": hashlib.sha256(raw).hexdigest(),
                }
            except AdmissionHold:
                raise
            except Exception as exc:
                raise AdmissionHold(
                    "SPACE_RUNTIME_CONFIG_UNOBSERVED_" + type(exc).__name__
                ) from None
        time.sleep(10)
    raise AdmissionHold("SPACE_RUNTIME_UNOBSERVED_AFTER_BOUNDED_POLL")


def publish() -> dict:
    sha = _identity(publish=True)
    token = os.getenv("HF_ORG_TOKEN") or os.getenv("HF_TOKEN")
    if not token:
        raise AdmissionHold("HF_WRITE_AUTHORITY_UNAVAILABLE")
    from huggingface_hub import HfApi
    from huggingface_hub.errors import RepositoryNotFoundError

    api = HfApi(token=token)
    # Authentication denial is terminal; do not look for alternative credentials.
    identity = api.whoami()
    if not isinstance(identity, dict) or not identity.get("name"):
        raise AdmissionHold("HF_IDENTITY_UNOBSERVED")
    with tempfile.TemporaryDirectory(prefix="szl-proof-loom-publish-") as td:
        root = Path(td)
        manifest = _stage(root, sha)
        created_new = False
        try:
            info = api.repo_info(repo_id=TARGET, repo_type="space")
        except RepositoryNotFoundError:
            # Explicitly requested new public Space; never take over a private one.
            api.create_repo(
                repo_id=TARGET, repo_type="space", space_sdk="gradio",
                private=False, exist_ok=False,
            )
            created_new = True
            info = api.repo_info(repo_id=TARGET, repo_type="space")
        if (
            getattr(info, "private", None) is not False
            or getattr(info, "sdk", None) != "gradio"
        ):
            raise AdmissionHold("TARGET_VISIBILITY_OR_SDK_MISMATCH")
        parent = str(getattr(info, "sha", "")).lower()
        if not SHA40.fullmatch(parent):
            raise AdmissionHold("TARGET_PARENT_UNOBSERVED")
        if not created_new:
            try:
                from huggingface_hub import hf_hub_download
                prior = Path(hf_hub_download(
                    repo_id=TARGET, filename="SOURCE.json", revision=parent,
                    repo_type="space", token=token,
                ))
            except Exception as exc:
                # Existing Space without the owner's source marker is not ours.
                raise AdmissionHold(
                    "TARGET_OWNER_MARKER_UNOBSERVED_" + type(exc).__name__
                ) from None
            payload = json.loads(prior.read_text(encoding="utf-8"))
            if (
                payload.get("source_repository") != SOURCE_REPO
                or payload.get("target_space") != TARGET
            ):
                raise AdmissionHold("TARGET_OWNED_BY_OTHER_WRITER")
        commit = api.upload_folder(
            folder_path=str(root), repo_id=TARGET, repo_type="space",
            parent_commit=parent,
            commit_message="feat(proof-loom): source-bound Python 3D research lab",
        )
        revision = str(commit.oid)
        _readback(api, revision, manifest, token)
        runtime = _runtime_readback(api)
        return {
            "schema": "szl.khipu.proof-loom-deployment/v1",
            "source_commit": sha, "hf_revision": revision, "repository": TARGET,
            "readback": "PINNED_BYTES_VERIFIED", "runtime": runtime,
            "quality": "NOT_ASSESSED", "historical_claim": "NOT_ESTABLISHED",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="offline source-only staging")
    parser.add_argument("--publish", action="store_true", help="protected-main provider publish")
    args = parser.parse_args()
    if args.check == args.publish:
        parser.error("select exactly one operation")
    try:
        if args.check:
            with tempfile.TemporaryDirectory(prefix="szl-proofloom-check-") as td:
                manifest = _stage(Path(td), _identity(publish=False))
                print(json.dumps(
                    {"status": "OFFLINE_STAGE_VALID", "manifest": manifest}, sort_keys=True
                ))
        else:
            result = publish()
            Path("proof-loom-hub-publication.json").write_text(
                json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(json.dumps(result, sort_keys=True))
        return 0
    except AdmissionHold as exc:
        print(json.dumps({"status": "HOLD", "reason": str(exc)}, sort_keys=True))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
