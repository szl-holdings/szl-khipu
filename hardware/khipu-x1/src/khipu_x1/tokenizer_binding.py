"""Bounded local tokenizer-artifact binding for KHIPU-X1.

The binder hashes and describes an explicit set of well-known local tokenizer
artifacts. It does not execute a tokenizer, render a chat template, import model
code, or access the network.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .kids import canonical_json_bytes
from .receipt import ReceiptChain


class TokenizerBindingError(ValueError):
    """Raised when tokenizer artifacts violate the bounded binding contract."""


_KNOWN_ARTIFACTS: tuple[tuple[str, str, bool], ...] = (
    ("tokenizer.json", "application/json", True),
    ("tokenizer.model", "application/octet-stream", True),
    ("sentencepiece.bpe.model", "application/octet-stream", True),
    ("spiece.model", "application/octet-stream", True),
    ("vocab.json", "application/json", True),
    ("vocab.txt", "text/plain", True),
    ("merges.txt", "text/plain", False),
    ("tokenizer_config.json", "application/json", False),
    ("special_tokens_map.json", "application/json", False),
    ("added_tokens.json", "application/json", False),
    ("chat_template.jinja", "text/plain", False),
)

_SPECIAL_TOKEN_NAMES = (
    "bos_token",
    "eos_token",
    "unk_token",
    "sep_token",
    "pad_token",
    "cls_token",
    "mask_token",
    "additional_special_tokens",
)


@dataclass(frozen=True)
class TokenizerArtifact:
    path: str
    size: int
    sha256: str
    media_type: str
    vocabulary_source: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "size": self.size,
            "sha256": self.sha256,
            "media_type": self.media_type,
            "vocabulary_source": self.vocabulary_source,
        }


@dataclass(frozen=True)
class SpecialTokenBinding:
    name: str
    canonical_value_json: str
    token_id: int | None
    sources: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "canonical_value_json": self.canonical_value_json,
            "token_id": self.token_id,
            "sources": list(self.sources),
        }


@dataclass(frozen=True)
class ChatTemplateBinding:
    source: str
    representation: str
    sha256: str
    byte_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "representation": self.representation,
            "sha256": self.sha256,
            "byte_count": self.byte_count,
        }


@dataclass(frozen=True)
class TokenizerBinding:
    root: str
    artifacts: tuple[TokenizerArtifact, ...]
    special_tokens: tuple[SpecialTokenBinding, ...]
    chat_templates: tuple[ChatTemplateBinding, ...]
    total_bytes: int
    manifest_digest: str
    receipt_chain: ReceiptChain
    status: str = "LOCAL_TOKENIZER_ARTIFACT_BINDING"
    tokenizer_execution: str = "NOT_PERFORMED"
    network_access: str = "NOT_PERFORMED"

    def manifest(self) -> dict[str, Any]:
        return {
            "schema": "khipu-tokenizer-artifact-binding/v0.1",
            "status": self.status,
            "root": self.root,
            "artifacts": [artifact.as_dict() for artifact in self.artifacts],
            "special_tokens": [token.as_dict() for token in self.special_tokens],
            "chat_templates": [template.as_dict() for template in self.chat_templates],
            "total_bytes": self.total_bytes,
            "tokenizer_execution": self.tokenizer_execution,
            "chat_template_execution": "NOT_PERFORMED",
            "network_access": self.network_access,
            "hardware_status": "UNAVAILABLE",
            "energy_j": None,
            "energy_status": "UNAVAILABLE",
        }

    def report(self) -> dict[str, Any]:
        verified, first_break, reason = self.receipt_chain.verify()
        return {
            **self.manifest(),
            "manifest_digest": self.manifest_digest,
            "receipt_head": self.receipt_chain.head,
            "receipt_verified": verified,
            "receipt_first_break": first_break,
            "receipt_reason": reason,
        }


def _positive_bound(name: str, value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise TokenizerBindingError(f"{name} must be a positive integer")
    return value


def _identity(stat: os.stat_result) -> tuple[int, int, int, int]:
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)


def _safe_root(root: str | Path) -> Path:
    candidate = Path(root)
    if candidate.is_symlink():
        raise TokenizerBindingError("symbolic-link tokenizer root is forbidden")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_dir():
        raise TokenizerBindingError("tokenizer root must be a local directory")
    return resolved


def _safe_file(root: Path, name: str) -> Path:
    path = root / name
    if path.is_symlink():
        raise TokenizerBindingError(f"symbolic-link tokenizer artifact is forbidden: {name}")
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise TokenizerBindingError(f"tokenizer artifact escapes root: {name}") from exc
    if not resolved.is_file():
        raise TokenizerBindingError(f"tokenizer artifact is not a regular file: {name}")
    return resolved


def _hash_file(path: Path, *, max_file_bytes: int) -> tuple[int, str, bytes | None]:
    before = path.stat()
    if before.st_size > max_file_bytes:
        raise TokenizerBindingError(f"tokenizer artifact exceeds byte bound: {path.name}")
    identity = _identity(before)
    digest = hashlib.sha256()
    capture = bytearray() if before.st_size <= 16 * 1024 * 1024 else None
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
            if capture is not None:
                capture.extend(block)
        after = os.fstat(handle.fileno())
    if _identity(after) != identity:
        raise TokenizerBindingError(f"tokenizer artifact changed while hashing: {path.name}")
    return before.st_size, digest.hexdigest(), bytes(capture) if capture is not None else None


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TokenizerBindingError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _parse_json(name: str, raw: bytes | None) -> Any:
    if raw is None:
        raise TokenizerBindingError(
            f"metadata JSON exceeds the 16 MiB parsing ceiling: {name}"
        )
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise TokenizerBindingError(f"tokenizer metadata is not UTF-8: {name}") from exc
    try:
        return json.loads(text, object_pairs_hook=_unique_object)
    except TokenizerBindingError:
        raise
    except json.JSONDecodeError as exc:
        raise TokenizerBindingError(f"invalid tokenizer JSON: {name}") from exc


def _canonical_value(value: Any) -> str:
    try:
        return canonical_json_bytes(value).decode("utf-8")
    except (TypeError, ValueError) as exc:
        raise TokenizerBindingError("special-token metadata is not canonical JSON") from exc


def _extract_special_tokens(
    tokenizer_config: dict[str, Any] | None,
    special_map: dict[str, Any] | None,
) -> tuple[SpecialTokenBinding, ...]:
    values: dict[str, tuple[str, set[str]]] = {}
    for source, document in (
        ("tokenizer_config.json", tokenizer_config),
        ("special_tokens_map.json", special_map),
    ):
        if document is None:
            continue
        for name in _SPECIAL_TOKEN_NAMES:
            if name not in document:
                continue
            canonical = _canonical_value(document[name])
            existing = values.get(name)
            if existing is not None and existing[0] != canonical:
                raise TokenizerBindingError(
                    f"conflicting special-token declaration for {name}"
                )
            if existing is None:
                values[name] = (canonical, {source})
            else:
                existing[1].add(source)

    ids: dict[str, int] = {}
    if tokenizer_config is not None:
        for name in _SPECIAL_TOKEN_NAMES:
            if name == "additional_special_tokens":
                continue
            key = f"{name}_id"
            if key not in tokenizer_config or tokenizer_config[key] is None:
                continue
            value = tokenizer_config[key]
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise TokenizerBindingError(f"{key} must be a non-negative integer")
            ids[name] = value
            if name not in values:
                values[name] = ("null", {"tokenizer_config.json"})

    return tuple(
        SpecialTokenBinding(
            name=name,
            canonical_value_json=values[name][0],
            token_id=ids.get(name),
            sources=tuple(sorted(values[name][1])),
        )
        for name in sorted(values)
    )


def _extract_chat_templates(
    tokenizer_config: dict[str, Any] | None,
    chat_template_file: bytes | None,
) -> tuple[ChatTemplateBinding, ...]:
    bindings: list[ChatTemplateBinding] = []
    if tokenizer_config is not None and "chat_template" in tokenizer_config:
        raw = canonical_json_bytes(tokenizer_config["chat_template"])
        bindings.append(
            ChatTemplateBinding(
                source="tokenizer_config.json:chat_template",
                representation="CANONICAL_JSON",
                sha256=hashlib.sha256(raw).hexdigest(),
                byte_count=len(raw),
            )
        )
    if chat_template_file is not None:
        try:
            chat_template_file.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise TokenizerBindingError("chat_template.jinja is not UTF-8") from exc
        bindings.append(
            ChatTemplateBinding(
                source="chat_template.jinja",
                representation="UTF8_BYTES",
                sha256=hashlib.sha256(chat_template_file).hexdigest(),
                byte_count=len(chat_template_file),
            )
        )
    return tuple(bindings)


def bind_tokenizer_artifacts(
    root: str | Path,
    *,
    max_file_bytes: int = 256 * 1024 * 1024,
    max_total_bytes: int = 512 * 1024 * 1024,
) -> TokenizerBinding:
    """Hash and describe well-known local tokenizer artifacts without executing them."""

    file_bound = _positive_bound("max_file_bytes", max_file_bytes)
    total_bound = _positive_bound("max_total_bytes", max_total_bytes)
    resolved = _safe_root(root)
    artifacts: list[TokenizerArtifact] = []
    captured: dict[str, bytes | None] = {}
    total = 0
    vocabulary_sources = 0

    for name, media_type, vocabulary_source in _KNOWN_ARTIFACTS:
        candidate = resolved / name
        if not candidate.exists() and not candidate.is_symlink():
            continue
        path = _safe_file(resolved, name)
        size, digest, raw = _hash_file(path, max_file_bytes=file_bound)
        total += size
        if total > total_bound:
            raise TokenizerBindingError("tokenizer artifacts exceed total byte bound")
        artifacts.append(
            TokenizerArtifact(
                path=name,
                size=size,
                sha256=digest,
                media_type=media_type,
                vocabulary_source=vocabulary_source,
            )
        )
        captured[name] = raw
        if vocabulary_source:
            vocabulary_sources += 1

    if vocabulary_sources == 0:
        raise TokenizerBindingError("no supported tokenizer vocabulary artifact was found")

    tokenizer_config = (
        _parse_json("tokenizer_config.json", captured["tokenizer_config.json"])
        if "tokenizer_config.json" in captured
        else None
    )
    if tokenizer_config is not None and not isinstance(tokenizer_config, dict):
        raise TokenizerBindingError("tokenizer_config.json must contain a JSON object")

    special_map = (
        _parse_json("special_tokens_map.json", captured["special_tokens_map.json"])
        if "special_tokens_map.json" in captured
        else None
    )
    if special_map is not None and not isinstance(special_map, dict):
        raise TokenizerBindingError("special_tokens_map.json must contain a JSON object")

    special_tokens = _extract_special_tokens(tokenizer_config, special_map)
    chat_templates = _extract_chat_templates(
        tokenizer_config,
        captured.get("chat_template.jinja"),
    )
    artifact_tuple = tuple(artifacts)
    manifest = {
        "schema": "khipu-tokenizer-artifact-binding/v0.1",
        "status": "LOCAL_TOKENIZER_ARTIFACT_BINDING",
        "root": resolved.name,
        "artifacts": [artifact.as_dict() for artifact in artifact_tuple],
        "special_tokens": [token.as_dict() for token in special_tokens],
        "chat_templates": [template.as_dict() for template in chat_templates],
        "total_bytes": total,
        "tokenizer_execution": "NOT_PERFORMED",
        "chat_template_execution": "NOT_PERFORMED",
        "network_access": "NOT_PERFORMED",
        "hardware_status": "UNAVAILABLE",
        "energy_j": None,
        "energy_status": "UNAVAILABLE",
    }
    manifest_digest = hashlib.sha256(canonical_json_bytes(manifest)).hexdigest()
    chain = ReceiptChain()
    chain.append(
        "tokenizer_artifacts_bound",
        {**manifest, "manifest_digest": manifest_digest},
    )
    chain.require_valid()
    return TokenizerBinding(
        root=resolved.name,
        artifacts=artifact_tuple,
        special_tokens=special_tokens,
        chat_templates=chat_templates,
        total_bytes=total,
        manifest_digest=manifest_digest,
        receipt_chain=chain,
    )


def verify_tokenizer_binding(
    root: str | Path,
    expected: TokenizerBinding,
    *,
    max_file_bytes: int = 256 * 1024 * 1024,
    max_total_bytes: int = 512 * 1024 * 1024,
) -> TokenizerBinding:
    """Rebind current local bytes and fail if their manifest changed."""

    observed = bind_tokenizer_artifacts(
        root,
        max_file_bytes=max_file_bytes,
        max_total_bytes=max_total_bytes,
    )
    if observed.root != expected.root:
        raise TokenizerBindingError("tokenizer root identity changed")
    if observed.manifest_digest != expected.manifest_digest:
        raise TokenizerBindingError("tokenizer artifact manifest mismatch")
    return observed


__all__ = [
    "ChatTemplateBinding",
    "SpecialTokenBinding",
    "TokenizerArtifact",
    "TokenizerBinding",
    "TokenizerBindingError",
    "bind_tokenizer_artifacts",
    "verify_tokenizer_binding",
]
