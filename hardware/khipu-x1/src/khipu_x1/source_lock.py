"""Offline validator for the KHIPU-X1 cross-repository source lock."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

_SHA = re.compile(r"^[0-9a-f]{40}$")
_REPO = re.compile(r"^szl-holdings/[A-Za-z0-9_.-]+$")
_ALLOWED_ROLES = {
    "control-plane",
    "formal-proof",
    "training-publication",
    "kernel-suite",
    "attention-reference",
    "kv-reference",
    "mask-reference",
    "provenance-reference",
    "signing-reference",
    "energy-reference",
}


class SourceLockError(ValueError):
    pass


def validate_source_lock(value: Mapping[str, Any]) -> dict[str, Any]:
    if value.get("schema") != "khipu-x1-source-lock/v0.1":
        raise SourceLockError("unsupported source-lock schema")
    if value.get("hardware_status") != "UNAVAILABLE":
        raise SourceLockError("source lock must not claim hardware availability")
    repos = value.get("repositories")
    if not isinstance(repos, list) or not repos:
        raise SourceLockError("repositories must be a non-empty list")

    seen: set[str] = set()
    normalized = []
    for item in repos:
        if not isinstance(item, dict):
            raise SourceLockError("repository entry must be an object")
        name = item.get("repository")
        commit = item.get("commit")
        role = item.get("role")
        if not isinstance(name, str) or not _REPO.fullmatch(name):
            raise SourceLockError(f"invalid repository name: {name!r}")
        if name in seen:
            raise SourceLockError(f"duplicate repository: {name}")
        seen.add(name)
        if not isinstance(commit, str) or not _SHA.fullmatch(commit):
            raise SourceLockError(f"invalid commit for {name}")
        if role not in _ALLOWED_ROLES:
            raise SourceLockError(f"invalid role for {name}: {role}")
        if item.get("claim") not in {"REFERENCE_ONLY", "SOURCE_OF_TRUTH"}:
            raise SourceLockError(f"invalid claim label for {name}")
        normalized.append(dict(item))

    if [item["repository"] for item in normalized] != sorted(item["repository"] for item in normalized):
        raise SourceLockError("repository entries must be sorted")
    return dict(value)


def load_source_lock(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceLockError(f"cannot read source lock: {exc}") from exc
    if not isinstance(value, dict):
        raise SourceLockError("source lock root must be an object")
    return validate_source_lock(value)
