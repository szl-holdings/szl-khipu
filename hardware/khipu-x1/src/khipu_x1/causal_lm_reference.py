"""Deterministic, bounded causal-LM reference for KHIPU-X1.

The implementation composes the Wave 6 decoder block into a tiny complete
language-model truth surface. It is intentionally simple and CPU/NumPy only:
no tokenizer, dynamic model code, network access, accelerator execution,
performance claim, or measured-energy claim is involved.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

from .kids import canonical_json_bytes
from .receipt import ReceiptChain
from .simulator import array_commitment
from .transformer import TransformerSpec
from .transformer_reference import (
    DecoderBlockConfig,
    DecoderBlockWeights,
    TransformerReferenceError,
    embedding_lookup,
    rms_norm,
    run_decoder_block,
)


class CausalLMReferenceError(ValueError):
    """Raised when a complete causal-LM reference contract is violated."""


def _integer_token_ids(value: np.ndarray | object, *, name: str) -> np.ndarray:
    array = np.asarray(value)
    if array.dtype.kind not in {"i", "u"}:
        raise CausalLMReferenceError(f"{name} must contain integers")
    if array.ndim != 2 or array.shape[0] <= 0 or array.shape[1] <= 0:
        raise CausalLMReferenceError(f"{name} must have non-empty shape [batch, sequence]")
    ids = np.ascontiguousarray(array.astype(np.int64, copy=False))
    if np.any(ids < 0):
        raise CausalLMReferenceError(f"{name} must be non-negative")
    return ids


def _finite_float32(value: np.ndarray | object, *, name: str) -> np.ndarray:
    array = np.asarray(value)
    if array.dtype.kind not in {"f", "i", "u", "b"}:
        raise CausalLMReferenceError(f"{name} has unsupported dtype {array.dtype}")
    result = np.ascontiguousarray(array.astype(np.float32, copy=False))
    if not np.all(np.isfinite(result)):
        raise CausalLMReferenceError(f"{name} contains non-finite values")
    return result


def _decoder_config(
    spec: TransformerSpec,
    attention_mode: Literal["causal", "yarqa"],
) -> DecoderBlockConfig:
    return DecoderBlockConfig(
        hidden_size=spec.hidden_size,
        num_attention_heads=spec.num_attention_heads,
        num_key_value_heads=spec.num_key_value_heads,
        head_dim=spec.head_dim,
        intermediate_size=spec.intermediate_size,
        rms_norm_eps=spec.rms_norm_eps,
        rotary_theta=spec.rope_theta,
        attention_mode=attention_mode,
    )


@dataclass(frozen=True)
class CausalLMWeights:
    embedding: np.ndarray
    layers: tuple[DecoderBlockWeights, ...]
    final_norm: np.ndarray
    lm_head: np.ndarray
    tie_word_embeddings: bool

    def validate(
        self,
        spec: TransformerSpec,
        *,
        attention_mode: Literal["causal", "yarqa"] = "causal",
    ) -> None:
        if spec.attention_bias or spec.mlp_bias:
            raise CausalLMReferenceError(
                "bias-bearing causal-LM references are not implemented"
            )
        if spec.hidden_act.lower() not in {"silu", "swiglu"}:
            raise CausalLMReferenceError(
                f"unsupported hidden activation: {spec.hidden_act}"
            )
        embedding = _finite_float32(self.embedding, name="weights.embedding")
        final_norm = _finite_float32(self.final_norm, name="weights.final_norm")
        lm_head = _finite_float32(self.lm_head, name="weights.lm_head")
        if embedding.shape != (spec.vocab_size, spec.hidden_size):
            raise CausalLMReferenceError(
                f"embedding shape {embedding.shape} != {(spec.vocab_size, spec.hidden_size)}"
            )
        if final_norm.shape != (spec.hidden_size,):
            raise CausalLMReferenceError("final norm shape does not match hidden_size")
        if lm_head.shape != (spec.hidden_size, spec.vocab_size):
            raise CausalLMReferenceError(
                f"LM head shape {lm_head.shape} != {(spec.hidden_size, spec.vocab_size)}"
            )
        if not isinstance(self.tie_word_embeddings, bool):
            raise CausalLMReferenceError("tie_word_embeddings must be boolean")
        if self.tie_word_embeddings != spec.tie_word_embeddings:
            raise CausalLMReferenceError(
                "weight tying state does not match the transformer configuration"
            )
        if self.tie_word_embeddings and not np.array_equal(lm_head, embedding.T):
            raise CausalLMReferenceError(
                "tied LM head must equal the exact embedding transpose"
            )
        if len(self.layers) != spec.num_hidden_layers:
            raise CausalLMReferenceError(
                f"layer count {len(self.layers)} != {spec.num_hidden_layers}"
            )
        config = _decoder_config(spec, attention_mode)
        for index, layer in enumerate(self.layers):
            try:
                layer.validate(config)
            except TransformerReferenceError as exc:
                raise CausalLMReferenceError(
                    f"decoder layer {index} violates the reference contract: {exc}"
                ) from exc

    def manifest(self) -> dict[str, Any]:
        return {
            "embedding": array_commitment(np.asarray(self.embedding)),
            "layers": [
                {
                    "attention_norm": array_commitment(layer.attention_norm),
                    "q_proj": array_commitment(layer.q_proj),
                    "k_proj": array_commitment(layer.k_proj),
                    "v_proj": array_commitment(layer.v_proj),
                    "o_proj": array_commitment(layer.o_proj),
                    "ffn_norm": array_commitment(layer.ffn_norm),
                    "gate_proj": array_commitment(layer.gate_proj),
                    "up_proj": array_commitment(layer.up_proj),
                    "down_proj": array_commitment(layer.down_proj),
                }
                for layer in self.layers
            ],
            "final_norm": array_commitment(np.asarray(self.final_norm)),
            "lm_head": array_commitment(np.asarray(self.lm_head)),
            "tie_word_embeddings": self.tie_word_embeddings,
        }

    def manifest_digest(self) -> str:
        return hashlib.sha256(canonical_json_bytes(self.manifest())).hexdigest()


@dataclass(frozen=True)
class CausalLMResult:
    token_ids: np.ndarray
    hidden: np.ndarray
    logits: np.ndarray
    receipt_chain: ReceiptChain
    weights_manifest_digest: str
    execution_status: str = "SOFTWARE_EMULATED"
    hardware_status: str = "UNAVAILABLE"
    energy_j: None = None


@dataclass(frozen=True)
class GreedyGenerationResult:
    token_ids: np.ndarray
    generated_token_ids: np.ndarray
    receipt_chain: ReceiptChain
    stopped_on_eos: bool
    execution_status: str = "SOFTWARE_EMULATED"
    hardware_status: str = "UNAVAILABLE"
    energy_j: None = None


def run_causal_lm(
    token_ids: np.ndarray | object,
    weights: CausalLMWeights,
    spec: TransformerSpec,
    *,
    attention_mode: Literal["causal", "yarqa"] = "causal",
    canal_ids: np.ndarray | None = None,
    chain: ReceiptChain | None = None,
) -> CausalLMResult:
    """Execute a complete bounded causal-LM forward pass on CPU/NumPy."""

    ids = _integer_token_ids(token_ids, name="token_ids")
    if np.any(ids >= spec.vocab_size):
        raise CausalLMReferenceError("token ID is outside the configured vocabulary")
    if ids.shape[1] > spec.max_position_embeddings:
        raise CausalLMReferenceError("sequence exceeds max_position_embeddings")
    if attention_mode not in {"causal", "yarqa"}:
        raise CausalLMReferenceError("attention_mode must be causal or yarqa")
    if attention_mode == "yarqa":
        if canal_ids is None:
            raise CausalLMReferenceError("YARQA mode requires canal IDs")
        canals = np.asarray(canal_ids)
        if canals.dtype.kind not in {"i", "u"} or canals.ndim != 1:
            raise CausalLMReferenceError("canal IDs must be integer shape [sequence]")
        if canals.shape[0] != ids.shape[1] or np.any(canals.astype(np.int64) < 0):
            raise CausalLMReferenceError(
                "canal IDs must be non-negative and match the sequence length"
            )
        canals = np.ascontiguousarray(canals.astype(np.int64, copy=False))
    elif canal_ids is not None:
        raise CausalLMReferenceError("canal IDs are valid only in YARQA mode")
    else:
        canals = None

    weights.validate(spec, attention_mode=attention_mode)
    receipt_chain = chain if chain is not None else ReceiptChain()
    start_depth = len(receipt_chain.events)
    hidden = embedding_lookup(weights.embedding, ids)
    positions = np.arange(ids.shape[1], dtype=np.int64)
    config = _decoder_config(spec, attention_mode)
    for layer_index, layer_weights in enumerate(weights.layers):
        result = run_decoder_block(
            hidden,
            layer_weights,
            config,
            positions=positions,
            canal_ids=canals,
            chain=receipt_chain,
        )
        hidden = result.hidden
        receipt_chain = result.receipt_chain
        if len(receipt_chain.events) != start_depth + layer_index + 1:
            raise CausalLMReferenceError("decoder receipt depth advanced unexpectedly")

    normalized = rms_norm(hidden, weights.final_norm, eps=spec.rms_norm_eps)
    logits = np.ascontiguousarray(
        np.matmul(normalized.astype(np.float32), weights.lm_head.astype(np.float32)),
        dtype=np.float32,
    )
    if not np.all(np.isfinite(logits)):
        raise CausalLMReferenceError("causal-LM logits contain non-finite values")

    manifest_digest = weights.manifest_digest()
    receipt_chain.append(
        "causal_lm_reference_executed",
        {
            "execution_path": "software_reference_numpy",
            "execution_status": "SOFTWARE_EMULATED",
            "attention_mode": attention_mode,
            "batch": int(ids.shape[0]),
            "sequence": int(ids.shape[1]),
            "vocab_size": spec.vocab_size,
            "hidden_size": spec.hidden_size,
            "layer_count": spec.num_hidden_layers,
            "token_ids_commitment": array_commitment(ids),
            "hidden_commitment": array_commitment(hidden),
            "normalized_commitment": array_commitment(normalized),
            "logits_commitment": array_commitment(logits),
            "weights_manifest_digest": manifest_digest,
            "source_config_digest": spec.source_config_digest,
            "model_code_execution": "NOT_PERFORMED",
            "network_access": "NOT_PERFORMED",
            "hardware_status": "UNAVAILABLE",
            "energy_j": None,
            "energy_status": "UNAVAILABLE",
        },
    )
    receipt_chain.require_valid()
    return CausalLMResult(
        token_ids=ids,
        hidden=normalized,
        logits=logits,
        receipt_chain=receipt_chain,
        weights_manifest_digest=manifest_digest,
    )


def greedy_next_token(logits: np.ndarray | object) -> np.ndarray:
    """Return the lowest-index maximum token from the final sequence position."""

    values = _finite_float32(logits, name="logits")
    if values.ndim != 3 or values.shape[0] <= 0 or values.shape[1] <= 0 or values.shape[2] <= 0:
        raise CausalLMReferenceError("logits must have non-empty shape [batch, sequence, vocab]")
    return np.ascontiguousarray(np.argmax(values[:, -1, :], axis=-1).astype(np.int64))


def greedy_generate(
    prompt_token_ids: np.ndarray | object,
    weights: CausalLMWeights,
    spec: TransformerSpec,
    *,
    max_new_tokens: int,
    eos_token_id: int | None = None,
    attention_mode: Literal["causal", "yarqa"] = "causal",
    canal_ids: np.ndarray | None = None,
    generated_canal_id: int | None = None,
    chain: ReceiptChain | None = None,
) -> GreedyGenerationResult:
    """Bounded deterministic greedy generation by repeated full forward passes."""

    if (
        not isinstance(max_new_tokens, int)
        or isinstance(max_new_tokens, bool)
        or not 1 <= max_new_tokens <= 64
    ):
        raise CausalLMReferenceError("max_new_tokens must be an integer in [1, 64]")
    if eos_token_id is not None and (
        not isinstance(eos_token_id, int)
        or isinstance(eos_token_id, bool)
        or not 0 <= eos_token_id < spec.vocab_size
    ):
        raise CausalLMReferenceError("eos_token_id is outside the vocabulary")
    ids = _integer_token_ids(prompt_token_ids, name="prompt_token_ids")
    if ids.shape[1] + max_new_tokens > spec.max_position_embeddings:
        raise CausalLMReferenceError("generation budget exceeds max_position_embeddings")

    if attention_mode == "yarqa":
        if canal_ids is None or generated_canal_id is None:
            raise CausalLMReferenceError(
                "YARQA generation requires prompt canal IDs and generated_canal_id"
            )
        if (
            not isinstance(generated_canal_id, int)
            or isinstance(generated_canal_id, bool)
            or generated_canal_id < 0
        ):
            raise CausalLMReferenceError("generated_canal_id must be a non-negative integer")
        active_canals = np.ascontiguousarray(np.asarray(canal_ids, dtype=np.int64))
    elif canal_ids is not None or generated_canal_id is not None:
        raise CausalLMReferenceError(
            "canal arguments are valid only for YARQA generation"
        )
    else:
        active_canals = None

    receipt_chain = chain if chain is not None else ReceiptChain()
    prompt_length = ids.shape[1]
    stopped = False
    for _ in range(max_new_tokens):
        result = run_causal_lm(
            ids,
            weights,
            spec,
            attention_mode=attention_mode,
            canal_ids=active_canals,
            chain=receipt_chain,
        )
        receipt_chain = result.receipt_chain
        next_ids = greedy_next_token(result.logits)[:, None]
        ids = np.ascontiguousarray(np.concatenate((ids, next_ids), axis=1))
        if active_canals is not None:
            active_canals = np.ascontiguousarray(
                np.concatenate(
                    (active_canals, np.array([generated_canal_id], dtype=np.int64))
                )
            )
        if eos_token_id is not None and np.all(next_ids[:, 0] == eos_token_id):
            stopped = True
            break

    generated = np.ascontiguousarray(ids[:, prompt_length:])
    receipt_chain.append(
        "greedy_generation_completed",
        {
            "execution_status": "SOFTWARE_EMULATED",
            "attention_mode": attention_mode,
            "prompt_length": prompt_length,
            "generated_length": int(generated.shape[1]),
            "max_new_tokens": max_new_tokens,
            "stopped_on_eos": stopped,
            "final_token_ids_commitment": array_commitment(ids),
            "generated_token_ids_commitment": array_commitment(generated),
            "sampling": "GREEDY_ARGMAX_LOWEST_INDEX_TIEBREAK",
            "hardware_status": "UNAVAILABLE",
            "energy_j": None,
            "energy_status": "UNAVAILABLE",
        },
    )
    receipt_chain.require_valid()
    return GreedyGenerationResult(
        token_ids=ids,
        generated_token_ids=generated,
        receipt_chain=receipt_chain,
        stopped_on_eos=stopped,
    )


__all__ = [
    "CausalLMReferenceError",
    "CausalLMResult",
    "CausalLMWeights",
    "GreedyGenerationResult",
    "greedy_generate",
    "greedy_next_token",
    "run_causal_lm",
]
