# SPDX-License-Identifier: Apache-2.0
"""Exact-byte, research-only Khipu Yachay release asset preflight.

The expected digests were checked against the Git object bytes in PR #121 at
b16cc3e3f8ffdb776ebb7b0b46263e58a77b6929, not against CRLF-transformed
Windows worktree copies. This static source contract is not a signature,
external witness, cultural rights clearance or immutable deployed image.
Update ONLY after reviewed Git-source and model-revision changes.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

# Relative to research/khipu_yachay/ and intentionally bounded. Each expected
# length and digest is an exact Git release input, NOT a semantic dataset verdict.
ASSET_PINS = {
    "model/training_receipt.json": (
        1688, "ce5821a32e64b02a350419d0233156c06910efa7f8ea2bc030e22e014405b7c2"
    ),
    "model/yachay_nb_v0.json": (
        15980, "bf346facd30fa7abdabdb2dc8f5aa67058c122f98a7cf2b2d626f5cd03470646"
    ),
    "data/synthetic_train.jsonl": (
        100116, "12a602ffad35d32d7ad70225bb35e340f3ed2e67fddfa3b4ab1c22b544c28b2a"
    ),
    "data/synthetic_eval.jsonl": (
        14956, "0a9a7e5a13ee6cf6d8c8321733f8bd696f24c79f9a1edd685dd9198d4ebb50f7"
    ),
    "data/sources.jsonl": (
        5915, "c0713ee09d1fc78eef170cdfa0800c4031adfa4ec6aca4053b6b4e0d4ffe08e9"
    ),
    "data/okr_kh_index.jsonl": (
        262548, "3034308f81df0a953f7fef6f6cd4304a6a33e1f76d0b510dd4cf61153417a990"
    ),
    "data/okr_registry_provenance.json": (
        715, "f0286a89aae78a2e59bb1749fcf9d724720c46172989be12f462661459cf5c23"
    ),
}


class AssetBindingError(ValueError):
    """A required research artifact is missing or not the reviewed bytes."""


def _fail(reason: str, relative: str) -> None:
    # Preserve the release-stager's existing model error contract; changing
    # verification order must not make callers treat the same fault differently.
    if relative == "model/yachay_nb_v0.json":
        raise AssetBindingError("MODEL_DIGEST_MISMATCH")
    raise AssetBindingError(reason + ":" + relative)


def verify_assets(project: Path) -> dict[str, str]:
    """Fail before any model, dataset or Space publication stage can start."""
    if not isinstance(project, Path):
        raise AssetBindingError("PROJECT_PATH_REQUIRED")
    observed: dict[str, str] = {}
    for relative, (expected_size, expected_hash) in ASSET_PINS.items():
        file = project / relative
        try:
            # No arbitrary path from a caller; all names are literals in source.
            if file.is_symlink() or not file.is_file() or file.stat().st_size != expected_size:
                _fail("ASSET_BYTES_OR_TYPE_MISMATCH", relative)
            data = file.read_bytes()
        except OSError:
            _fail("ASSET_NOT_OBSERVED", relative)
        actual = hashlib.sha256(data).hexdigest()
        if len(data) != expected_size or actual != expected_hash:
            _fail("ASSET_SHA256_MISMATCH", relative)
        observed[relative] = actual
    return observed
