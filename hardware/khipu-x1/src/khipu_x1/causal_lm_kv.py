"""Functional KV-cache prefill and decode reference for KHIPU-X1.

Cache state is returned as immutable snapshots. This is a deterministic NumPy
correctness path only: no tokenizer, hardware, performance, or energy claim is
made.
"""

from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

from .causal_lm_reference import (
    CausalLMReferenceError,
    CausalLMWeights,
    greedy_next_token,
)
from .kids import canonical_json_bytes
from .receipt import ReceiptChain
from .simulator import array_commitment
from .transformer import TransformerSpec
from .transformer_reference import (
    DecoderBlockConfig,
    KVCache,
    TransformerReferenceError,
    embedding_lookup,
    rms_norm,
    run_decoder_block,
)


class CausalLMKVError(ValueError):
    """Raised when a functional KV-cache contract is violated."""


def _token_ids(value: np.ndarray | object, *, single: bool = False) -> np.ndarray:
    array = np.asarray(value)
    if array.dtype.kind not in {"i", "u"}:
        raise CausalLMKVError("token IDs must be integers")
    if array.ndim != 2 or array.shape[0] <= 0 or array.shape[1] <= 0:
        raise CausalLMKVError("token IDs must have non-empty shape [batch, sequence]")
    if single and array.shape[1] != 1:
        raise CausalLMKVError("decode step requires exactly one token per batch item")
    result = np.ascontiguousarray(array.astype(np.int64, copy=False))
    if np.any(result < 0):
        raise CausalLMKVError("token IDs must be non-negative")
    return result


def _canals(value: np.ndarray | object, *, length: int) -> np.ndarray:
    array = np.asarray(value)
    if array.dtype.kind not in {"i", "u"} or array.ndim != 1:
        raise CausalLMKVError("canal IDs must be integer shape [sequence]")
    result = np.ascontiguousarray(array.astype(np.int64, copy=False))
    if result.shape[0] != length or np.any(result < 0):
        raise CausalLMKVError("canal IDs must be non-negative and match sequence length")
    return result


def _freeze(value: np.ndarray) -> np.ndarray:
    result = np.ascontiguousarray(value).copy()
    result.setflags(write=False)
    return result


def _clone_chain(chain: ReceiptChain | None) -> ReceiptChain:
    if chain is None:
        return ReceiptChain()
    chain.require_valid()
    result = copy.deepcopy(chain)
    result.require_valid()
    return result


def _config(
    spec: TransformerSpec,
    mode: Literal["causal", "yarqa"],
) -> DecoderBlockConfig:
    return DecoderBlockConfig(
        hidden_size=spec.hidden_size,
        num_attention_heads=spec.num_attention_heads,
        num_key_value_heads=spec.num_key_value_heads,
        head_dim=spec.head_dim,
        intermediate_size=spec.intermediate_size,
        rms_norm_eps=spec.rms_norm_eps,
        rotary_theta=spec.rope_theta,
        attention_mode=mode,
    )


def _final_projection(
    hidden: np.ndarray,
    weights: CausalLMWeights,
    spec: TransformerSpec,
) -> tuple[np.ndarray, np.ndarray]:
    normalized = rms_norm(hidden, weights.final_norm, eps=spec.rms_norm_eps)
    logits = np.ascontiguousarray(
        np.matmul(normalized.astype(np.float32), weights.lm_head.astype(np.float32)),
        dtype=np.float32,
    )
    if not np.all(np.isfinite(logits)):
        raise CausalLMKVError("KV reference produced non-finite logits")
    return normalized, logits


@dataclass(frozen=True)
class LayerKVSnapshot:
    k: np.ndarray
    v: np.ndarray
    canal_ids: np.ndarray | None

    @classmethod
    def from_cache(cls, cache: KVCache) -> "LayerKVSnapshot":
        k, v, canals = cache.view()
        return cls(
            k=_freeze(k),
            v=_freeze(v),
            canal_ids=_freeze(canals) if canals is not None else None,
        )

    @property
    def length(self) -> int:
        return int(np.asarray(self.k).shape[2])

    def validate(
        self,
        *,
        batch_size: int,
        kv_heads: int,
        sequence_length: int,
        head_dim: int,
        mode: Literal["causal", "yarqa"],
    ) -> None:
        k = np.asarray(self.k)
        v = np.asarray(self.v)
        expected = (batch_size, kv_heads, sequence_length, head_dim)
        if k.shape != expected or v.shape != expected:
            raise CausalLMKVError(
                f"KV snapshot shape mismatch: K={k.shape}, V={v.shape}, expected={expected}"
            )
        if k.dtype != np.float32 or v.dtype != np.float32:
            raise CausalLMKVError("KV snapshots must be float32")
        if k.flags.writeable or v.flags.writeable:
            raise CausalLMKVError("KV snapshot arrays must be read-only")
        if not np.all(np.isfinite(k)) or not np.all(np.isfinite(v)):
            raise CausalLMKVError("KV snapshot contains non-finite values")
        if mode == "yarqa":
            if self.canal_ids is None:
                raise CausalLMKVError("YARQA KV snapshot is missing canal IDs")
            canals = np.asarray(self.canal_ids)
            if canals.shape != (sequence_length,) or canals.dtype != np.int64:
                raise CausalLMKVError("YARQA KV canal snapshot shape or dtype is invalid")
            if canals.flags.writeable or np.any(canals < 0):
                raise CausalLMKVError(
                    "YARQA KV canal snapshot must be read-only and non-negative"
                )
        elif self.canal_ids is not None:
            raise CausalLMKVError("causal KV snapshot must not carry canal IDs")

    def commitment(self) -> str:
        parts = [array_commitment(np.asarray(self.k)), array_commitment(np.asarray(self.v))]
        if self.canal_ids is not None:
            parts.append(array_commitment(np.asarray(self.canal_ids)))
        return hashlib.sha3_256("|".join(parts).encode("ascii")).hexdigest()

    def to_cache(self, *, max_sequence: int) -> KVCache:
        k = np.asarray(self.k)
        cache = KVCache(
            batch_size=k.shape[0],
            kv_heads=k.shape[1],
            max_sequence=min(max_sequence, self.length + 1),
            head_dim=k.shape[3],
        )
        cache.append(k, np.asarray(self.v), canal_ids=self.canal_ids)
        return cache


@dataclass(frozen=True)
class CausalLMKVState:
    layers: tuple[LayerKVSnapshot, ...]
    batch_size: int
    sequence_length: int
    max_sequence: int
    attention_mode: Literal["causal", "yarqa"]
    weights_manifest_digest: str
    source_config_digest: str
    state_digest: str
    receipt_head: str
    receipt_chain: ReceiptChain
    status: str = "SOFTWARE_EMULATED_KV_STATE"
    hardware_status: str = "UNAVAILABLE"
    energy_j: None = None

    def payload(self) -> dict[str, Any]:
        return {
            "schema": "khipu-causal-lm-kv-state/v0.1",
            "status": self.status,
            "batch_size": self.batch_size,
            "sequence_length": self.sequence_length,
            "max_sequence": self.max_sequence,
            "attention_mode": self.attention_mode,
            "weights_manifest_digest": self.weights_manifest_digest,
            "source_config_digest": self.source_config_digest,
            "layer_commitments": [layer.commitment() for layer in self.layers],
            "hardware_status": self.hardware_status,
            "energy_j": self.energy_j,
            "energy_status": "UNAVAILABLE",
        }

    def validate(self, weights: CausalLMWeights, spec: TransformerSpec) -> None:
        if self.batch_size <= 0:
            raise CausalLMKVError("KV state batch size must be positive")
        if not 0 < self.sequence_length <= self.max_sequence:
            raise CausalLMKVError("KV state sequence length is outside its bound")
        if self.max_sequence != spec.max_position_embeddings:
            raise CausalLMKVError("KV state maximum sequence does not match config")
        if self.source_config_digest != spec.source_config_digest:
            raise CausalLMKVError("KV state source configuration digest mismatch")
        if self.weights_manifest_digest != weights.manifest_digest():
            raise CausalLMKVError("KV state weight manifest digest mismatch")
        if len(self.layers) != spec.num_hidden_layers:
            raise CausalLMKVError("KV state layer count does not match config")
        for layer in self.layers:
            layer.validate(
                batch_size=self.batch_size,
                kv_heads=spec.num_key_value_heads,
                sequence_length=self.sequence_length,
                head_dim=spec.head_dim,
                mode=self.attention_mode,
            )
        expected = hashlib.sha256(canonical_json_bytes(self.payload())).hexdigest()
        if self.state_digest != expected:
            raise CausalLMKVError("KV state digest mismatch")
        self.receipt_chain.require_valid()
        if self.receipt_head != self.receipt_chain.head:
            raise CausalLMKVError("KV state receipt-head binding mismatch")


@dataclass(frozen=True)
class KVForwardResult:
    token_ids: np.ndarray
    hidden: np.ndarray
    logits: np.ndarray
    state: CausalLMKVState
    execution_status: str = "SOFTWARE_EMULATED"
    hardware_status: str = "UNAVAILABLE"
    energy_j: None = None


@dataclass(frozen=True)
class CachedGenerationResult:
    token_ids: np.ndarray
    generated_token_ids: np.ndarray
    state: CausalLMKVState
    stopped_on_eos: bool
    execution_status: str = "SOFTWARE_EMULATED"
    hardware_status: str = "UNAVAILABLE"
    energy_j: None = None


def _make_state(
    *,
    snapshots: tuple[LayerKVSnapshot, ...],
    batch_size: int,
    sequence_length: int,
    spec: TransformerSpec,
    mode: Literal["causal", "yarqa"],
    weights_digest: str,
    chain: ReceiptChain,
) -> CausalLMKVState:
    payload = {
        "schema": "khipu-causal-lm-kv-state/v0.1",
        "status": "SOFTWARE_EMULATED_KV_STATE",
        "batch_size": batch_size,
        "sequence_length": sequence_length,
        "max_sequence": spec.max_position_embeddings,
        "attention_mode": mode,
        "weights_manifest_digest": weights_digest,
        "source_config_digest": spec.source_config_digest,
        "layer_commitments": [layer.commitment() for layer in snapshots],
        "hardware_status": "UNAVAILABLE",
        "energy_j": None,
        "energy_status": "UNAVAILABLE",
    }
    return CausalLMKVState(
        layers=snapshots,
        batch_size=batch_size,
        sequence_length=sequence_length,
        max_sequence=spec.max_position_embeddings,
        attention_mode=mode,
        weights_manifest_digest=weights_digest,
        source_config_digest=spec.source_config_digest,
        state_digest=hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
        receipt_head=chain.head,
        receipt_chain=chain,
    )


def _run_layers(
    hidden: np.ndarray,
    weights: CausalLMWeights,
    spec: TransformerSpec,
    *,
    mode: Literal["causal", "yarqa"],
    positions: np.ndarray,
    canals: np.ndarray | None,
    chain: ReceiptChain,
    prior: tuple[LayerKVSnapshot, ...] | None,
) -> tuple[np.ndarray, tuple[LayerKVSnapshot, ...], ReceiptChain]:
    snapshots: list[LayerKVSnapshot] = []
    config = _config(spec, mode)
    try:
        for index, layer_weights in enumerate(weights.layers):
            if prior is None:
                cache = KVCache(
                    batch_size=hidden.shape[0],
                    kv_heads=spec.num_key_value_heads,
                    max_sequence=hidden.shape[1],
                    head_dim=spec.head_dim,
                )
            else:
                cache = prior[index].to_cache(
                    max_sequence=spec.max_position_embeddings
                )
            result = run_decoder_block(
                hidden,
                layer_weights,
                config,
                positions=positions,
                cache=cache,
                canal_ids=canals,
                chain=chain,
            )
            hidden = result.hidden
            chain = result.receipt_chain
            snapshots.append(LayerKVSnapshot.from_cache(cache))
    except (TransformerReferenceError, CausalLMReferenceError) as exc:
        raise CausalLMKVError(str(exc)) from exc
    return hidden, tuple(snapshots), chain


def prefill_causal_lm(
    token_ids: np.ndarray | object,
    weights: CausalLMWeights,
    spec: TransformerSpec,
    *,
    attention_mode: Literal["causal", "yarqa"] = "causal",
    canal_ids: np.ndarray | None = None,
    chain: ReceiptChain | None = None,
) -> KVForwardResult:
    """Run one prompt prefill and return immutable per-layer KV snapshots."""

    ids = _token_ids(token_ids)
    if np.any(ids >= spec.vocab_size):
        raise CausalLMKVError("token ID is outside the configured vocabulary")
    if ids.shape[1] > spec.max_position_embeddings:
        raise CausalLMKVError("prompt exceeds max_position_embeddings")
    if attention_mode not in {"causal", "yarqa"}:
        raise CausalLMKVError("attention_mode must be causal or yarqa")
    if attention_mode == "yarqa":
        if canal_ids is None:
            raise CausalLMKVError("YARQA prefill requires canal IDs")
        canals = _canals(canal_ids, length=ids.shape[1])
    elif canal_ids is not None:
        raise CausalLMKVError("canal IDs are valid only in YARQA mode")
    else:
        canals = None
    try:
        weights.validate(spec, attention_mode=attention_mode)
    except CausalLMReferenceError as exc:
        raise CausalLMKVError(str(exc)) from exc

    receipt_chain = _clone_chain(chain)
    hidden = embedding_lookup(weights.embedding, ids)
    hidden, snapshots, receipt_chain = _run_layers(
        hidden,
        weights,
        spec,
        mode=attention_mode,
        positions=np.arange(ids.shape[1], dtype=np.int64),
        canals=canals,
        chain=receipt_chain,
        prior=None,
    )
    normalized, logits = _final_projection(hidden, weights, spec)
    weights_digest = weights.manifest_digest()
    provisional = _make_state(
        snapshots=snapshots,
        batch_size=ids.shape[0],
        sequence_length=ids.shape[1],
        spec=spec,
        mode=attention_mode,
        weights_digest=weights_digest,
        chain=receipt_chain,
    )
    receipt_chain.append(
        "causal_lm_kv_prefill_completed",
        {
            "execution_status": "SOFTWARE_EMULATED",
            "attention_mode": attention_mode,
            "batch": int(ids.shape[0]),
            "sequence": int(ids.shape[1]),
            "token_ids_commitment": array_commitment(ids),
            "hidden_commitment": array_commitment(normalized),
            "logits_commitment": array_commitment(logits),
            "weights_manifest_digest": weights_digest,
            "source_config_digest": spec.source_config_digest,
            "kv_state_digest": provisional.state_digest,
            "cache_update": "FUNCTIONAL_SNAPSHOT",
            "hardware_status": "UNAVAILABLE",
            "energy_j": None,
            "energy_status": "UNAVAILABLE",
        },
    )
    receipt_chain.require_valid()
    state = _make_state(
        snapshots=snapshots,
        batch_size=ids.shape[0],
        sequence_length=ids.shape[1],
        spec=spec,
        mode=attention_mode,
        weights_digest=weights_digest,
        chain=receipt_chain,
    )
    state.validate(weights, spec)
    return KVForwardResult(ids, normalized, logits, state)


def decode_causal_lm_step(
    token_ids: np.ndarray | object,
    state: CausalLMKVState,
    weights: CausalLMWeights,
    spec: TransformerSpec,
    *,
    canal_id: int | None = None,
) -> KVForwardResult:
    """Append one token to a functional KV state and return a new state."""

    state.validate(weights, spec)
    ids = _token_ids(token_ids, single=True)
    if ids.shape[0] != state.batch_size:
        raise CausalLMKVError("decode batch size does not match KV state")
    if np.any(ids >= spec.vocab_size):
        raise CausalLMKVError("token ID is outside the configured vocabulary")
    if state.sequence_length >= state.max_sequence:
        raise CausalLMKVError("KV state has reached max_position_embeddings")
    if state.attention_mode == "yarqa":
        if (
            not isinstance(canal_id, int)
            or isinstance(canal_id, bool)
            or canal_id < 0
        ):
            raise CausalLMKVError("YARQA decode requires a non-negative canal_id")
        canals = np.array([canal_id], dtype=np.int64)
    elif canal_id is not None:
        raise CausalLMKVError("canal_id is valid only in YARQA mode")
    else:
        canals = None

    receipt_chain = _clone_chain(state.receipt_chain)
    hidden = embedding_lookup(weights.embedding, ids)
    hidden, snapshots, receipt_chain = _run_layers(
        hidden,
        weights,
        spec,
        mode=state.attention_mode,
        positions=np.array([state.sequence_length], dtype=np.int64),
        canals=canals,
        chain=receipt_chain,
        prior=state.layers,
    )
    normalized, logits = _final_projection(hidden, weights, spec)
    provisional = _make_state(
        snapshots=snapshots,
        batch_size=state.batch_size,
        sequence_length=state.sequence_length + 1,
        spec=spec,
        mode=state.attention_mode,
        weights_digest=state.weights_manifest_digest,
        chain=receipt_chain,
    )
    receipt_chain.append(
        "causal_lm_kv_decode_step_completed",
        {
            "execution_status": "SOFTWARE_EMULATED",
            "attention_mode": state.attention_mode,
            "position": state.sequence_length,
            "token_ids_commitment": array_commitment(ids),
            "hidden_commitment": array_commitment(normalized),
            "logits_commitment": array_commitment(logits),
            "previous_kv_state_digest": state.state_digest,
            "kv_state_digest": provisional.state_digest,
            "cache_update": "FUNCTIONAL_SNAPSHOT",
            "hardware_status": "UNAVAILABLE",
            "energy_j": None,
            "energy_status": "UNAVAILABLE",
        },
    )
    receipt_chain.require_valid()
    next_state = _make_state(
        snapshots=snapshots,
        batch_size=state.batch_size,
        sequence_length=state.sequence_length + 1,
        spec=spec,
        mode=state.attention_mode,
        weights_digest=state.weights_manifest_digest,
        chain=receipt_chain,
    )
    next_state.validate(weights, spec)
    return KVForwardResult(ids, normalized, logits, next_state)


def greedy_generate_cached(
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
) -> CachedGenerationResult:
    """Generate with one prefill followed by functional single-token KV steps."""

    if (
        not isinstance(max_new_tokens, int)
        or isinstance(max_new_tokens, bool)
        or not 1 <= max_new_tokens <= 64
    ):
        raise CausalLMKVError("max_new_tokens must be an integer in [1, 64]")
    if eos_token_id is not None and (
        not isinstance(eos_token_id, int)
        or isinstance(eos_token_id, bool)
        or not 0 <= eos_token_id < spec.vocab_size
    ):
        raise CausalLMKVError("eos_token_id is outside the vocabulary")
    prompt = _token_ids(prompt_token_ids)
    if prompt.shape[1] + max_new_tokens > spec.max_position_embeddings:
        raise CausalLMKVError("generation budget exceeds max_position_embeddings")
    if attention_mode == "yarqa":
        if (
            generated_canal_id is None
            or not isinstance(generated_canal_id, int)
            or isinstance(generated_canal_id, bool)
            or generated_canal_id < 0
        ):
            raise CausalLMKVError(
                "YARQA generation requires a non-negative generated_canal_id"
            )
    elif generated_canal_id is not None:
        raise CausalLMKVError("generated_canal_id is valid only in YARQA mode")

    prefill = prefill_causal_lm(
        prompt,
        weights,
        spec,
        attention_mode=attention_mode,
        canal_ids=canal_ids,
        chain=chain,
    )
    all_ids = prompt.copy()
    generated: list[np.ndarray] = []
    state = prefill.state
    logits = prefill.logits
    stopped = False
    for _ in range(max_new_tokens):
        next_ids = greedy_next_token(logits)[:, None]
        all_ids = np.ascontiguousarray(np.concatenate((all_ids, next_ids), axis=1))
        generated.append(next_ids.copy())
        step = decode_causal_lm_step(
            next_ids,
            state,
            weights,
            spec,
            canal_id=generated_canal_id if attention_mode == "yarqa" else None,
        )
        state = step.state
        logits = step.logits
        if eos_token_id is not None and np.all(next_ids[:, 0] == eos_token_id):
            stopped = True
            break

    generated_ids = np.ascontiguousarray(np.concatenate(generated, axis=1))
    final_chain = _clone_chain(state.receipt_chain)
    final_chain.append(
        "causal_lm_cached_generation_completed",
        {
            "execution_status": "SOFTWARE_EMULATED",
            "attention_mode": attention_mode,
            "prompt_length": int(prompt.shape[1]),
            "generated_length": int(generated_ids.shape[1]),
            "max_new_tokens": max_new_tokens,
            "stopped_on_eos": stopped,
            "final_token_ids_commitment": array_commitment(all_ids),
            "generated_token_ids_commitment": array_commitment(generated_ids),
            "final_kv_state_digest": state.state_digest,
            "sampling": "GREEDY_ARGMAX_LOWEST_INDEX_TIEBREAK",
            "decode_strategy": "ONE_PREFILL_THEN_FUNCTIONAL_KV_STEPS",
            "hardware_status": "UNAVAILABLE",
            "energy_j": None,
            "energy_status": "UNAVAILABLE",
        },
    )
    final_chain.require_valid()
    final_state = _make_state(
        snapshots=state.layers,
        batch_size=state.batch_size,
        sequence_length=state.sequence_length,
        spec=spec,
        mode=state.attention_mode,
        weights_digest=state.weights_manifest_digest,
        chain=final_chain,
    )
    final_state.validate(weights, spec)
    return CachedGenerationResult(
        token_ids=all_ids,
        generated_token_ids=generated_ids,
        state=final_state,
        stopped_on_eos=stopped,
    )


__all__ = [
    "CachedGenerationResult",
    "CausalLMKVError",
    "CausalLMKVState",
    "KVForwardResult",
    "LayerKVSnapshot",
    "decode_causal_lm_step",
    "greedy_generate_cached",
    "prefill_causal_lm",
]
