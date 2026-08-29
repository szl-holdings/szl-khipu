#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Upload SZL KHIPU artifacts to Hugging Face org SZLHOLDINGS.

Requires HF_TOKEN (or HUGGINGFACE_HUB_TOKEN) with write on the org.
GitHub source remains canonical. Hub is the publish mirror.

Never walks the Git root (atelier-space made upload_folder time out at 20m).
Stage allow-listed trees, then upload those.
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


def _copy_files(dst: Path, names: list[str], src_root: Path = ROOT) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for name in names:
        src = src_root / name
        if src.is_file():
            shutil.copy2(src, dst / src.name)


def _stage_model() -> Path:
    staging = Path(tempfile.mkdtemp(prefix="szl-khipu-model-"))
    _copy_files(staging, ["README.md", "LICENSE", "CARD.md", "pyproject.toml", "SECURITY.md"])
    pkg = ROOT / "szl_khipu"
    if pkg.is_dir():
        shutil.copytree(pkg, staging / "szl_khipu", ignore=IGNORE)
    hf = ROOT / "hf"
    if hf.is_dir():
        shutil.copytree(hf, staging / "hf", ignore=IGNORE)
    docs = ROOT / "docs"
    if docs.is_dir():
        shutil.copytree(docs, staging / "docs", ignore=IGNORE)
    return staging


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


def _upload_nano(api, org: str, repo: str, readme: Path, blob: Path | None, receipt: Path | None) -> None:
    api.create_repo(f"{org}/{repo}", repo_type="model", exist_ok=True, private=False)
    if readme.is_file():
        api.upload_file(
            path_or_fileobj=str(readme),
            path_in_repo="README.md",
            repo_id=f"{org}/{repo}",
            repo_type="model",
            commit_message=f"{repo} card",
        )
    if blob is not None and blob.is_file():
        api.upload_file(
            path_or_fileobj=str(blob),
            path_in_repo=blob.name,
            repo_id=f"{org}/{repo}",
            repo_type="model",
        )
    if receipt is not None and receipt.is_file():
        api.upload_file(
            path_or_fileobj=str(receipt),
            path_in_repo="TRAINING_RECEIPT.json",
            repo_id=f"{org}/{repo}",
            repo_type="model",
        )


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

    model_staging = _stage_model()
    try:
        api.create_repo(f"{org}/szl-khipu", repo_type="model", exist_ok=True, private=False)
        api.upload_folder(
            folder_path=str(model_staging),
            repo_id=f"{org}/szl-khipu",
            repo_type="model",
            commit_message="szl-khipu kernels — GitHub canonical, Hub mirror",
        )
    finally:
        shutil.rmtree(model_staging, ignore_errors=True)

    _upload_nano(
        api,
        org,
        "TinyKhipu-Nano",
        ROOT / "hf/TinyKhipu-Nano/README.md",
        nano / "tiny_khipu.npz",
        rec,
    )
    _upload_nano(
        api,
        org,
        "ReceiptAgent-Nano",
        ROOT / "hf/ReceiptAgent-Nano/README.md",
        nano / "receipt_agent.npz",
        rec,
    )
    _upload_nano(
        api,
        org,
        "Moons-Nano",
        ROOT / "hf/Moons-Nano/README.md",
        nano / "moons.npz",
        rec,
    )
    _upload_nano(
        api,
        org,
        "MiniEmbed-Nano",
        ROOT / "hf/MiniEmbed-Nano/README.md",
        nano / "mini_embed.npz",
        rec,
    )

    api.create_repo(f"{org}/szl-khipu-kernels", repo_type="model", exist_ok=True, private=False)
    api.upload_file(
        path_or_fileobj=str(ROOT / "hf/szl-khipu-kernels/README.md"),
        path_in_repo="README.md",
        repo_id=f"{org}/szl-khipu-kernels",
        repo_type="model",
        commit_message="szl-khipu-kernels card — original cuts, not rehosts",
    )

    space_staging = _stage_space()
    try:
        api.create_repo(
            f"{org}/szl-khipu",
            repo_type="space",
            space_sdk="docker",
            exist_ok=True,
            private=False,
        )
        api.upload_folder(
            folder_path=str(space_staging),
            repo_id=f"{org}/szl-khipu",
            repo_type="space",
            commit_message="hologram + package — Inference Bay / Prefix / Route LIVE",
        )
    finally:
        shutil.rmtree(space_staging, ignore_errors=True)

    print("uploaded models + hologram space to", org)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
