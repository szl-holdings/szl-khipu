"""Strict local safetensors-to-decoder mapping for KHIPU-X1.

The mapper consumes a previously validated :class:`ModelWeightInventory`,
verifies the exact local shard bytes again, and materializes one dense decoder
layer into the deterministic NumPy reference layout. It never imports model
code, performs network access, or claims accelerator execution.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Literal

import numpy as np

from .kids import canonical_json_bytes
from .receipt import ReceiptChain
from .safetensors_inventory import (
    ModelWeightInventory,
    SafetensorsFileInventory,
    TensorInventory,
)
from .simulator import array_commitment
from .transformer import TransformerSpec
from .transformer_reference import DecoderBlockConfig, DecoderBlockWeights


class SafetensorsMappingError(ValueError):
    """Raised when local bytes cannot be mapped under the v0.1 contract."""


@dataclass(frozen=True)
class DecoderLayerTensorNames:
    """Exact source names required to map one dense decoder layer."""

    attention_norm: str
    q_proj: str
    k_proj: str
    v_proj: str
    o_proj: str
    ffn_norm: str
    gate_proj: str
    up_proj: str
    down_proj: str

    @classmethod
    def hf_dense(cls, layer_index: int) -> "DecoderLayerTensorNames":
        if not isinstance(layer_index, int) or isinstance(layer_index, bool) or layer_index < 0:
            raise SafetensorsMappingError("layer_index must be a non-negative integer")
        prefix = f"model.layers.{layer_index}"
        return cls(
            attention_norm=f"{prefix}.input_layernorm.weight",
            q_proj=f"{prefix}.self_attn.q_proj.weight",
            k_proj=f"{prefix}.self_attn.k_proj.weight",
            v_proj=f"{prefix}.self_attn.v_proj.weight",
            o_proj=f"{prefix}.self_attn.o_proj.weight",
            ffn_norm=f"{prefix}.post_attention_layernorm.weight",
            gate_proj=f"{prefix}.mlp.gate_proj.weight",
            up_proj=f"{prefix}.mlp.up_proj.weight",
            down_proj=f"{prefix}.mlp.down_proj.weight",
        )

    def validate(self) -> None:
        values: list[str] = []
        for field in fields(self):
            value = getattr(self, field.name)
            if not isinstance(value, str) or not value or len(value) > 1024:
                raise SafetensorsMappingError(
                    f"{field.name} must be a non-empty bounded tensor name"
                )
            values.append(value)
        if len(set(values)) != len(values):
            raise SafetensorsMappingError("decoder tensor names must be unique")

    def as_dict(self) -> dict[str, str]:
        self.validate()
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass(frozen=True)
class TensorMappingBinding:
    logical_role: str
    source_name: str
    source_file: str
    source_dtype: str
    source_shape: tuple[int, ...]
    source_byte_count: int
    source_range_sha256: str
    source_file_sha256: str
    transform: Literal["identity", "transpose_2d"]
    mapped_shape: tuple[int, ...]
    mapped_array_sha3_256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "logical_role": self.logical_role,
            "source_name": self.source_name,
            "source_file": self.source_file,
            "source_dtype": self.source_dtype,
            "source_shape": list(self.source_shape),
            "source_byte_count": self.source_byte_count,
            "source_range_sha256": self.source_range_sha256,
            "source_file_sha256": self.source_file_sha256,
            "transform": self.transform,
            "mapped_shape": list(self.mapped_shape),
            "mapped_array_sha3_256": self.mapped_array_sha3_256,
        }


@dataclass(frozen=True)
class MappedDecoderLayer:
    layer_index: int
    config: DecoderBlockConfig
    weights: DecoderBlockWeights
    bindings: tuple[TensorMappingBinding, ...]
    inventory_digest: str
    source_config_digest: str
    mapping_digest: str
    receipt_chain: ReceiptChain
    status: str = "LOCAL_STATIC_WEIGHT_MAPPING"
    hardware_status: str = "UNAVAILABLE"
    energy_j: None = None

    def report(self) -> dict[str, Any]:
        verified, first_break, reason = self.receipt_chain.verify()
        return {
            "schema": "khipu-safetensors-decoder-mapping/v0.1",
            "status": self.status,
            "layer_index": self.layer_index,
            "inventory_digest": self.inventory_digest,
            "source_config_digest": self.source_config_digest,
            "mapping_digest": self.mapping_digest,
            "content_binding": "FULL_FILE_SHA256_REVERIFIED",
            "bindings": [binding.as_dict() for binding in self.bindings],
            "receipt_head": self.receipt_chain.head,
            "receipt_verified": verified,
            "receipt_first_break": first_break,
            "receipt_reason": reason,
            "model_code_execution": "NOT_PERFORMED",
            "network_access": "NOT_PERFORMED",
            "hardware_status": self.hardware_status,
            "energy_j": self.energy_j,
            "energy_status": "UNAVAILABLE",
        }


@dataclass(frozen=True)
class _TensorLocation:
    file: SafetensorsFileInventory
    tensor: TensorInventory


class _BoundReader:
    def __init__(
        self,
        model_root: str | Path,
        inventory: ModelWeightInventory,
        *,
        max_file_bytes: int,
        max_tensor_bytes: int,
        max_total_loaded_bytes: int,
    ) -> None:
        self.root = Path(model_root)
        if self.root.is_symlink():
            raise SafetensorsMappingError("symbolic-link model root is forbidden")
        self.root = self.root.resolve(strict=True)
        if not self.root.is_dir():
            raise SafetensorsMappingError("model_root must be a local directory")
        if self.root.name != inventory.root:
            raise SafetensorsMappingError(
                "model_root basename does not match the supplied inventory"
            )
        self.inventory = inventory
        self.max_file_bytes = self._bound("max_file_bytes", max_file_bytes)
        self.max_tensor_bytes = self._bound("max_tensor_bytes", max_tensor_bytes)
        self.max_total_loaded_bytes = self._bound(
            "max_total_loaded_bytes", max_total_loaded_bytes
        )
        self.loaded_bytes = 0
        self.locations: dict[str, _TensorLocation] = {}
        self._verified_files: dict[str, tuple[int, int, int, int]] = {}
        for file in inventory.files:
            if not file.file_sha256:
                raise SafetensorsMappingError(
                    f"full-file SHA-256 is required before mapping: {file.path}"
                )
            for tensor in file.tensors:
                if tensor.name in self.locations:
                    raise SafetensorsMappingError(
                        f"tensor appears more than once in inventory: {tensor.name}"
                    )
                self.locations[tensor.name] = _TensorLocation(file=file, tensor=tensor)

    @staticmethod
    def _bound(name: str, value: int) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise SafetensorsMappingError(f"{name} must be a positive integer")
        return value

    def _path(self, display_path: str) -> Path:
        relative = Path(display_path)
        if (
            relative.is_absolute()
            or not relative.parts
            or any(part in {"", ".", ".."} for part in relative.parts)
            or "\\" in display_path
        ):
            raise SafetensorsMappingError("inventory contains an unsafe file path")
        candidate = self.root.joinpath(*relative.parts)
        if candidate.is_symlink():
            raise SafetensorsMappingError("symbolic-link weight file is forbidden")
        resolved = candidate.resolve(strict=True)
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise SafetensorsMappingError("weight file escapes model_root") from exc
        if not resolved.is_file():
            raise SafetensorsMappingError("weight path is not a regular file")
        return resolved

    @staticmethod
    def _identity(stat: os.stat_result) -> tuple[int, int, int, int]:
        return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)

    def _verify_file(self, file: SafetensorsFileInventory) -> Path:
        path = self._path(file.path)
        before = path.stat()
        if before.st_size != file.file_size:
            raise SafetensorsMappingError(f"file size changed after inventory: {file.path}")
        if before.st_size > self.max_file_bytes:
            raise SafetensorsMappingError(f"file exceeds mapping byte bound: {file.path}")
        identity = self._identity(before)
        cached = self._verified_files.get(file.path)
        if cached is not None:
            if cached != identity:
                raise SafetensorsMappingError(
                    f"file identity changed after verification: {file.path}"
                )
            return path

        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while True:
                block = handle.read(1024 * 1024)
                if not block:
                    break
                digest.update(block)
            after = os.fstat(handle.fileno())
        if self._identity(after) != identity:
            raise SafetensorsMappingError(f"file changed while hashing: {file.path}")
        if digest.hexdigest() != file.file_sha256:
            raise SafetensorsMappingError(f"file SHA-256 mismatch: {file.path}")
        self._verified_files[file.path] = identity
        return path

    @staticmethod
    def _decode(tensor: TensorInventory, raw: bytes) -> np.ndarray:
        if tensor.dtype == "F32":
            array = np.frombuffer(raw, dtype="<f4").astype(np.float32, copy=False)
        elif tensor.dtype == "F16":
            array = np.frombuffer(raw, dtype="<f2").astype(np.float32)
        elif tensor.dtype == "BF16":
            words = np.frombuffer(raw, dtype="<u2").astype(np.uint32)
            array = np.ascontiguousarray(words << 16).view(np.float32)
        else:
            raise SafetensorsMappingError(
                f"unsupported decoder weight dtype {tensor.dtype}: {tensor.name}"
            )
        try:
            shaped = array.reshape(tensor.shape)
        except ValueError as exc:
            raise SafetensorsMappingError(
                f"tensor cannot be reshaped to inventory shape: {tensor.name}"
            ) from exc
        if not np.all(np.isfinite(shaped)):
            raise SafetensorsMappingError(
                f"decoder weight contains non-finite values: {tensor.name}"
            )
        return np.ascontiguousarray(shaped, dtype=np.float32)

    def load(
        self,
        source_name: str,
        *,
        logical_role: str,
        expected_source_shape: tuple[int, ...],
        transform: Literal["identity", "transpose_2d"],
    ) -> tuple[np.ndarray, TensorMappingBinding]:
        location = self.locations.get(source_name)
        if location is None:
            raise SafetensorsMappingError(f"required tensor is missing: {source_name}")
        tensor = location.tensor
        file = location.file
        if tensor.shape != expected_source_shape:
            raise SafetensorsMappingError(
                f"{source_name} shape {tensor.shape} != expected {expected_source_shape}"
            )
        if tensor.byte_count > self.max_tensor_bytes:
            raise SafetensorsMappingError(
                f"tensor exceeds mapping byte bound: {source_name}"
            )
        if self.loaded_bytes + tensor.byte_count > self.max_total_loaded_bytes:
            raise SafetensorsMappingError("decoder mapping exceeds total byte bound")

        path = self._verify_file(file)
        expected_identity = self._verified_files[file.path]
        absolute_start = 8 + file.header_size + tensor.data_start
        with path.open("rb") as handle:
            if self._identity(os.fstat(handle.fileno())) != expected_identity:
                raise SafetensorsMappingError(
                    f"file identity changed before tensor read: {file.path}"
                )
            handle.seek(absolute_start)
            raw = handle.read(tensor.byte_count)
            after = os.fstat(handle.fileno())
        if self._identity(after) != expected_identity:
            raise SafetensorsMappingError(
                f"file changed while reading tensor: {file.path}"
            )
        if len(raw) != tensor.byte_count:
            raise SafetensorsMappingError(f"short tensor read: {source_name}")
        range_digest = hashlib.sha256(raw).hexdigest()
        if tensor.data_sha256 is not None and range_digest != tensor.data_sha256:
            raise SafetensorsMappingError(
                f"tensor range SHA-256 mismatch: {source_name}"
            )

        source_array = self._decode(tensor, raw)
        if transform == "identity":
            mapped = source_array
        elif transform == "transpose_2d":
            if source_array.ndim != 2:
                raise SafetensorsMappingError(
                    f"transpose_2d requires a matrix: {source_name}"
                )
            mapped = np.ascontiguousarray(source_array.T, dtype=np.float32)
        else:  # pragma: no cover - Literal plus explicit runtime guard
            raise SafetensorsMappingError(f"unknown mapping transform: {transform}")

        self.loaded_bytes += tensor.byte_count
        binding = TensorMappingBinding(
            logical_role=logical_role,
            source_name=source_name,
            source_file=file.path,
            source_dtype=tensor.dtype,
            source_shape=tensor.shape,
            source_byte_count=tensor.byte_count,
            source_range_sha256=range_digest,
            source_file_sha256=file.file_sha256,
            transform=transform,
            mapped_shape=tuple(int(value) for value in mapped.shape),
            mapped_array_sha3_256=array_commitment(mapped),
        )
        return mapped, binding


def _mapping_payload(
    *,
    layer_index: int,
    inventory: ModelWeightInventory,
    spec: TransformerSpec,
    attention_mode: str,
    names: DecoderLayerTensorNames,
    bindings: tuple[TensorMappingBinding, ...],
) -> dict[str, Any]:
    return {
        "schema": "khipu-safetensors-decoder-mapping/v0.1",
        "status": "LOCAL_STATIC_WEIGHT_MAPPING",
        "layer_index": layer_index,
        "attention_mode": attention_mode,
        "inventory_digest": inventory.inventory_digest,
        "source_config_digest": spec.source_config_digest,
        "source_model_type": spec.model_type,
        "source_tensor_names": names.as_dict(),
        "bindings": [binding.as_dict() for binding in bindings],
        "content_binding": "FULL_FILE_SHA256_REVERIFIED",
        "model_code_execution": "NOT_PERFORMED",
        "network_access": "NOT_PERFORMED",
        "hardware_status": "UNAVAILABLE",
        "energy_j": None,
        "energy_status": "UNAVAILABLE",
    }


def map_decoder_layer(
    model_root: str | Path,
    inventory: ModelWeightInventory,
    spec: TransformerSpec,
    layer_index: int,
    *,
    names: DecoderLayerTensorNames | None = None,
    attention_mode: Literal["causal", "yarqa"] = "causal",
    max_file_bytes: int = 8 * 1024**3,
    max_tensor_bytes: int = 1024**3,
    max_total_loaded_bytes: int = 2 * 1024**3,
) -> MappedDecoderLayer:
    """Map one explicit dense decoder layer into the NumPy reference layout."""

    if not isinstance(layer_index, int) or isinstance(layer_index, bool):
        raise SafetensorsMappingError("layer_index must be an integer")
    if not 0 <= layer_index < spec.num_hidden_layers:
        raise SafetensorsMappingError("layer_index is outside the transformer config")
    if spec.attention_bias or spec.mlp_bias:
        raise SafetensorsMappingError(
            "bias-bearing decoder mappings are not implemented in v0.1"
        )
    if spec.hidden_activation.lower() not in {"silu", "swiglu"}:
        raise SafetensorsMappingError(
            f"unsupported decoder activation in v0.1: {spec.hidden_activation}"
        )
    if attention_mode not in {"causal", "yarqa"}:
        raise SafetensorsMappingError("attention_mode must be causal or yarqa")

    tensor_names = names or DecoderLayerTensorNames.hf_dense(layer_index)
    tensor_names.validate()
    reader = _BoundReader(
        model_root,
        inventory,
        max_file_bytes=max_file_bytes,
        max_tensor_bytes=max_tensor_bytes,
        max_total_loaded_bytes=max_total_loaded_bytes,
    )

    hidden = spec.hidden_size
    query_width = spec.num_attention_heads * spec.head_dim
    kv_width = spec.num_key_value_heads * spec.head_dim
    intermediate = spec.intermediate_size
    requests = (
        ("attention_norm", tensor_names.attention_norm, (hidden,), "identity"),
        ("q_proj", tensor_names.q_proj, (query_width, hidden), "transpose_2d"),
        ("k_proj", tensor_names.k_proj, (kv_width, hidden), "transpose_2d"),
        ("v_proj", tensor_names.v_proj, (kv_width, hidden), "transpose_2d"),
        ("o_proj", tensor_names.o_proj, (hidden, query_width), "transpose_2d"),
        ("ffn_norm", tensor_names.ffn_norm, (hidden,), "identity"),
        ("gate_proj", tensor_names.gate_proj, (intermediate, hidden), "transpose_2d"),
        ("up_proj", tensor_names.up_proj, (intermediate, hidden), "transpose_2d"),
        ("down_proj", tensor_names.down_proj, (hidden, intermediate), "transpose_2d"),
    )

    arrays: dict[str, np.ndarray] = {}
    binding_list: list[TensorMappingBinding] = []
    for logical_role, source_name, source_shape, transform in requests:
        array, binding = reader.load(
            source_name,
            logical_role=logical_role,
            expected_source_shape=source_shape,
            transform=transform,  # type: ignore[arg-type]
        )
        arrays[logical_role] = array
        binding_list.append(binding)

    config = DecoderBlockConfig(
        hidden_size=spec.hidden_size,
        num_attention_heads=spec.num_attention_heads,
        num_key_value_heads=spec.num_key_value_heads,
        head_dim=spec.head_dim,
        intermediate_size=spec.intermediate_size,
        rms_norm_eps=spec.rms_norm_eps,
        rotary_theta=spec.rope_theta,
        attention_mode=attention_mode,
    )
    weights = DecoderBlockWeights(
        attention_norm=arrays["attention_norm"],
        q_proj=arrays["q_proj"],
        k_proj=arrays["k_proj"],
        v_proj=arrays["v_proj"],
        o_proj=arrays["o_proj"],
        ffn_norm=arrays["ffn_norm"],
        gate_proj=arrays["gate_proj"],
        up_proj=arrays["up_proj"],
        down_proj=arrays["down_proj"],
    )
    weights.validate(config)
    bindings = tuple(binding_list)
    payload = _mapping_payload(
        layer_index=layer_index,
        inventory=inventory,
        spec=spec,
        attention_mode=attention_mode,
        names=tensor_names,
        bindings=bindings,
    )
    mapping_digest = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    chain = ReceiptChain()
    chain.append(
        "safetensors_decoder_layer_mapped",
        {**payload, "mapping_digest": mapping_digest},
    )
    chain.require_valid()
    return MappedDecoderLayer(
        layer_index=layer_index,
        config=config,
        weights=weights,
        bindings=bindings,
        inventory_digest=inventory.inventory_digest,
        source_config_digest=spec.source_config_digest,
        mapping_digest=mapping_digest,
        receipt_chain=chain,
    )


__all__ = [
    "DecoderLayerTensorNames",
    "MappedDecoderLayer",
    "SafetensorsMappingError",
    "TensorMappingBinding",
    "map_decoder_layer",
]
