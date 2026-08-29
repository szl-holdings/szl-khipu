#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Upload SZL KHIPU artifacts to Hugging Face org SZLHOLDINGS.

Requires HF_TOKEN (or HUGGINGFACE_HUB_TOKEN) with write on the org.
GitHub source remains canonical. Hub is the publish mirror.

Small cards first. Never walk the Git root. The szl-khipu model repo
is bloated with a historical atelier tree — do not upload_folder it.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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


def _put(api, repo: str, local: Path, dest: str, kind: str, message: str) -> None:
    if not local.is_file():
        print("skip missing", local, file=sys.stderr)
        return
    api.upload_file(
        path_or_fileobj=str(local),
        path_in_repo=dest,
        repo_id=repo,
        repo_type=kind,
        commit_message=message,
    )
    print("uploaded", dest, "->", repo)


def main() -> int:
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    if not token:
        print("HF_TOKEN unset — skip Hub upload. GitHub remains the source.", file=sys.stderr)
        return 2
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    org = os.environ.get("HF_ORG", "SZLHOLDINGS")
    nano = ROOT / "artifacts"
    rec = nano / "TRAINING_RECEIPT.json"

    # Cards + weights first so a timeout still leaves the estate honest.
    nanos = [
        ("TinyKhipu-Nano", ROOT / "hf/TinyKhipu-Nano/README.md", nano / "tiny_khipu.npz"),
        ("ReceiptAgent-Nano", ROOT / "hf/ReceiptAgent-Nano/README.md", nano / "receipt_agent.npz"),
        ("Moons-Nano", ROOT / "hf/Moons-Nano/README.md", nano / "moons.npz"),
        ("MiniEmbed-Nano", ROOT / "hf/MiniEmbed-Nano/README.md", nano / "mini_embed.npz"),
    ]
    for repo, readme, blob in nanos:
        rid = f"{org}/{repo}"
        api.create_repo(rid, repo_type="model", exist_ok=True, private=False)
        _put(api, rid, readme, "README.md", "model", f"{repo} card")
        _put(api, rid, blob, blob.name, "model", f"{repo} weights")
        _put(api, rid, rec, "TRAINING_RECEIPT.json", "model", f"{repo} receipt")

    kid = f"{org}/szl-khipu-kernels"
    api.create_repo(kid, repo_type="model", exist_ok=True, private=False)
    _put(
        api,
        kid,
        ROOT / "hf/szl-khipu-kernels/README.md",
        "README.md",
        "model",
        "szl-khipu-kernels card — original cuts, not rehosts",
    )

    # Package card pointer only — do not re-upload the bloated model tree.
    _put(
        api,
        f"{org}/szl-khipu",
        ROOT / "README.md",
        "README.md",
        "model",
        "szl-khipu card pointer — GitHub canonical",
    )
    _put(
        api,
        f"{org}/szl-khipu",
        ROOT / "hf/szl-khipu-kernels/README.md",
        "hf/szl-khipu-kernels/README.md",
        "model",
        "szl-khipu original-cut kernel card",
    )

    staging = _stage_space()
    try:
        sid = f"{org}/szl-khipu"
        api.create_repo(sid, repo_type="space", space_sdk="docker", exist_ok=True, private=False)
        api.upload_folder(
            folder_path=str(staging),
            repo_id=sid,
            repo_type="space",
            commit_message="hologram + package — Inference Bay / Prefix / Route LIVE",
        )
        print("uploaded hologram space", sid)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    print("uploaded models + hologram space to", org)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
