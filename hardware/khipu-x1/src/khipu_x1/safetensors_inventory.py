"""Bounded, non-executing safetensors inventory for KHIPU-X1.

The parser follows the public container layout but supports only byte-aligned
dtypes. It never imports model code, constructs framework tensors, or executes
weights.
"""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path
from typing import Any, Iterable

from ._safetensors_common import (
    DTYPE_BYTES,
    MAX_DIMENSION,
    MAX_HEADER_BYTES,
    MAX_INDEX_BYTES,
    MAX_RANK,
    MAX_TENSORS,
    SUBBYTE_DTYPES,
    TENSOR_NAME,
    ModelWeightInventory,
    SafetensorsFileInventory,
    SafetensorsInventoryError,
    TensorInventory,
    checked_product,
    load_header,
    load_json_unique,
    safe_shard_path,
    sha256_stream,
)
from .kids import canonical_json_bytes
from .transformer import TransformerSpec


def inventory_safetensors_file(
    path: str | Path,
    *,
    hash_file: bool = True,
    hash_tensors: bool = False,
    display_path: str | None = None,
) -> SafetensorsFileInventory:
    """Validate one local file without loading or executing tensor values."""

    supplied = Path(path)
    if supplied.is_symlink():
        raise SafetensorsInventoryError(
            "symbolic-link safetensors inputs are forbidden"
        )
    file_path = supplied.resolve(strict=True)
    if not file_path.is_file() or file_path.suffix != ".safetensors":
        raise SafetensorsInventoryError("input must be a local .safetensors file")
    file_size = file_path.stat().st_size
    if file_size < 10:
        raise SafetensorsInventoryError("safetensors file is too short")

    with file_path.open("rb") as stream:
        prefix = stream.read(8)
        if len(prefix) != 8:
            raise SafetensorsInventoryError(
                "cannot read safetensors header length"
            )
        header_size = struct.unpack("<Q", prefix)[0]
        if not 2 <= header_size <= MAX_HEADER_BYTES:
            raise SafetensorsInventoryError(
                f"header size must be in [2, {MAX_HEADER_BYTES}]"
            )
        data_base = 8 + header_size
        if data_base > file_size:
            raise SafetensorsInventoryError("declared header exceeds the file size")
        header_raw = stream.read(header_size)
        if len(header_raw) != header_size or not header_raw.startswith(b"{"):
            raise SafetensorsInventoryError(
                "header must start with a JSON object"
            )
        header = load_header(header_raw)

        metadata_raw = header.pop("__metadata__", {})
        if not isinstance(metadata_raw, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in metadata_raw.items()
        ):
            raise SafetensorsInventoryError(
                "__metadata__ must be string-to-string"
            )
        if not header or len(header) > MAX_TENSORS:
            raise SafetensorsInventoryError(
                "tensor count is empty or exceeds the v0.1 bound"
            )

        provisional: list[
            tuple[str, str, tuple[int, ...], int, int, int]
        ] = []
        for name, info in header.items():
            if not isinstance(name, str) or not TENSOR_NAME.fullmatch(name):
                raise SafetensorsInventoryError(
                    "tensor name is empty, oversized or contains controls"
                )
            if (
                not isinstance(info, dict)
                or set(info) != {"dtype", "shape", "data_offsets"}
            ):
                raise SafetensorsInventoryError(
                    f"tensor {name} has an invalid descriptor"
                )
            dtype = info.get("dtype")
            if dtype in SUBBYTE_DTYPES:
                raise SafetensorsInventoryError(
                    f"tensor {name} uses unsupported sub-byte dtype {dtype}"
                )
            if not isinstance(dtype, str) or dtype not in DTYPE_BYTES:
                raise SafetensorsInventoryError(
                    f"tensor {name} uses unsupported dtype {dtype!r}"
                )
            shape_raw = info.get("shape")
            if not isinstance(shape_raw, list) or len(shape_raw) > MAX_RANK:
                raise SafetensorsInventoryError(
                    f"tensor {name} has an invalid rank"
                )
            shape: list[int] = []
            for dimension in shape_raw:
                if (
                    not isinstance(dimension, int)
                    or isinstance(dimension, bool)
                    or not 0 <= dimension <= MAX_DIMENSION
                ):
                    raise SafetensorsInventoryError(
                        f"tensor {name} has an invalid dimension"
                    )
                shape.append(dimension)
            shape_tuple = tuple(shape)
            parameters = checked_product(shape_tuple)
            offsets = info.get("data_offsets")
            if (
                not isinstance(offsets, list)
                or len(offsets) != 2
                or any(
                    not isinstance(value, int)
                    or isinstance(value, bool)
                    or value < 0
                    for value in offsets
                )
            ):
                raise SafetensorsInventoryError(
                    f"tensor {name} has invalid data_offsets"
                )
            start, end = offsets
            if end < start:
                raise SafetensorsInventoryError(
                    f"tensor {name} has reversed data_offsets"
                )
            byte_count = end - start
            if byte_count != parameters * DTYPE_BYTES[dtype]:
                raise SafetensorsInventoryError(
                    f"tensor {name} byte count does not match dtype and shape"
                )
            provisional.append(
                (name, dtype, shape_tuple, parameters, start, end)
            )

        data_size = file_size - data_base
        cursor = 0
        for name, _dtype, _shape, _parameters, start, end in sorted(
            provisional,
            key=lambda item: (item[4], item[5], item[0]),
        ):
            if start != cursor:
                relation = "overlap" if start < cursor else "hole"
                raise SafetensorsInventoryError(
                    f"tensor buffer contains an {relation} before {name}"
                )
            if end > data_size:
                raise SafetensorsInventoryError(
                    f"tensor {name} exceeds the file data buffer"
                )
            cursor = end
        if cursor != data_size:
            raise SafetensorsInventoryError(
                "tensor offsets do not index the complete data buffer"
            )

        tensors: list[TensorInventory] = []
        parameters_by_dtype: dict[str, int] = {}
        bytes_by_dtype: dict[str, int] = {}
        for name, dtype, shape, parameters, start, end in sorted(
            provisional,
            key=lambda item: item[0],
        ):
            byte_count = end - start
            data_digest = (
                sha256_stream(
                    stream,
                    start=data_base + start,
                    length=byte_count,
                )
                if hash_tensors
                else None
            )
            tensors.append(
                TensorInventory(
                    name=name,
                    dtype=dtype,
                    shape=shape,
                    parameter_count=parameters,
                    data_start=start,
                    data_end=end,
                    byte_count=byte_count,
                    data_sha256=data_digest,
                )
            )
            parameters_by_dtype[dtype] = (
                parameters_by_dtype.get(dtype, 0) + parameters
            )
            bytes_by_dtype[dtype] = bytes_by_dtype.get(dtype, 0) + byte_count

        file_digest = (
            sha256_stream(stream, start=0, length=file_size)
            if hash_file
            else None
        )

    return SafetensorsFileInventory(
        path=display_path or file_path.name,
        file_size=file_size,
        header_size=header_size,
        data_size=data_size,
        tensor_count=len(tensors),
        parameter_count=sum(tensor.parameter_count for tensor in tensors),
        parameters_by_dtype=parameters_by_dtype,
        bytes_by_dtype=bytes_by_dtype,
        metadata=dict(metadata_raw),
        file_sha256=file_digest,
        tensors=tuple(tensors),
    )


def _digest_payload(
    *,
    root: str,
    sharded: bool,
    index_path: str | None,
    files: Iterable[SafetensorsFileInventory],
    weight_map_digest: str | None,
) -> dict[str, Any]:
    return {
        "schema": "khipu-model-weight-inventory-digest/v0.1",
        "root": root,
        "sharded": sharded,
        "index_path": index_path,
        "weight_map_digest": weight_map_digest,
        "files": [file.as_dict() for file in files],
    }


def _combine(
    *,
    root: Path,
    sharded: bool,
    index_path: str | None,
    files: tuple[SafetensorsFileInventory, ...],
    weight_map_digest: str | None,
) -> ModelWeightInventory:
    parameters_by_dtype: dict[str, int] = {}
    bytes_by_dtype: dict[str, int] = {}
    tensor_names: set[str] = set()
    for file in files:
        for tensor in file.tensors:
            if tensor.name in tensor_names:
                raise SafetensorsInventoryError(
                    f"tensor appears in multiple shards: {tensor.name}"
                )
            tensor_names.add(tensor.name)
        for dtype, count in file.parameters_by_dtype.items():
            parameters_by_dtype[dtype] = (
                parameters_by_dtype.get(dtype, 0) + count
            )
        for dtype, count in file.bytes_by_dtype.items():
            bytes_by_dtype[dtype] = bytes_by_dtype.get(dtype, 0) + count

    payload = _digest_payload(
        root=root.name,
        sharded=sharded,
        index_path=index_path,
        files=files,
        weight_map_digest=weight_map_digest,
    )
    return ModelWeightInventory(
        root=root.name,
        sharded=sharded,
        index_path=index_path,
        shard_count=len(files),
        tensor_count=sum(file.tensor_count for file in files),
        parameter_count=sum(file.parameter_count for file in files),
        data_bytes=sum(file.data_size for file in files),
        file_bytes=sum(file.file_size for file in files),
        parameters_by_dtype=parameters_by_dtype,
        bytes_by_dtype=bytes_by_dtype,
        files=files,
        weight_map_digest=weight_map_digest,
        inventory_digest=hashlib.sha256(
            canonical_json_bytes(payload)
        ).hexdigest(),
    )


def inventory_sharded_model(
    index_path: str | Path,
    *,
    hash_files: bool = True,
    hash_tensors: bool = False,
) -> ModelWeightInventory:
    """Validate an index and all referenced local shards without execution."""

    supplied = Path(index_path)
    if supplied.is_symlink():
        raise SafetensorsInventoryError("symbolic-link index is forbidden")
    index = supplied.resolve(strict=True)
    if not index.is_file() or index.suffix != ".json":
        raise SafetensorsInventoryError("index must be a local JSON file")
    if index.stat().st_size > MAX_INDEX_BYTES:
        raise SafetensorsInventoryError("index exceeds the v0.1 size bound")
    parsed = load_json_unique(index.read_bytes(), label="safetensors index")
    if not isinstance(parsed, dict) or set(parsed) - {"metadata", "weight_map"}:
        raise SafetensorsInventoryError(
            "index root contains unsupported fields"
        )
    metadata = parsed.get("metadata", {})
    weight_map = parsed.get("weight_map")
    if (
        not isinstance(metadata, dict)
        or not isinstance(weight_map, dict)
        or not weight_map
    ):
        raise SafetensorsInventoryError(
            "index requires metadata object and non-empty weight_map"
        )
    if len(weight_map) > MAX_TENSORS:
        raise SafetensorsInventoryError(
            "weight_map exceeds the v0.1 tensor bound"
        )

    root = index.parent
    normalized: dict[str, str] = {}
    for tensor_name, shard_name in weight_map.items():
        if (
            not isinstance(tensor_name, str)
            or not TENSOR_NAME.fullmatch(tensor_name)
        ):
            raise SafetensorsInventoryError(
                "weight_map has an invalid tensor name"
            )
        if not isinstance(shard_name, str):
            raise SafetensorsInventoryError(
                f"weight_map shard for {tensor_name} is invalid"
            )
        safe_shard_path(root, shard_name)
        normalized[tensor_name] = shard_name

    files = tuple(
        inventory_safetensors_file(
            safe_shard_path(root, shard_name),
            hash_file=hash_files,
            hash_tensors=hash_tensors,
            display_path=shard_name,
        )
        for shard_name in sorted(set(normalized.values()))
    )
    actual_pairs = {
        (tensor.name, file.path)
        for file in files
        for tensor in file.tensors
    }
    expected_pairs = set(normalized.items())
    if actual_pairs != expected_pairs:
        missing = sorted(expected_pairs - actual_pairs)[:10]
        extra = sorted(actual_pairs - expected_pairs)[:10]
        raise SafetensorsInventoryError(
            f"index/shard tensor map mismatch; missing={missing}, extra={extra}"
        )

    declared_total = metadata.get("total_size")
    data_total = sum(file.data_size for file in files)
    if declared_total is not None and (
        not isinstance(declared_total, int)
        or isinstance(declared_total, bool)
        or declared_total != data_total
    ):
        raise SafetensorsInventoryError(
            "index metadata.total_size does not match validated tensor data bytes"
        )

    weight_map_digest = hashlib.sha256(
        canonical_json_bytes(dict(sorted(normalized.items())))
    ).hexdigest()
    return _combine(
        root=root,
        sharded=True,
        index_path=index.name,
        files=files,
        weight_map_digest=weight_map_digest,
    )


def inventory_local_model(
    model_root: str | Path,
    *,
    hash_files: bool = True,
    hash_tensors: bool = False,
) -> ModelWeightInventory:
    """Inventory canonical single-file or indexed local model weights."""

    root = Path(model_root).resolve(strict=True)
    if not root.is_dir():
        raise SafetensorsInventoryError(
            "model_root must be a local directory"
        )
    index = root / "model.safetensors.index.json"
    single = root / "model.safetensors"
    if index.exists() and single.exists():
        raise SafetensorsInventoryError(
            "model root is ambiguous: canonical single and sharded entry points coexist"
        )
    if index.exists():
        return inventory_sharded_model(
            index,
            hash_files=hash_files,
            hash_tensors=hash_tensors,
        )
    if not single.exists():
        raise SafetensorsInventoryError(
            "model root has neither model.safetensors nor "
            "model.safetensors.index.json"
        )
    file = inventory_safetensors_file(
        single,
        hash_file=hash_files,
        hash_tensors=hash_tensors,
        display_path=single.name,
    )
    return _combine(
        root=root,
        sharded=False,
        index_path=None,
        files=(file,),
        weight_map_digest=None,
    )


def compare_inventory_to_spec(
    inventory: ModelWeightInventory,
    spec: TransformerSpec,
) -> dict[str, Any]:
    """Compare exact header count with the independent analytic estimate."""

    estimate = spec.parameter_estimate
    exact = inventory.parameter_count
    delta = exact - estimate
    payload = {
        "schema": "khipu-inventory-spec-comparison/v0.1",
        "inventory_digest": inventory.inventory_digest,
        "source_config_digest": spec.source_config_digest,
        "exact_header_parameter_count": exact,
        "analytic_parameter_estimate": estimate,
        "delta": delta,
        "ratio": exact / estimate if estimate else None,
        "status": (
            "OBSERVED_COUNTS_DIFFER"
            if delta
            else "COUNTS_EQUAL_NOT_EQUIVALENCE"
        ),
        "interpretation": (
            "Equality does not prove architecture compatibility; difference may "
            "reflect biases, tied/shared tensors, adapters, quantization metadata "
            "or another architecture."
        ),
        "model_execution": "NOT_PERFORMED",
        "hardware_status": "UNAVAILABLE",
    }
    return {
        **payload,
        "comparison_digest": hashlib.sha256(
            canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = [
    "ModelWeightInventory",
    "SafetensorsFileInventory",
    "SafetensorsInventoryError",
    "TensorInventory",
    "compare_inventory_to_spec",
    "inventory_local_model",
    "inventory_safetensors_file",
    "inventory_sharded_model",
]
