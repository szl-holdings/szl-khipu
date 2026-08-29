#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Upload SZL KHIPU artifacts to Hugging Face org SZLHOLDINGS.

Requires HF_TOKEN (or HUGGINGFACE_HUB_TOKEN) with write on the org.
GitHub source remains canonical. Hub is the publish mirror.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
    ]

    # Package card (model repo)
    api.create_repo(f"{org}/szl-khipu", repo_type="model", exist_ok=True, private=False)
    api.upload_folder(
        folder_path=str(ROOT),
        repo_id=f"{org}/szl-khipu",
        repo_type="model",
        ignore_patterns=ignore,
        commit_message="szl-khipu 0.1.0 — kernels + tiny trained silhouettes",
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

    # Gradio Space — app.py + package (space root, not spaces/ layout)
    api.create_repo(
        f"{org}/szl-khipu",
        repo_type="space",
        exist_ok=True,
        private=False,
        space_sdk="gradio",
    )
    space_files = [
        (ROOT / "spaces/README.md", "README.md"),
        (ROOT / "spaces/app.py", "app.py"),
        (ROOT / "spaces/requirements.txt", "requirements.txt"),
    ]
    for src, dest in space_files:
        api.upload_file(
            path_or_fileobj=str(src),
            path_in_repo=dest,
            repo_id=f"{org}/szl-khipu",
            repo_type="space",
        )
    api.upload_folder(
        folder_path=str(ROOT / "szl_khipu"),
        path_in_repo="szl_khipu",
        repo_id=f"{org}/szl-khipu",
        repo_type="space",
        ignore_patterns=["__pycache__/**", "*.pyc"],
        commit_message="szl_khipu package for the Gradio space",
    )

    print("uploaded to", org)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
