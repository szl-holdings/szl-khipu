#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Upload SZL KHIPU artifacts to Hugging Face org SZLHOLDINGS.

Requires HF_TOKEN (or HUGGINGFACE_HUB_TOKEN) with write on the org.
GitHub source remains canonical. Hub is the publish mirror.

Full-repo upload_folder of the Git tree timed out at 20m. This script
allow-lists the model card, the package, and the hologram payload.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _stage_space() -> Path:
    staging = Path(tempfile.mkdtemp(prefix="szl-khipu-space-"))
    for name in ("Dockerfile", "server.py", "index.html", "README.md", "energy.py"):
        src = ROOT / "space" / name
        if src.is_file():
            shutil.copy2(src, staging / name)
    pkg = ROOT / "szl_khipu"
    if pkg.is_dir():
        shutil.copytree(
            pkg,
            staging / "szl_khipu",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyi"),
        )
    return staging


def main() -> int:
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    if not token:
        print("HF_TOKEN unset — skip Hub upload. GitHub remains the source.", file=sys.stderr)
        return 2
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    org = os.environ.get("HF_ORG", "SZLHOLDINGS")
    ignore = [
        ".git*",
        ".venv/**",
        "venv/**",
        "__pycache__/**",
        "*.pyc",
        "*.egg-info/**",
        ".pytest_cache/**",
        ".github/**",
        "torch-ext/**",
        "tests/**",
        "artifacts/**",
        "spaces/**",
    ]

    # Package card (model repo) — allowlisted, not the whole git tree.
    api.create_repo(f"{org}/szl-khipu", repo_type="model", exist_ok=True, private=False)
    api.upload_folder(
        folder_path=str(ROOT),
        repo_id=f"{org}/szl-khipu",
        repo_type="model",
        allow_patterns=[
            "README.md",
            "LICENSE",
            "CARD.md",
            "pyproject.toml",
            "SECURITY.md",
            "szl_khipu/**",
            "hf/**",
            "docs/**",
        ],
        ignore_patterns=ignore,
        commit_message="szl-khipu kernels — GitHub canonical, Hub mirror",
    )

    nano = ROOT / "artifacts"

    api.create_repo(f"{org}/TinyKhipu-Nano", repo_type="model", exist_ok=True, private=False)
    api.upload_file(
        path_or_fileobj=str(ROOT / "hf/TinyKhipu-Nano/README.md"),
        path_in_repo="README.md",
        repo_id=f"{org}/TinyKhipu-Nano",
        repo_type="model",
        commit_message="TinyKhipu-Nano card",
    )
    tk = nano / "tiny_khipu.npz"
    if tk.exists():
        api.upload_file(
            path_or_fileobj=str(tk),
            path_in_repo="tiny_khipu.npz",
            repo_id=f"{org}/TinyKhipu-Nano",
            repo_type="model",
        )
    rec = nano / "TRAINING_RECEIPT.json"
    if rec.exists():
        api.upload_file(
            path_or_fileobj=str(rec),
            path_in_repo="TRAINING_RECEIPT.json",
            repo_id=f"{org}/TinyKhipu-Nano",
            repo_type="model",
        )

    api.create_repo(f"{org}/ReceiptAgent-Nano", repo_type="model", exist_ok=True, private=False)
    api.upload_file(
        path_or_fileobj=str(ROOT / "hf/ReceiptAgent-Nano/README.md"),
        path_in_repo="README.md",
        repo_id=f"{org}/ReceiptAgent-Nano",
        repo_type="model",
        commit_message="ReceiptAgent-Nano card",
    )
    ra = nano / "receipt_agent.npz"
    if ra.exists():
        api.upload_file(
            path_or_fileobj=str(ra),
            path_in_repo="receipt_agent.npz",
            repo_id=f"{org}/ReceiptAgent-Nano",
            repo_type="model",
        )

    api.create_repo(f"{org}/szl-khipu-kernels", repo_type="model", exist_ok=True, private=False)
    api.upload_file(
        path_or_fileobj=str(ROOT / "hf/szl-khipu-kernels/README.md"),
        path_in_repo="README.md",
        repo_id=f"{org}/szl-khipu-kernels",
        repo_type="model",
        commit_message="szl-khipu-kernels card",
    )

    for nano_id, card, blob in [
        ("Moons-Nano", "hf/Moons-Nano/README.md", "moons.npz"),
        ("MiniEmbed-Nano", "hf/MiniEmbed-Nano/README.md", "mini_embed.npz"),
    ]:
        api.create_repo(f"{org}/{nano_id}", repo_type="model", exist_ok=True, private=False)
        api.upload_file(
            path_or_fileobj=str(ROOT / card),
            path_in_repo="README.md",
            repo_id=f"{org}/{nano_id}",
            repo_type="model",
            commit_message=f"{nano_id} card",
        )
        art = nano / blob
        if art.exists():
            api.upload_file(
                path_or_fileobj=str(art),
                path_in_repo=blob,
                repo_id=f"{org}/{nano_id}",
                repo_type="model",
            )
        if rec.exists():
            api.upload_file(
                path_or_fileobj=str(rec),
                path_in_repo="TRAINING_RECEIPT.json",
                repo_id=f"{org}/{nano_id}",
                repo_type="model",
            )

    # Docker hologram Space: assemble flatten payload (server + package).
    # Do not create_repo(..., space_sdk="gradio") — that trips HfFolder RUNTIME_ERROR.
    staging = _stage_space()
    try:
        api.create_repo(
            f"{org}/szl-khipu",
            repo_type="space",
            space_sdk="docker",
            exist_ok=True,
            private=False,
        )
        api.upload_folder(
            folder_path=str(staging),
            repo_id=f"{org}/szl-khipu",
            repo_type="space",
            commit_message="hologram + package — GreenLight / Anatomy LIVE",
        )
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    print("uploaded models + hologram space to", org)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
