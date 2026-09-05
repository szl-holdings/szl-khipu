"""Strict complete causal-LM mapping from verified local safetensors bytes.

This module composes the Wave 7 bounded reader with the Wave 8 complete NumPy
reference. It maps a caller-declared dense decoder model only; it never imports
model code or infers an architecture from arbitrary tensor names.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np

from .causal_lm_reference import (
    CausalLMReferenceError,
    CausalLMWeights,
)
from .kids import canonical_json_bytes
from .receipt import ReceiptChain
from .safetensors_inventory import ModelWeightInventory
from .safetensors_mapping import (
    DecoderLayerTensorNames,
    SafetensorsMappingError,
    TensorMappingBinding,
    _BoundReader,
)
from .simulator import array_commitment
from .transformer import TransformerSpec
from .transformer_reference import DecoderBlockConfig, DecoderBlockWeights


class CausalLMMappingError(SafetensorsMappingError):
    """Raised when a complete configured model cannot be mapped safely."""


@dataclass(frozen=True)
class CausalLMTensorNames:
    """Exact global tensor names plus the bounded dense-layer profile."""

    embedding: str = "model.embed_tokens.weight"
    final_norm: str = "model.norm.weight"
    lm_head: str = "lm_head.weight"

    def validate(self) -> None:
        values = (self.embedding, self.final_norm, self.lm_head)
        if any(
            not isinstance(value, str) or not value or len(value) > 1024
            for value in values
        ):
            raise CausalLMMappingError(
                "global tensor names must be non-empty bounded strings"
            )
        if self.embedding == self.final_norm:
            raise CausalLMMappingError(
                "embedding and final norm names must differ"
            )

    def layer(self, layer_index: int) -> DecoderLayerTensorNames:
        return DecoderLayerTensorNames.hf_dense(layer_index)

    def as_dict(self) -> dict[str, str]:
        self.validate()
        return {
            "embedding": self.embedding,
            "final_norm": self.final_norm,
            "lm_head": self.lm_head,
        }


@dataclass(frozen=True)
class MappedCausalLM:
    weights: CausalLMWeights
    bindings: tuple[TensorMappingBinding, ...]
    inventory_digest: str
    source_config_digest: str
    mapping_digest: str
    receipt_chain: ReceiptChain
    status: str = "LOCAL_STATIC_FULL_MODEL_MAPPING"
    hardware_status: str = "UNAVAILABLE"
    energy_j: None = None

    def report(self) -> dict[str, Any]:
        verified, first_break, reason = self.receipt_chain.verify()
        return {
            "schema": "khipu-safetensors-causal-lm-mapping/v0.1",
            "status": self.status,
            "inventory_digest": self.inventory_digest,
            "source_config_digest": self.source_config_digest,
            "mapping_digest": self.mapping_digest,
            "layer_count": len(self.weights.layers),
            "tie_word_embeddings": self.weights.tie_word_embeddings,
            "weights_manifest_digest": self.weights.manifest_digest(),
            "content_binding": "FULL_FILE_SHA256_REVERIFIED",
            "bindings": [binding.as_dict() for binding in self.bindings],
            "receipt_head": self.receipt_chain.head,
            "receipt_verified": verified,
            "receipt_first_break": first_break,
            "receipt_reason": reason,
            "model_code_execution": "NOT_PERFORMED",
            "network_access": "NOT_PERFORMED",
            "tokenizer_status": "UNAVAILABLE",
            "hardware_status": self.hardware_status,
            "energy_j": self.energy_j,
            "energy_status": "UNAVAILABLE",
        }


def _map_layer(
    reader: _BoundReader,
    spec: TransformerSpec,
    layer_index: int,
    *,
    attention_mode: Literal["causal", "yarqa"],
    names: DecoderLayerTensorNames,
) -> tuple[DecoderBlockWeights, tuple[TensorMappingBinding, ...]]:
    names.validate()
    hidden = spec.hidden_size
    query_width = spec.num_attention_heads * spec.head_dim
    kv_width = spec.num_key_value_heads * spec.head_dim
    intermediate = spec.intermediate_size
    requests = (
        ("attention_norm", names.attention_norm, (hidden,), "identity"),
        ("q_proj", names.q_proj, (query_width, hidden), "transpose_2d"),
        ("k_proj", names.k_proj, (kv_width, hidden), "transpose_2d"),
        ("v_proj", names.v_proj, (kv_width, hidden), "transpose_2d"),
        ("o_proj", names.o_proj, (hidden, query_width), "transpose_2d"),
        ("ffn_norm", names.ffn_norm, (hidden,), "identity"),
        (
            "gate_proj",
            names.gate_proj,
            (intermediate, hidden),
            "transpose_2d",
        ),
        ("up_proj", names.up_proj, (intermediate, hidden), "transpose_2d"),
        (
            "down_proj",
            names.down_proj,
            (hidden, intermediate),
            "transpose_2d",
        ),
    )
    arrays: dict[str, np.ndarray] = {}
    bindings: list[TensorMappingBinding] = []
    for role, source_name, shape, transform in requests:
        array, binding = reader.load(
            source_name,
            logical_role=f"layer.{layer_index}.{role}",
            expected_source_shape=shape,
            transform=transform,  # type: ignore[arg-type]
        )
        arrays[role] = array
        bindings.append(binding)
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
    return weights, tuple(bindings)


def _map_complete_model(
    model_root: str | Path,
    inventory: ModelWeightInventory,
    spec: TransformerSpec,
    *,
    tensor_names: CausalLMTensorNames,
    attention_mode: Literal["causal", "yarqa"],
    max_file_bytes: int,
    max_tensor_bytes: int,
    max_total_loaded_bytes: int,
) -> tuple[CausalLMWeights, tuple[TensorMappingBinding, ...]]:
    reader = _BoundReader(
        model_root,
        inventory,
        max_file_bytes=max_file_bytes,
        max_tensor_bytes=max_tensor_bytes,
        max_total_loaded_bytes=max_total_loaded_bytes,
    )
    bindings: list[TensorMappingBinding] = []
    embedding, embedding_binding = reader.load(
        tensor_names.embedding,
        logical_role="embedding",
        expected_source_shape=(spec.vocab_size, spec.hidden_size),
        transform="identity",
    )
    bindings.append(embedding_binding)

    layers: list[DecoderBlockWeights] = []
    for layer_index in range(spec.num_hidden_layers):
        layer_weights, layer_bindings = _map_layer(
            reader,
            spec,
            layer_index,
            attention_mode=attention_mode,
            names=tensor_names.layer(layer_index),
        )
        layers.append(layer_weights)
        bindings.extend(layer_bindings)

    final_norm, final_norm_binding = reader.load(
        tensor_names.final_norm,
        logical_role="final_norm",
        expected_source_shape=(spec.hidden_size,),
        transform="identity",
    )
    bindings.append(final_norm_binding)

    if spec.tie_word_embeddings:
        lm_head = np.ascontiguousarray(embedding.T, dtype=np.float32)
        lm_head_binding = TensorMappingBinding(
            logical_role="lm_head_tied",
            source_name=embedding_binding.source_name,
            source_file=embedding_binding.source_file,
            source_dtype=embedding_binding.source_dtype,
            source_shape=embedding_binding.source_shape,
            source_byte_count=embedding_binding.source_byte_count,
            source_range_sha256=embedding_binding.source_range_sha256,
            source_file_sha256=embedding_binding.source_file_sha256,
            transform="transpose_2d",
            mapped_shape=tuple(int(value) for value in lm_head.shape),
            mapped_array_sha3_256=array_commitment(lm_head),
        )
    else:
        lm_head, lm_head_binding = reader.load(
            tensor_names.lm_head,
            logical_role="lm_head",
            expected_source_shape=(spec.vocab_size, spec.hidden_size),
            transform="transpose_2d",
        )
    bindings.append(lm_head_binding)

    weights = CausalLMWeights(
        embedding=embedding,
        layers=tuple(layers),
        final_norm=final_norm,
        lm_head=lm_head,
        tie_word_embeddings=spec.tie_word_embeddings,
    )
    weights.validate(spec, attention_mode=attention_mode)
    return weights, tuple(bindings)


def map_causal_lm(
    model_root: str | Path,
    inventory: ModelWeightInventory,
    spec: TransformerSpec,
    *,
    names: CausalLMTensorNames | None = None,
    attention_mode: Literal["causal", "yarqa"] = "causal",
    max_layers: int = 64,
    max_file_bytes: int = 8 * 1024**3,
    max_tensor_bytes: int = 2 * 1024**3,
    max_total_loaded_bytes: int = 4 * 1024**3,
) -> MappedCausalLM:
    """Map one complete declared dense causal LM into the NumPy reference."""

    if (
        not isinstance(max_layers, int)
        or isinstance(max_layers, bool)
        or max_layers <= 0
    ):
        raise CausalLMMappingError("max_layers must be a positive integer")
    if spec.num_hidden_layers > max_layers:
        raise CausalLMMappingError("configured layer count exceeds max_layers")
    if spec.attention_bias or spec.mlp_bias:
        raise CausalLMMappingError(
            "bias-bearing model mapping is not implemented"
        )
    if spec.hidden_act.lower() not in {"silu", "swiglu"}:
        raise CausalLMMappingError(
            f"unsupported hidden activation: {spec.hidden_act}"
        )
    if attention_mode not in {"causal", "yarqa"}:
        raise CausalLMMappingError("attention_mode must be causal or yarqa")

    tensor_names = names or CausalLMTensorNames()
    tensor_names.validate()
    if not spec.tie_word_embeddings and len(
        {tensor_names.embedding, tensor_names.final_norm, tensor_names.lm_head}
    ) != 3:
        raise CausalLMMappingError(
            "untied embedding, final norm and LM head names must be unique"
        )

    try:
        weights, binding_tuple = _map_complete_model(
            model_root,
            inventory,
            spec,
            tensor_names=tensor_names,
            attention_mode=attention_mode,
            max_file_bytes=max_file_bytes,
            max_tensor_bytes=max_tensor_bytes,
            max_total_loaded_bytes=max_total_loaded_bytes,
        )
    except CausalLMMappingError:
        raise
    except (SafetensorsMappingError, CausalLMReferenceError) as exc:
        raise CausalLMMappingError(str(exc)) from exc

    payload = {
        "schema": "khipu-safetensors-causal-lm-mapping/v0.1",
        "status": "LOCAL_STATIC_FULL_MODEL_MAPPING",
        "attention_mode": attention_mode,
        "inventory_digest": inventory.inventory_digest,
        "source_config_digest": spec.source_config_digest,
        "source_model_type": spec.model_type,
        "layer_count": spec.num_hidden_layers,
        "tie_word_embeddings": spec.tie_word_embeddings,
        "global_tensor_names": tensor_names.as_dict(),
        "bindings": [binding.as_dict() for binding in binding_tuple],
        "weights_manifest_digest": weights.manifest_digest(),
        "content_binding": "FULL_FILE_SHA256_REVERIFIED",
        "model_code_execution": "NOT_PERFORMED",
        "network_access": "NOT_PERFORMED",
        "tokenizer_status": "UNAVAILABLE",
        "hardware_status": "UNAVAILABLE",
        "energy_j": None,
        "energy_status": "UNAVAILABLE",
    }
    mapping_digest = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    chain = ReceiptChain()
    chain.append(
        "safetensors_causal_lm_mapped",
        {**payload, "mapping_digest": mapping_digest},
    )
    chain.require_valid()
    return MappedCausalLM(
        weights=weights,
        bindings=binding_tuple,
        inventory_digest=inventory.inventory_digest,
        source_config_digest=spec.source_config_digest,
        mapping_digest=mapping_digest,
        receipt_chain=chain,
    )


__all__ = [
    "CausalLMMappingError",
    "CausalLMTensorNames",
    "MappedCausalLM",
    "map_causal_lm",
]
