"""Internal bounded safetensors inventory types and validation helpers."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Mapping

MAX_HEADER_BYTES = 16 * 1024 * 1024
MAX_INDEX_BYTES = 16 * 1024 * 1024
MAX_TENSORS = 200_000
MAX_RANK = 16
MAX_DIMENSION = (1 << 48) - 1
MAX_PARAMETER_COUNT = (1 << 63) - 1
HASH_CHUNK_BYTES = 4 * 1024 * 1024

TENSOR_NAME = re.compile(r"^[^\x00-\x1f\x7f]{1,1024}$")
SAFE_SHARD_PART = re.compile(r"^[A-Za-z0-9._-]{1,255}$")

# Byte-aligned dtypes intentionally supported by the KHIPU v0.1 inspector.
DTYPE_BYTES: dict[str, int] = {
    "BOOL": 1,
    "U8": 1,
    "I8": 1,
    "F8_E5M2": 1,
    "F8_E4M3": 1,
    "F8_E8M0": 1,
    "F8_E4M3FNUZ": 1,
    "F8_E5M2FNUZ": 1,
    "I16": 2,
    "U16": 2,
    "F16": 2,
    "BF16": 2,
    "I32": 4,
    "U32": 4,
    "F32": 4,
    "C64": 8,
    "F64": 8,
    "I64": 8,
    "U64": 8,
}
SUBBYTE_DTYPES = {"F4", "F6_E2M3", "F6_E3M2"}


class SafetensorsInventoryError(ValueError):
    """Raised when a local artifact violates the bounded inventory contract."""


class _DuplicateKeyError(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json_unique(raw: bytes, *, label: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError, _DuplicateKeyError) as exc:
        raise SafetensorsInventoryError(
            f"{label} is not valid unique-key UTF-8 JSON: {exc}"
        ) from exc


def load_header(raw: bytes) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
        value, end = json.JSONDecoder(object_pairs_hook=_unique_object).raw_decode(text)
    except (UnicodeDecodeError, json.JSONDecodeError, _DuplicateKeyError) as exc:
        raise SafetensorsInventoryError(
            f"safetensors header is not valid unique-key UTF-8 JSON: {exc}"
        ) from exc
    if any(character != " " for character in text[end:]):
        raise SafetensorsInventoryError(
            "safetensors header padding must contain ASCII spaces only"
        )
    if not isinstance(value, dict):
        raise SafetensorsInventoryError("safetensors header root must be an object")
    return value


def sha256_stream(stream: BinaryIO, *, start: int, length: int) -> str:
    if start < 0 or length < 0:
        raise SafetensorsInventoryError("hash range is invalid")
    stream.seek(start)
    remaining = length
    digest = hashlib.sha256()
    while remaining:
        block = stream.read(min(HASH_CHUNK_BYTES, remaining))
        if not block:
            raise SafetensorsInventoryError("file ended while hashing a committed range")
        digest.update(block)
        remaining -= len(block)
    return digest.hexdigest()


def checked_product(shape: tuple[int, ...]) -> int:
    count = 1
    for dimension in shape:
        if dimension == 0:
            return 0
        if count > MAX_PARAMETER_COUNT // dimension:
            raise SafetensorsInventoryError(
                "tensor parameter count exceeds the v0.1 bound"
            )
        count *= dimension
    return count


def safe_shard_path(root: Path, relative: str) -> Path:
    if (
        not isinstance(relative, str)
        or not relative
        or "\\" in relative
        or "\x00" in relative
    ):
        raise SafetensorsInventoryError(f"unsafe shard path: {relative!r}")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(
        part in {"", ".", ".."} or not SAFE_SHARD_PART.fullmatch(part)
        for part in pure.parts
    ):
        raise SafetensorsInventoryError(f"unsafe shard path: {relative!r}")
    candidate = root
    for part in pure.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise SafetensorsInventoryError(
                f"symbolic-link shard component is forbidden: {relative}"
            )
    resolved_root = root.resolve(strict=True)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise SafetensorsInventoryError(
            f"referenced shard is unavailable: {relative}"
        ) from exc
    if resolved_root != resolved and resolved_root not in resolved.parents:
        raise SafetensorsInventoryError(f"shard escapes model root: {relative}")
    if not resolved.is_file() or resolved.suffix != ".safetensors":
        raise SafetensorsInventoryError(
            f"shard is not a .safetensors file: {relative}"
        )
    return resolved


@dataclass(frozen=True)
class TensorInventory:
    name: str
    dtype: str
    shape: tuple[int, ...]
    parameter_count: int
    data_start: int
    data_end: int
    byte_count: int
    data_sha256: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "dtype": self.dtype,
            "shape": list(self.shape),
            "parameter_count": self.parameter_count,
            "data_offsets": [self.data_start, self.data_end],
            "byte_count": self.byte_count,
            "data_sha256": self.data_sha256,
        }


@dataclass(frozen=True)
class SafetensorsFileInventory:
    path: str
    file_size: int
    header_size: int
    data_size: int
    tensor_count: int
    parameter_count: int
    parameters_by_dtype: Mapping[str, int]
    bytes_by_dtype: Mapping[str, int]
    metadata: Mapping[str, str]
    file_sha256: str | None
    tensors: tuple[TensorInventory, ...]

    @property
    def content_binding_status(self) -> str:
        if self.file_sha256 is not None:
            return "FULL_FILE_SHA256"
        if all(tensor.data_sha256 is not None for tensor in self.tensors):
            return "TENSOR_RANGE_SHA256"
        return "HEADER_AND_LAYOUT_ONLY"

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "khipu-safetensors-file-inventory/v0.1",
            "path": self.path,
            "file_size": self.file_size,
            "header_size": self.header_size,
            "data_size": self.data_size,
            "tensor_count": self.tensor_count,
            "parameter_count": self.parameter_count,
            "parameters_by_dtype": dict(sorted(self.parameters_by_dtype.items())),
            "bytes_by_dtype": dict(sorted(self.bytes_by_dtype.items())),
            "metadata": dict(sorted(self.metadata.items())),
            "file_sha256": self.file_sha256,
            "content_binding_status": self.content_binding_status,
            "tensors": [tensor.as_dict() for tensor in self.tensors],
            "inspection": "LOCAL_NON_EXECUTING_BYTE_VALIDATION",
            "hardware_status": "UNAVAILABLE",
        }


@dataclass(frozen=True)
class ModelWeightInventory:
    root: str
    sharded: bool
    index_path: str | None
    shard_count: int
    tensor_count: int
    parameter_count: int
    data_bytes: int
    file_bytes: int
    parameters_by_dtype: Mapping[str, int]
    bytes_by_dtype: Mapping[str, int]
    files: tuple[SafetensorsFileInventory, ...]
    weight_map_digest: str | None
    inventory_digest: str

    @property
    def content_binding_status(self) -> str:
        if all(file.file_sha256 is not None for file in self.files):
            return "FULL_FILE_SHA256"
        if all(
            tensor.data_sha256 is not None
            for file in self.files
            for tensor in file.tensors
        ):
            return "TENSOR_RANGE_SHA256"
        return "HEADER_AND_LAYOUT_ONLY"

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "khipu-model-weight-inventory/v0.1",
            "root": self.root,
            "sharded": self.sharded,
            "index_path": self.index_path,
            "shard_count": self.shard_count,
            "tensor_count": self.tensor_count,
            "parameter_count": self.parameter_count,
            "data_bytes": self.data_bytes,
            "file_bytes": self.file_bytes,
            "parameters_by_dtype": dict(sorted(self.parameters_by_dtype.items())),
            "bytes_by_dtype": dict(sorted(self.bytes_by_dtype.items())),
            "files": [file.as_dict() for file in self.files],
            "weight_map_digest": self.weight_map_digest,
            "inventory_digest": self.inventory_digest,
            "content_binding_status": self.content_binding_status,
            "inspection": "LOCAL_NON_EXECUTING_BYTE_VALIDATION",
            "parameter_count_status": "EXACT_FROM_VALIDATED_HEADER_SHAPES",
            "model_quality_status": "NOT_EVALUATED",
            "license_status": "NOT_EVALUATED",
            "hardware_status": "UNAVAILABLE",
        }
