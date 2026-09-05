"""Safe deterministic ``.khipu`` package builder and verifier.

A KHIPU package is a bounded ZIP container. Verification never extracts files;
it validates names, entry types, sizes, canonical manifest bytes and exact
SHA-256 commitments in memory.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from .graph import GraphPlan, GraphValidationError, lower_graph
from .kids import Opcode, canonical_json_bytes

FORMAT_VERSION = "0.1"
MANIFEST_PATH = "manifest.json"
MAX_ENTRIES = 128
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
_MAX_COMPRESSION_RATIO = 100
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_PACKAGE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_SAFE_PATH = re.compile(r"^[A-Za-z0-9._/-]+$")


class KhipuPackageError(ValueError):
    """Raised when a package cannot be built or verified safely."""


@dataclass(frozen=True)
class PackageReport:
    package_id: str
    package_digest: str
    model_digest: str
    policy_digest: str
    graph_digest: str
    required_ops: tuple[str, ...]
    files_verified: int
    total_bytes: int
    verified: bool = True
    execution_status: str = "PACKAGE_VERIFIED_ONLY"

    def as_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "package_digest": self.package_digest,
            "model_digest": self.model_digest,
            "policy_digest": self.policy_digest,
            "graph_digest": self.graph_digest,
            "required_ops": list(self.required_ops),
            "files_verified": self.files_verified,
            "total_bytes": self.total_bytes,
            "verified": self.verified,
            "execution_status": self.execution_status,
        }


def _safe_archive_path(name: str) -> str:
    if not isinstance(name, str) or not name or len(name) > 240:
        raise KhipuPackageError("archive path must be 1..240 characters")
    if "\\" in name or "\x00" in name or not _SAFE_PATH.fullmatch(name):
        raise KhipuPackageError(f"unsafe archive path: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise KhipuPackageError(f"unsafe archive path: {name!r}")
    normalized = path.as_posix()
    if normalized != name:
        raise KhipuPackageError(f"non-canonical archive path: {name!r}")
    return normalized


def _canonical_manifest_bytes(manifest: Mapping[str, Any]) -> bytes:
    return canonical_json_bytes(dict(manifest)) + b"\n"


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_package(
    destination: str | Path,
    *,
    package_id: str,
    model_digest: str,
    policy_digest: str,
    graph: Mapping[str, Any] | GraphPlan,
    payloads: Mapping[str, bytes] | None = None,
    required_ops: Sequence[Opcode | str] = (),
    roles: Mapping[str, str] | None = None,
) -> PackageReport:
    """Build a deterministic reference package and verify it before return."""

    if not _PACKAGE_ID.fullmatch(package_id):
        raise KhipuPackageError("invalid package_id")
    if not _HEX64.fullmatch(model_digest) or not _HEX64.fullmatch(policy_digest):
        raise KhipuPackageError("model_digest and policy_digest must be lowercase SHA-256")

    plan = graph if isinstance(graph, GraphPlan) else GraphPlan.from_dict(graph)
    graph_bytes = canonical_json_bytes(plan.as_dict()) + b"\n"
    entries: dict[str, bytes] = {"graphs/model.json": graph_bytes}
    for raw_name, raw_data in (payloads or {}).items():
        name = _safe_archive_path(raw_name)
        if name == MANIFEST_PATH or name in entries:
            raise KhipuPackageError(f"duplicate or reserved payload path: {name}")
        if not isinstance(raw_data, bytes):
            raise KhipuPackageError(f"payload {name} must be bytes")
        entries[name] = raw_data

    if len(entries) + 1 > MAX_ENTRIES:
        raise KhipuPackageError("package contains too many entries")
    total = sum(len(data) for data in entries.values())
    if any(len(data) > MAX_FILE_BYTES for data in entries.values()) or total > MAX_TOTAL_BYTES:
        raise KhipuPackageError("package exceeds reference size limits")

    graph_ops = sorted({node.opcode.value for node in plan.nodes})
    op_names: list[str] = []
    for raw in required_ops:
        try:
            op_names.append((raw if isinstance(raw, Opcode) else Opcode(str(raw))).value)
        except ValueError as exc:
            raise KhipuPackageError(f"unknown required opcode: {raw}") from exc
    op_names = sorted(set(op_names)) if op_names else graph_ops
    if op_names != graph_ops:
        raise KhipuPackageError("required_ops must exactly match graph operations")

    role_map = {_safe_archive_path(name): role for name, role in dict(roles or {}).items()}
    unknown_role_paths = set(role_map) - set(entries)
    if unknown_role_paths:
        raise KhipuPackageError(f"roles reference unknown payloads: {sorted(unknown_role_paths)}")
    manifest_files = []
    for name, data in sorted(entries.items()):
        role = "graph" if name == "graphs/model.json" else role_map.get(name, "artifact")
        if role not in {"graph", "weights", "tokenizer", "config", "artifact", "license"}:
            raise KhipuPackageError(f"unsupported role {role!r} for {name}")
        manifest_files.append({"path": name, "sha256": _sha256(data), "size": len(data), "role": role})

    manifest = {
        "format": "khipu-package",
        "format_version": FORMAT_VERSION,
        "package_id": package_id,
        "kids_version": "0.1",
        "model_digest": model_digest,
        "policy_digest": policy_digest,
        "entry_graph": "graphs/model.json",
        "graph_digest": plan.digest,
        "required_ops": op_names,
        "hardware_execution": "UNAVAILABLE",
        "production_eligible": False,
        "files": manifest_files,
    }
    manifest_bytes = _canonical_manifest_bytes(manifest)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr(_zip_info(MANIFEST_PATH), manifest_bytes, compresslevel=9)
        for name, data in sorted(entries.items()):
            archive.writestr(_zip_info(name), data, compresslevel=9)

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(buffer.getvalue())
    return verify_package(destination)


def _read_package_bytes(source: str | Path | bytes) -> bytes:
    if isinstance(source, bytes):
        return source
    path = Path(source)
    if path.suffix != ".khipu":
        raise KhipuPackageError("package file must use the .khipu suffix")
    size = path.stat().st_size
    if size > MAX_TOTAL_BYTES:
        raise KhipuPackageError("package archive exceeds the reference size limit")
    return path.read_bytes()


def verify_package(source: str | Path | bytes) -> PackageReport:
    raw = _read_package_bytes(source)
    package_digest = _sha256(raw)
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw), "r")
    except zipfile.BadZipFile as exc:
        raise KhipuPackageError("invalid ZIP container") from exc

    with archive:
        infos = archive.infolist()
        if not infos or len(infos) > MAX_ENTRIES:
            raise KhipuPackageError("invalid package entry count")
        names = [info.filename for info in infos]
        if len(names) != len(set(names)) or len(names) != len({name.casefold() for name in names}):
            raise KhipuPackageError("duplicate or case-colliding archive entries")
        for info in infos:
            _safe_archive_path(info.filename)
            mode = (info.external_attr >> 16) & 0o170000
            if mode == stat.S_IFLNK:
                raise KhipuPackageError(f"symbolic link entry forbidden: {info.filename}")
            if info.is_dir():
                raise KhipuPackageError(f"directory entries forbidden: {info.filename}")
            if info.flag_bits & 0x1:
                raise KhipuPackageError(f"encrypted entry forbidden: {info.filename}")
            if info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
                raise KhipuPackageError(f"unsupported compression type: {info.filename}")
            if info.file_size > MAX_FILE_BYTES:
                raise KhipuPackageError(f"entry too large: {info.filename}")
            if (
                info.file_size > 1024 * 1024
                and info.compress_size > 0
                and info.file_size / info.compress_size > _MAX_COMPRESSION_RATIO
            ):
                raise KhipuPackageError(f"suspicious compression ratio: {info.filename}")
        if sum(info.file_size for info in infos) > MAX_TOTAL_BYTES:
            raise KhipuPackageError("uncompressed package exceeds the reference size limit")
        if MANIFEST_PATH not in names:
            raise KhipuPackageError("manifest.json is missing")

        manifest_raw = archive.read(MANIFEST_PATH)
        try:
            manifest = json.loads(manifest_raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise KhipuPackageError("manifest is not valid UTF-8 JSON") from exc
        if not isinstance(manifest, dict) or manifest_raw != _canonical_manifest_bytes(manifest):
            raise KhipuPackageError("manifest is not canonical")
        if manifest.get("format") != "khipu-package" or manifest.get("format_version") != FORMAT_VERSION:
            raise KhipuPackageError("unsupported package format")
        package_id = manifest.get("package_id")
        if not isinstance(package_id, str) or not _PACKAGE_ID.fullmatch(package_id):
            raise KhipuPackageError("invalid manifest package_id")
        model_digest = manifest.get("model_digest")
        policy_digest = manifest.get("policy_digest")
        graph_digest = manifest.get("graph_digest")
        if not all(isinstance(item, str) and _HEX64.fullmatch(item) for item in (model_digest, policy_digest, graph_digest)):
            raise KhipuPackageError("manifest digest fields are invalid")
        if manifest.get("kids_version") != "0.1":
            raise KhipuPackageError("unsupported KIDS version")
        if manifest.get("hardware_execution") != "UNAVAILABLE" or manifest.get("production_eligible") is not False:
            raise KhipuPackageError("reference package truth labels were altered")

        required_raw = manifest.get("required_ops")
        if not isinstance(required_raw, list) or required_raw != sorted(set(required_raw)):
            raise KhipuPackageError("required_ops must be a sorted unique list")
        required_ops: list[str] = []
        for value in required_raw:
            try:
                required_ops.append(Opcode(str(value)).value)
            except ValueError as exc:
                raise KhipuPackageError(f"unknown required opcode: {value}") from exc

        declared = manifest.get("files")
        if not isinstance(declared, list) or not declared:
            raise KhipuPackageError("manifest files list is missing")
        by_path: dict[str, Mapping[str, Any]] = {}
        for item in declared:
            if not isinstance(item, dict):
                raise KhipuPackageError("invalid manifest file entry")
            path = _safe_archive_path(item.get("path"))
            if path == MANIFEST_PATH or path in by_path or path.casefold() in {p.casefold() for p in by_path}:
                raise KhipuPackageError(f"duplicate manifest path: {path}")
            if not isinstance(item.get("sha256"), str) or not _HEX64.fullmatch(item["sha256"]):
                raise KhipuPackageError(f"invalid file digest: {path}")
            if not isinstance(item.get("size"), int) or item["size"] < 0:
                raise KhipuPackageError(f"invalid file size: {path}")
            if item.get("role") not in {"graph", "weights", "tokenizer", "config", "artifact", "license"}:
                raise KhipuPackageError(f"invalid file role: {path}")
            by_path[path] = item

        expected_names = {MANIFEST_PATH, *by_path.keys()}
        if set(names) != expected_names:
            raise KhipuPackageError("archive and manifest file sets differ")

        total_bytes = 0
        for path, item in by_path.items():
            data = archive.read(path)
            total_bytes += len(data)
            if len(data) != item["size"] or _sha256(data) != item["sha256"]:
                raise KhipuPackageError(f"file commitment mismatch: {path}")

        entry_graph = manifest.get("entry_graph")
        if entry_graph not in by_path or by_path[entry_graph].get("role") != "graph":
            raise KhipuPackageError("entry_graph is not declared with graph role")
        graph_raw = archive.read(entry_graph)
        try:
            graph_dict = json.loads(graph_raw.decode("utf-8"))
            graph_plan = GraphPlan.from_dict(graph_dict)
            lowered = lower_graph(
                graph_plan, model_digest=model_digest, policy_digest=policy_digest
            )
        except (UnicodeDecodeError, json.JSONDecodeError, GraphValidationError) as exc:
            raise KhipuPackageError(f"entry graph is invalid: {exc}") from exc
        if graph_raw != canonical_json_bytes(graph_plan.as_dict()) + b"\n":
            raise KhipuPackageError("entry graph is not canonical")
        if graph_plan.digest != graph_digest or lowered.graph_digest != graph_digest:
            raise KhipuPackageError("entry graph digest mismatch")
        graph_ops = sorted({descriptor.opcode.value for descriptor in lowered.descriptors})
        if required_ops != graph_ops:
            raise KhipuPackageError("required_ops do not match the entry graph")

    return PackageReport(
        package_id=package_id,
        package_digest=package_digest,
        model_digest=model_digest,
        policy_digest=policy_digest,
        graph_digest=graph_digest,
        required_ops=tuple(required_ops),
        files_verified=len(by_path),
        total_bytes=total_bytes,
    )
