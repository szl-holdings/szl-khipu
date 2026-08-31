#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Publish exact, source-bound SZL KHIPU artifacts to Hugging Face."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_REPOSITORY = "szl-holdings/szl-khipu"
HF_REPOSITORY = "SZLHOLDINGS/szl-khipu"
WORKFLOW_NAME = "publish-hf"
ARTIFACT_NAME = "szl-khipu-hf-provenance"
PROVENANCE_NAME = "hf-deployment-provenance.json"
RECEIPT_NAME = "hf-deployment-receipt.json"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
IGNORE = shutil.ignore_patterns(
    "__pycache__",
    "*.pyc",
    "*.pyi",
    ".git*",
    ".venv",
    "venv",
    "*.egg-info",
    ".pytest_cache",
)


def _canonical_json(payload: dict) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _write_json(path: Path, payload: dict) -> bytes:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)
    return encoded


def _identity() -> dict:
    source_commit = os.environ.get("GITHUB_SHA", "").lower()
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
    if not SHA40.fullmatch(source_commit):
        raise RuntimeError("GITHUB_SHA must be an immutable 40-hex commit")
    if not run_id.isdigit() or int(run_id) <= 0:
        raise RuntimeError("GITHUB_RUN_ID must be a positive integer")
    if not run_attempt.isdigit() or int(run_attempt) <= 0:
        raise RuntimeError("GITHUB_RUN_ATTEMPT must be a positive integer")
    return {
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": source_commit,
        "hf_repository": HF_REPOSITORY,
        "workflow_name": WORKFLOW_NAME,
        "workflow_run_id": int(run_id),
        "workflow_run_attempt": int(run_attempt),
        "artifact_name": ARTIFACT_NAME,
    }


def _stage_space() -> Path:
    staging = Path(tempfile.mkdtemp(prefix="szl-khipu-space-"))
    for name in ("Dockerfile", "server.py", "index.html", "README.md", "energy.py"):
        src = ROOT / "space" / name
        if src.is_file():
            shutil.copy2(src, staging / name)
    pkg = ROOT / "szl_khipu"
    if pkg.is_dir():
        shutil.copytree(pkg, staging / "szl_khipu", ignore=IGNORE)
    art = ROOT / "artifacts"
    if art.is_dir():
        shutil.copytree(art, staging / "artifacts", ignore=IGNORE)
    return staging


def _deployment_manifest(staging: Path) -> dict:
    files = []
    for path in sorted((item for item in staging.rglob("*") if item.is_file())):
        content = path.read_bytes()
        files.append(
            {
                "path": path.relative_to(staging).as_posix(),
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
            }
        )
    core = {
        "schema": "szl.hf-deployment-tree/v2",
        **_identity(),
        "files": files,
    }
    return {
        **core,
        "tree_sha256": hashlib.sha256(_canonical_json(core)).hexdigest(),
    }


def prepare_provenance(output: Path) -> dict:
    staging = _stage_space()
    try:
        manifest = _deployment_manifest(staging)
        _write_json(output, manifest)
        return manifest
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _validated_provenance(staging: Path, path: Path) -> tuple[dict, bytes]:
    try:
        encoded = path.read_bytes()
        supplied = json.loads(encoded.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"deployment provenance unavailable: {exc}") from exc
    expected = _deployment_manifest(staging)
    if supplied != expected:
        raise RuntimeError("deployment provenance does not match the exact staged tree")
    return supplied, encoded


def _put(api, repo: str, local: Path, dest: str, kind: str, message: str) -> None:
    if not local.is_file():
        print("skip missing", local, file=sys.stderr)
        return
    print("uploading", dest, "->", repo, flush=True)
    api.upload_file(
        path_or_fileobj=str(local),
        path_in_repo=dest,
        repo_id=repo,
        repo_type=kind,
        commit_message=message,
    )
    print("uploaded", dest, "->", repo, flush=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prepare-provenance",
        metavar="PATH",
        help="write the exact staged-tree manifest and exit without a Hub mutation",
    )
    parser.add_argument("--provenance-file", default=PROVENANCE_NAME)
    parser.add_argument("--receipt-file", default=RECEIPT_NAME)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.prepare_provenance:
        manifest = prepare_provenance(Path(args.prepare_provenance))
        print("prepared staged deployment tree", manifest["tree_sha256"])
        return 0

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    if not token:
        print("HF_TOKEN unset — Hub publish blocked. GitHub remains the source.", file=sys.stderr)
        return 2
    from huggingface_hub import HfApi

    org = os.environ.get("HF_ORG", "SZLHOLDINGS")
    if org != "SZLHOLDINGS":
        raise RuntimeError("HF_ORG must remain the governed SZLHOLDINGS target")
    api = HfApi(token=token)
    nano = ROOT / "artifacts"
    rec = nano / "TRAINING_RECEIPT.json"

    nanos = [
        ("TinyKhipu-Nano", ROOT / "hf/TinyKhipu-Nano/README.md", nano / "tiny_khipu.npz"),
        ("ReceiptAgent-Nano", ROOT / "hf/ReceiptAgent-Nano/README.md", nano / "receipt_agent.npz"),
        ("Moons-Nano", ROOT / "hf/Moons-Nano/README.md", nano / "moons.npz"),
        ("MiniEmbed-Nano", ROOT / "hf/MiniEmbed-Nano/README.md", nano / "mini_embed.npz"),
    ]
    for repo, readme, blob in nanos:
        rid = f"{org}/{repo}"
        _put(api, rid, readme, "README.md", "model", f"{repo} card")
        _put(api, rid, blob, blob.name, "model", f"{repo} weights")
        _put(api, rid, rec, "TRAINING_RECEIPT.json", "model", f"{repo} receipt")

    _put(
        api,
        f"{org}/szl-khipu-kernels",
        ROOT / "hf/szl-khipu-kernels/README.md",
        "README.md",
        "model",
        "szl-khipu-kernels card — original cuts, not rehosts",
    )
    _put(
        api,
        f"{org}/szl-khipu",
        ROOT / "README.md",
        "README.md",
        "model",
        "szl-khipu card pointer — GitHub canonical",
    )

    provenance_path = Path(args.provenance_file).resolve()
    receipt_path = Path(args.receipt_file).resolve()
    staging = _stage_space()
    try:
        manifest, manifest_bytes = _validated_provenance(staging, provenance_path)
        shutil.copy2(provenance_path, staging / PROVENANCE_NAME)
        manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
        build_info = {
            "schema": "szl.hf-build-info/v2",
            **_identity(),
            "manifest_sha256": manifest_sha256,
            "tree_sha256": manifest["tree_sha256"],
        }
        _write_json(staging / "build-info.json", build_info)

        sid = f"{org}/szl-khipu"
        print("uploading hologram space", sid, flush=True)
        commit_info = api.upload_folder(
            folder_path=str(staging),
            repo_id=sid,
            repo_type="space",
            commit_message="source-bound hologram + package",
            delete_patterns=["*", "**/*"],
        )
        hf_revision = str(getattr(commit_info, "oid", "")).lower()
        if not SHA40.fullmatch(hf_revision):
            raise RuntimeError("Hugging Face upload did not return an immutable commit")
        receipt = {
            "schema": "szl.hf-deployment-receipt/v2",
            **_identity(),
            "manifest_sha256": manifest_sha256,
            "tree_sha256": manifest["tree_sha256"],
            "hf_revision": hf_revision,
        }
        _write_json(receipt_path, receipt)
        print("uploaded source-bound hologram", sid, hf_revision, flush=True)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    print("uploaded models + source-bound hologram space to", org)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
