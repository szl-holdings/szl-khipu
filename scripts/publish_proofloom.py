#!/usr/bin/env python3
"""Protected-main publisher for the independent Gradio Proof Loom Space.

Only the three allowlisted public Python/Markdown files and SOURCE.json are sent.
Existing unrelated files are preserved; parent-commit CAS protects other writers.
No retries across auth, quota, revision, visibility, source or runtime refusals.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
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
    "research/rr_discovery/learner.py": "hypothesis.py",
    "research/rr_discovery/receipts/sequence_scout_v1.json": "sequence_scout_v1.json",
}
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
# One-shot recovery of the exact owner-created empty Space after the 2026-11-17
# Hub card-metadata 400, with immutable provider readback and no file deletion.
# GitHub Action 44033724202 journal pins the CREATE_INTENT / created SHA.
OWNER_STUB_REVISION = "d67dccc2e8167d43cca9b05847ef1f5fca894f43"
OWNER_STUB_README_SHA256 = "bdcf9cffdc3328160cd25d1bb646c6b13173abd217fb2c0457f58bd9f6129c7a"


class AdmissionHold(RuntimeError):
    """A reported hold, not permission to bypass or retry by another identity."""


def _journal(status: str, **facts: object) -> None:
    """Append one secret-free local provider-attempt event, including uncertainty."""
    path = Path("proof-loom-publication.journal.jsonl")
    if path.is_symlink():
        raise AdmissionHold("PUBLICATION_JOURNAL_SYMLINK")
    payload = {
        "schema": "szl.khipu.proof-loom-publication-journal/v1",
        "observed_utc": datetime.now(timezone.utc).isoformat(),
        "status": status, "target": TARGET, **facts,
    }
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _validate_space_card(raw: bytes) -> None:
    """Fail offline on the exact 60-character Hub metadata cap."""
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise AdmissionHold("SPACE_CARD_NOT_UTF8") from exc
    if len(lines) < 3 or lines[0] != "---":
        raise AdmissionHold("SPACE_CARD_FRONTMATTER_MISSING")
    try:
        closing = lines.index("---", 1)
    except ValueError as exc:
        raise AdmissionHold("SPACE_CARD_FRONTMATTER_UNTERMINATED") from exc
    descriptions = [
        line.split(":", 1)[1].strip().strip("'\\\"")
        for line in lines[1:closing]
        if line.startswith("short_description:")
    ]
    if len(descriptions) != 1 or not 0 < len(descriptions[0]) <= 60:
        raise AdmissionHold("SPACE_CARD_SHORT_DESCRIPTION_INVALID")


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
        if name == "README.md":
            _validate_space_card(raw)
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


def _runtime_readback(api, source_sha: str, manifest_sha: str) -> dict:
    # One bounded post-publication observation: no extra GPU, schedulers or secrets.
    if not SHA40.fullmatch(source_sha) or re.fullmatch(r"[0-9a-f]{64}", manifest_sha) is None:
        raise AdmissionHold("RUNTIME_EXPECTED_SOURCE_INVALID")
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
                components = config.get("components", [])
                if (
                    config.get("title") != "Khipu Proof Loom"
                    or not isinstance(components, list)
                    or not any(
                        isinstance(x, dict) and x.get("type") == "model3d"
                        for x in components
                    )
                ):
                    raise AdmissionHold("SPACE_RENDERED_SOURCE_MISMATCH")
                expected_marker = (
                    f'data-szl-source-sha="{source_sha}"'
                    f' data-szl-manifest-sha256="{manifest_sha}"'
                )
                if not any(
                    isinstance(x, dict)
                    and x.get("type") == "html"
                    and isinstance(x.get("props"), dict)
                    and expected_marker in str(x["props"].get("value", ""))
                    for x in components
                ):
                    raise AdmissionHold("SPACE_RUNTIME_SOURCE_MISMATCH")
                dependencies = config.get("dependencies")
                if not isinstance(dependencies, list) or not any(
                    isinstance(item, dict)
                    and item.get("api_name") == "discover"
                    for item in dependencies
                ):
                    raise AdmissionHold("SPACE_DISCOVERY_API_UNOBSERVED")
                expensive = [
                    item for item in dependencies
                    if isinstance(item, dict)
                    and item.get("api_name") in ("discover", "recompute")
                ]
                # Gradio's public /config confirms that events use the queue,
                # but does not expose concurrency_limit/concurrency_id. The
                # exact-source local real-SDK smoke tests those backend values.
                if len(expensive) != 2 or any(
                    item.get("queue") is not True for item in expensive
                ):
                    raise AdmissionHold("SPACE_CALLBACK_QUEUE_DISABLED")
                opt_ins = [
                    item.get("props", {}) for item in components
                    if isinstance(item, dict)
                    and item.get("type") == "checkbox"
                    and isinstance(item.get("props"), dict)
                    and "Enable optional CPU symbolic training"
                        in item["props"].get("label", "")
                ]
                if len(opt_ins) != 1 or opt_ins[0].get("value") is not False:
                    raise AdmissionHold("SPACE_OPTIONAL_TRAINING_NOT_DEFAULT_OFF")
                return {
                    "status": "RUNTIME_SOURCE_VERIFIED", "stage": stage,
                    "source_commit": source_sha,
                    "manifest_sha256": manifest_sha,
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


def _verify_owner_stub(api, parent: str, token: str) -> None:
    """Recover only the exact empty Space created by prior accepted owner lane."""
    if parent != OWNER_STUB_REVISION:
        raise AdmissionHold("OWNER_STUB_PARENT_CHANGED")
    pinned = api.space_info(TARGET, revision=parent, files_metadata=True)
    paths = {row.rfilename for row in (getattr(pinned, "siblings", None) or [])}
    if (
        pinned.sha != parent
        or pinned.private is not False
        or pinned.sdk != "gradio"
        or paths != {".gitattributes", "README.md"}
    ):
        raise AdmissionHold("OWNER_STUB_FILE_SET_OR_IDENTITY_CHANGED")
    from huggingface_hub import hf_hub_download
    path = Path(hf_hub_download(
        repo_id=TARGET, filename="README.md", revision=parent,
        repo_type="space", token=token,
    ))
    if hashlib.sha256(path.read_bytes()).hexdigest() != OWNER_STUB_README_SHA256:
        raise AdmissionHold("OWNER_STUB_README_BYTES_CHANGED")
    _journal("PINNED_OWNER_STUB_RECONCILED", prior_run_id=44033724202,
             exact_stub_parent=parent, prior_readme_sha256=OWNER_STUB_README_SHA256)


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
    orgs = identity.get("orgs")
    if not isinstance(orgs, list) or not any(
        isinstance(item, dict)
        and item.get("name") == "SZLHOLDINGS"
        and item.get("roleInOrg") == "admin"
        for item in orgs
    ):
        raise AdmissionHold("HF_ORG_ADMIN_AUTHORITY_UNVERIFIED")
    # Enumerate this explicitly authorized org once. A not-found response alone
    # could mask a private repo or an access denial; never infer free namespace.
    org_spaces = list(api.list_spaces(author="SZLHOLDINGS", limit=200))
    if len(org_spaces) >= 200:
        raise AdmissionHold("HF_SPACE_DISCOVERY_CAPPED")
    target_in_catalog = any(getattr(item, "id", None) == TARGET for item in org_spaces)
    with tempfile.TemporaryDirectory(prefix="szl-proof-loom-publish-") as td:
        root = Path(td)
        manifest = _stage(root, sha)
        manifest_sha = hashlib.sha256((root / "SOURCE.json").read_bytes()).hexdigest()
        created_new = False
        try:
            info = api.repo_info(repo_id=TARGET, repo_type="space")
        except RepositoryNotFoundError as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if status_code != 404 or target_in_catalog:
                raise AdmissionHold("TARGET_VISIBILITY_OR_AUTH_AMBIGUOUS") from None
            # Namespace absent from the complete authorized org catalog; fail
            # rather than treating a 401/403/429 as evidence of absence.
            _journal("CREATE_INTENT", source_commit=sha, manifest_sha256=manifest_sha,
                     catalog_count=len(org_spaces))
            api.create_repo(
                repo_id=TARGET, repo_type="space", space_sdk="gradio",
                private=False, exist_ok=False,
            )
            _journal("CREATED_NO_SOURCE_UPLOAD", source_commit=sha,
                     manifest_sha256=manifest_sha)
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
            from huggingface_hub import hf_hub_download
            from huggingface_hub.errors import EntryNotFoundError
            try:
                prior = Path(hf_hub_download(
                    repo_id=TARGET, filename="SOURCE.json", revision=parent,
                    repo_type="space", token=token,
                ))
            except EntryNotFoundError as exc:
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
                if status_code != 404:
                    raise AdmissionHold("TARGET_OWNER_MARKER_AUTH_AMBIGUOUS") from None
                _verify_owner_stub(api, parent, token)
            except Exception as exc:
                raise AdmissionHold(
                    "TARGET_OWNER_MARKER_UNOBSERVED_" + type(exc).__name__
                ) from None
            else:
                payload = json.loads(prior.read_text(encoding="utf-8"))
                if (
                    payload.get("source_repository") != SOURCE_REPO
                    or payload.get("target_space") != TARGET
                ):
                    raise AdmissionHold("TARGET_OWNED_BY_OTHER_WRITER")
        _journal("UPLOAD_INTENT", source_commit=sha, manifest_sha256=manifest_sha,
                 expected_parent=parent)
        commit = api.upload_folder(
            folder_path=str(root), repo_id=TARGET, repo_type="space",
            parent_commit=parent,
            commit_message="feat(proof-loom): source-bound Python 3D research lab",
        )
        revision = str(commit.oid)
        if not SHA40.fullmatch(revision):
            raise AdmissionHold("PROVIDER_COMMIT_NOT_IMMUTABLE")
        _journal("HUB_COMMIT_ACCEPTED_UNVERIFIED", source_commit=sha,
                 manifest_sha256=manifest_sha, hf_revision=revision)
        _readback(api, revision, manifest, token)
        _journal("HUB_BYTES_VERIFIED_RUNTIME_UNOBSERVED", source_commit=sha,
                 manifest_sha256=manifest_sha, hf_revision=revision)
        runtime = _runtime_readback(api, sha, manifest_sha)
        _journal("RUNTIME_SOURCE_VERIFIED", source_commit=sha,
                 manifest_sha256=manifest_sha, hf_revision=revision,
                 config_sha256=runtime["config_sha256"])
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
