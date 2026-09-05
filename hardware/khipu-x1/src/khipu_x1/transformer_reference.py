"""Deterministic NumPy transformer reference operations for KHIPU-X1.

This module is a software reference only. It does not load model code, execute
on an FPGA/ASIC, measure energy, or claim performance equivalence with a
production inference engine.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, fields
from typing import Literal

import numpy as np

from .receipt import ReceiptChain
from .simulator import array_commitment


class TransformerReferenceError(ValueError):
    """Raised when a reference transformer contract is violated."""


def _finite(name: str, value: np.ndarray | object) -> np.ndarray:
    array = np.asarray(value)
    if array.dtype.kind not in {"f", "i", "u", "b"}:
        raise TransformerReferenceError(f"{name} has unsupported dtype {array.dtype}")
    if array.dtype.kind == "f" and not np.all(np.isfinite(array)):
        raise TransformerReferenceError(f"{name} contains non-finite values")
    return np.ascontiguousarray(array)


def _float32(name: str, value: np.ndarray | object) -> np.ndarray:
    return np.ascontiguousarray(_finite(name, value).astype(np.float32, copy=False))


def _linear(name: str, x: np.ndarray, weight: np.ndarray) -> np.ndarray:
    data = _float32(f"{name}.input", x)
    matrix = _float32(f"{name}.weight", weight)
    if matrix.ndim != 2:
        raise TransformerReferenceError(f"{name}.weight must be rank 2")
    if data.shape[-1] != matrix.shape[0]:
        raise TransformerReferenceError(
            f"{name} shape mismatch: input width {data.shape[-1]} != weight rows {matrix.shape[0]}"
        )
    return np.ascontiguousarray(np.matmul(data, matrix), dtype=np.float32)


def embedding_lookup(table: np.ndarray, token_ids: np.ndarray) -> np.ndarray:
    """Look up integer token IDs in a finite rank-2 embedding table."""

    embeddings = _float32("embedding.table", table)
    ids = _finite("embedding.token_ids", token_ids)
    if embeddings.ndim != 2 or embeddings.shape[0] == 0 or embeddings.shape[1] == 0:
        raise TransformerReferenceError("embedding table must be non-empty rank 2")
    if ids.dtype.kind not in {"i", "u"}:
        raise TransformerReferenceError("token IDs must be integers")
    if ids.ndim not in {1, 2}:
        raise TransformerReferenceError("token IDs must have shape [seq] or [batch, seq]")
    ids64 = ids.astype(np.int64, copy=False)
    if np.any(ids64 < 0) or np.any(ids64 >= embeddings.shape[0]):
        raise TransformerReferenceError("token ID is outside the embedding vocabulary")
    return np.ascontiguousarray(embeddings[ids64], dtype=np.float32)


def rms_norm(x: np.ndarray, weight: np.ndarray, *, eps: float = 1e-6) -> np.ndarray:
    """Reference RMSNorm over the final axis with a required learned weight."""

    data = _float32("rms_norm.input", x)
    scale = _float32("rms_norm.weight", weight)
    if data.ndim < 1 or data.shape[-1] == 0:
        raise TransformerReferenceError("RMSNorm input must have a non-empty final axis")
    if scale.ndim != 1 or scale.shape[0] != data.shape[-1]:
        raise TransformerReferenceError("RMSNorm weight width must match the input")
    if not math.isfinite(eps) or eps <= 0:
        raise TransformerReferenceError("RMSNorm epsilon must be finite and positive")
    mean_square = np.mean(np.square(data, dtype=np.float64), axis=-1, keepdims=True)
    result = data / np.sqrt(mean_square + eps)
    return np.ascontiguousarray(result * scale, dtype=np.float32)


def apply_rope(
    q: np.ndarray,
    k: np.ndarray,
    positions: np.ndarray,
    *,
    theta: float = 10_000.0,
    rotary_dim: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply pairwise rotary position embedding to Q and K."""

    query = _float32("rope.q", q)
    key = _float32("rope.k", k)
    pos = _finite("rope.positions", positions)
    if query.ndim != 4 or key.ndim != 4:
        raise TransformerReferenceError("RoPE Q and K must be rank 4")
    if query.shape[0] != key.shape[0] or query.shape[2:] != key.shape[2:]:
        raise TransformerReferenceError("RoPE Q and K batch/sequence/head_dim must match")
    if pos.dtype.kind not in {"i", "u"} or pos.ndim != 1 or pos.shape[0] != query.shape[2]:
        raise TransformerReferenceError("RoPE positions must be integer shape [sequence]")
    pos64 = pos.astype(np.int64, copy=False)
    if np.any(pos64 < 0):
        raise TransformerReferenceError("RoPE positions must be non-negative")
    if not math.isfinite(theta) or theta <= 1.0:
        raise TransformerReferenceError("RoPE theta must be finite and greater than 1")

    head_dim = query.shape[-1]
    dimension = head_dim if rotary_dim is None else rotary_dim
    if not isinstance(dimension, int) or dimension <= 0 or dimension > head_dim or dimension % 2:
        raise TransformerReferenceError("rotary_dim must be positive, even and <= head_dim")

    inverse = theta ** (-np.arange(0, dimension, 2, dtype=np.float64) / dimension)
    angles = np.outer(pos64.astype(np.float64), inverse)
    cosine = np.cos(angles).astype(np.float32)[None, None, :, :]
    sine = np.sin(angles).astype(np.float32)[None, None, :, :]

    def rotate(value: np.ndarray) -> np.ndarray:
        prefix = value[..., :dimension]
        even = prefix[..., 0::2]
        odd = prefix[..., 1::2]
        rotated = np.empty_like(prefix)
        rotated[..., 0::2] = even * cosine - odd * sine
        rotated[..., 1::2] = even * sine + odd * cosine
        if dimension == head_dim:
            return np.ascontiguousarray(rotated)
        return np.ascontiguousarray(np.concatenate((rotated, value[..., dimension:]), axis=-1))

    return rotate(query), rotate(key)


def _stable_softmax(scores: np.ndarray, allowed: np.ndarray) -> np.ndarray:
    if scores.shape != allowed.shape:
        raise TransformerReferenceError("attention mask shape mismatch")
    if not np.all(np.any(allowed, axis=-1)):
        raise TransformerReferenceError("attention contains an all-masked query row")
    masked = np.where(allowed, scores, -np.inf)
    maximum = np.max(masked, axis=-1, keepdims=True)
    exponential = np.where(allowed, np.exp(masked - maximum), 0.0)
    denominator = np.sum(exponential, axis=-1, keepdims=True)
    return np.ascontiguousarray(exponential / denominator, dtype=np.float32)


def grouped_query_attention(
    q: np.ndarray,
    k: np.ndarray,
    v: np.ndarray,
    *,
    causal: bool = True,
    query_start: int = 0,
    allowed_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Reference GQA/MQA attention with an explicit optional allowed mask."""

    query = _float32("attention.q", q)
    key = _float32("attention.k", k)
    value = _float32("attention.v", v)
    if query.ndim != 4 or key.ndim != 4 or value.ndim != 4:
        raise TransformerReferenceError("attention Q/K/V must be rank 4")
    if key.shape != value.shape:
        raise TransformerReferenceError("attention K and V shapes must match")
    if query.shape[0] != key.shape[0] or query.shape[-1] != key.shape[-1]:
        raise TransformerReferenceError("attention batch and head dimensions must match")
    if query.shape[1] % key.shape[1] != 0:
        raise TransformerReferenceError("query heads must be divisible by KV heads")
    if query.shape[2] == 0 or key.shape[2] == 0 or query.shape[-1] == 0:
        raise TransformerReferenceError("attention dimensions must be non-empty")
    if not isinstance(query_start, int) or query_start < 0:
        raise TransformerReferenceError("query_start must be a non-negative integer")

    repeat = query.shape[1] // key.shape[1]
    expanded_k = np.repeat(key, repeat, axis=1)
    expanded_v = np.repeat(value, repeat, axis=1)
    scores = np.matmul(query, np.swapaxes(expanded_k, -1, -2))
    scores = scores / math.sqrt(query.shape[-1])

    batch, heads, query_len, key_len = scores.shape
    allowed = np.ones((batch, heads, query_len, key_len), dtype=bool)
    if causal:
        query_positions = query_start + np.arange(query_len, dtype=np.int64)
        key_positions = np.arange(key_len, dtype=np.int64)
        allowed &= key_positions[None, None, None, :] <= query_positions[None, None, :, None]
    if allowed_mask is not None:
        external = np.asarray(allowed_mask, dtype=bool)
        if external.ndim == 2:
            external = external[None, None, :, :]
        elif external.ndim == 3:
            external = external[:, None, :, :]
        try:
            external = np.broadcast_to(external, allowed.shape)
        except ValueError as exc:
            raise TransformerReferenceError("allowed attention mask is not broadcastable") from exc
        allowed &= external

    probabilities = _stable_softmax(scores.astype(np.float32), allowed)
    output = np.matmul(probabilities, expanded_v)
    return np.ascontiguousarray(output, dtype=np.float32), probabilities


def yarqa_attention(
    q: np.ndarray,
    k: np.ndarray,
    v: np.ndarray,
    *,
    query_canal_ids: np.ndarray,
    key_canal_ids: np.ndarray,
    causal: bool = True,
    query_start: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Reference canal-isolated attention."""

    query_canals = _finite("yarqa.query_canal_ids", query_canal_ids)
    key_canals = _finite("yarqa.key_canal_ids", key_canal_ids)
    if query_canals.dtype.kind not in {"i", "u"} or key_canals.dtype.kind not in {"i", "u"}:
        raise TransformerReferenceError("YARQA canal IDs must be integers")
    if query_canals.ndim != 1 or key_canals.ndim != 1:
        raise TransformerReferenceError("YARQA canal IDs must be rank 1")
    if query_canals.shape[0] != np.asarray(q).shape[2]:
        raise TransformerReferenceError("query canal count must equal query length")
    if key_canals.shape[0] != np.asarray(k).shape[2]:
        raise TransformerReferenceError("key canal count must equal key length")
    same_canal = query_canals[:, None] == key_canals[None, :]
    return grouped_query_attention(
        q,
        k,
        v,
        causal=causal,
        query_start=query_start,
        allowed_mask=same_canal,
    )


class KVCache:
    """Bounded in-memory KV cache for deterministic reference decoding."""

    def __init__(self, *, batch_size: int, kv_heads: int, max_sequence: int, head_dim: int) -> None:
        for name, value in {
            "batch_size": batch_size,
            "kv_heads": kv_heads,
            "max_sequence": max_sequence,
            "head_dim": head_dim,
        }.items():
            if not isinstance(value, int) or value <= 0:
                raise TransformerReferenceError(f"{name} must be a positive integer")
        self.batch_size = batch_size
        self.kv_heads = kv_heads
        self.max_sequence = max_sequence
        self.head_dim = head_dim
        self.length = 0
        self._k = np.zeros((batch_size, kv_heads, max_sequence, head_dim), dtype=np.float32)
        self._v = np.zeros_like(self._k)
        self._canals = np.full((max_sequence,), -1, dtype=np.int64)
        self._uses_canals: bool | None = None

    def append(self, k: np.ndarray, v: np.ndarray, *, canal_ids: np.ndarray | None = None) -> None:
        key = _float32("kv_cache.k", k)
        value = _float32("kv_cache.v", v)
        if key.ndim != 4 or value.shape != key.shape:
            raise TransformerReferenceError("KV cache K/V must be matching rank-4 tensors")
        if key.shape[:2] != (self.batch_size, self.kv_heads) or key.shape[-1] != self.head_dim:
            raise TransformerReferenceError("KV cache append shape does not match cache contract")
        count = key.shape[2]
        if count <= 0 or self.length + count > self.max_sequence:
            raise TransformerReferenceError("KV cache capacity exceeded")

        uses_canals = canal_ids is not None
        if self._uses_canals is None:
            self._uses_canals = uses_canals
        elif self._uses_canals != uses_canals:
            raise TransformerReferenceError("KV cache canal mode cannot change after first append")
        if canal_ids is not None:
            canals = _finite("kv_cache.canal_ids", canal_ids)
            if canals.dtype.kind not in {"i", "u"} or canals.ndim != 1 or canals.shape[0] != count:
                raise TransformerReferenceError("KV cache canal IDs must be integer shape [sequence]")
            if np.any(canals.astype(np.int64, copy=False) < 0):
                raise TransformerReferenceError("KV cache canal IDs must be non-negative")
        else:
            canals = None

        start = self.length
        end = start + count
        self._k[:, :, start:end, :] = key
        self._v[:, :, start:end, :] = value
        if canals is not None:
            self._canals[start:end] = canals.astype(np.int64, copy=False)
        self.length = end

    def view(self) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
        canals = self._canals[: self.length].copy() if self._uses_canals else None
        return (
            self._k[:, :, : self.length, :].copy(),
            self._v[:, :, : self.length, :].copy(),
            canals,
        )

    def commitment(self) -> str:
        k, v, canals = self.view()
        parts = [array_commitment(k), array_commitment(v)]
        if canals is not None:
            parts.append(array_commitment(canals))
        return hashlib.sha3_256("|".join(parts).encode("ascii")).hexdigest()


@dataclass(frozen=True)
class DecoderBlockConfig:
    hidden_size: int
    num_attention_heads: int
    num_key_value_heads: int
    head_dim: int
    intermediate_size: int
    rms_norm_eps: float = 1e-6
    rotary_theta: float = 10_000.0
    rotary_dim: int | None = None
    attention_mode: Literal["causal", "yarqa"] = "causal"

    def validate(self) -> None:
        for name in (
            "hidden_size",
            "num_attention_heads",
            "num_key_value_heads",
            "head_dim",
            "intermediate_size",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or value <= 0:
                raise TransformerReferenceError(f"{name} must be a positive integer")
        if self.num_attention_heads % self.num_key_value_heads:
            raise TransformerReferenceError("attention heads must be divisible by KV heads")
        if self.num_attention_heads * self.head_dim != self.hidden_size:
            raise TransformerReferenceError("attention heads * head_dim must equal hidden_size")
        if not math.isfinite(self.rms_norm_eps) or self.rms_norm_eps <= 0:
            raise TransformerReferenceError("rms_norm_eps must be finite and positive")
        if not math.isfinite(self.rotary_theta) or self.rotary_theta <= 1.0:
            raise TransformerReferenceError("rotary_theta must be finite and greater than 1")
        dimension = self.head_dim if self.rotary_dim is None else self.rotary_dim
        if not isinstance(dimension, int) or dimension <= 0 or dimension > self.head_dim or dimension % 2:
            raise TransformerReferenceError("rotary_dim must be positive, even and <= head_dim")
        if self.attention_mode not in {"causal", "yarqa"}:
            raise TransformerReferenceError("attention_mode must be causal or yarqa")


@dataclass(frozen=True)
class DecoderBlockWeights:
    attention_norm: np.ndarray
    q_proj: np.ndarray
    k_proj: np.ndarray
    v_proj: np.ndarray
    o_proj: np.ndarray
    ffn_norm: np.ndarray
    gate_proj: np.ndarray
    up_proj: np.ndarray
    down_proj: np.ndarray

    def validate(self, config: DecoderBlockConfig) -> None:
        config.validate()
        expected = {
            "attention_norm": (config.hidden_size,),
            "q_proj": (config.hidden_size, config.num_attention_heads * config.head_dim),
            "k_proj": (config.hidden_size, config.num_key_value_heads * config.head_dim),
            "v_proj": (config.hidden_size, config.num_key_value_heads * config.head_dim),
            "o_proj": (config.num_attention_heads * config.head_dim, config.hidden_size),
            "ffn_norm": (config.hidden_size,),
            "gate_proj": (config.hidden_size, config.intermediate_size),
            "up_proj": (config.hidden_size, config.intermediate_size),
            "down_proj": (config.intermediate_size, config.hidden_size),
        }
        for field in fields(self):
            value = _float32(f"weights.{field.name}", getattr(self, field.name))
            if value.shape != expected[field.name]:
                raise TransformerReferenceError(
                    f"weights.{field.name} shape {value.shape} != {expected[field.name]}"
                )


@dataclass(frozen=True)
class DecoderBlockResult:
    hidden: np.ndarray
    attention_output: np.ndarray
    receipt_chain: ReceiptChain
    cache_length: int
    execution_status: str = "SOFTWARE_EMULATED"
    energy_j: None = None


def _silu(x: np.ndarray) -> np.ndarray:
    data = _float32("silu.input", x)
    clipped = np.clip(data, -80.0, 80.0)
    return np.ascontiguousarray(data / (1.0 + np.exp(-clipped)), dtype=np.float32)


def swiglu_mlp(x: np.ndarray, gate_weight: np.ndarray, up_weight: np.ndarray, down_weight: np.ndarray) -> np.ndarray:
    gate = _linear("swiglu.gate", x, gate_weight)
    up = _linear("swiglu.up", x, up_weight)
    if gate.shape != up.shape:
        raise TransformerReferenceError("SwiGLU gate and up projections must match")
    return _linear("swiglu.down", _silu(gate) * up, down_weight)


def run_decoder_block(
    hidden: np.ndarray,
    weights: DecoderBlockWeights,
    config: DecoderBlockConfig,
    *,
    positions: np.ndarray,
    cache: KVCache | None = None,
    canal_ids: np.ndarray | None = None,
    chain: ReceiptChain | None = None,
) -> DecoderBlockResult:
    """Execute one pre-norm decoder block using deterministic NumPy operations."""

    config.validate()
    weights.validate(config)
    state = _float32("decoder.hidden", hidden)
    if state.ndim != 3 or state.shape[-1] != config.hidden_size:
        raise TransformerReferenceError("hidden must have shape [batch, sequence, hidden_size]")
    batch, sequence, _ = state.shape
    if sequence <= 0:
        raise TransformerReferenceError("decoder sequence must be non-empty")

    pos = _finite("decoder.positions", positions)
    if pos.dtype.kind not in {"i", "u"} or pos.ndim != 1 or pos.shape[0] != sequence:
        raise TransformerReferenceError("positions must be integer shape [sequence]")
    pos64 = pos.astype(np.int64, copy=False)
    if np.any(pos64 < 0):
        raise TransformerReferenceError("positions must be non-negative")

    receipt_chain = chain if chain is not None else ReceiptChain()
    input_commitment = array_commitment(state)
    cache_before = 0 if cache is None else cache.length
    expected_positions = np.arange(cache_before, cache_before + sequence, dtype=np.int64)
    if not np.array_equal(pos64, expected_positions):
        raise TransformerReferenceError("positions must be contiguous and aligned with cache length")
    if cache is not None and (
        cache.batch_size != batch
        or cache.kv_heads != config.num_key_value_heads
        or cache.head_dim != config.head_dim
    ):
        raise TransformerReferenceError("KV cache contract does not match decoder configuration")

    normalized = rms_norm(state, weights.attention_norm, eps=config.rms_norm_eps)
    q = _linear("decoder.q_proj", normalized, weights.q_proj)
    k_new = _linear("decoder.k_proj", normalized, weights.k_proj)
    v_new = _linear("decoder.v_proj", normalized, weights.v_proj)
    q = q.reshape(batch, sequence, config.num_attention_heads, config.head_dim).transpose(0, 2, 1, 3)
    k_new = k_new.reshape(batch, sequence, config.num_key_value_heads, config.head_dim).transpose(0, 2, 1, 3)
    v_new = v_new.reshape(batch, sequence, config.num_key_value_heads, config.head_dim).transpose(0, 2, 1, 3)
    q, k_new = apply_rope(q, k_new, pos64, theta=config.rotary_theta, rotary_dim=config.rotary_dim)

    if config.attention_mode == "yarqa":
        if canal_ids is None:
            raise TransformerReferenceError("YARQA decoder mode requires canal IDs")
        canals = _finite("decoder.canal_ids", canal_ids)
        if canals.dtype.kind not in {"i", "u"} or canals.ndim != 1 or canals.shape[0] != sequence:
            raise TransformerReferenceError("canal IDs must be integer shape [sequence]")
        canals = canals.astype(np.int64, copy=False)
        if np.any(canals < 0):
            raise TransformerReferenceError("canal IDs must be non-negative")
    elif canal_ids is not None:
        raise TransformerReferenceError("canal IDs are only valid in YARQA mode")
    else:
        canals = None

    if cache is None:
        key = k_new
        value = v_new
        key_canals = canals
    else:
        cache.append(k_new, v_new, canal_ids=canals)
        key, value, key_canals = cache.view()

    if config.attention_mode == "yarqa":
        assert canals is not None and key_canals is not None
        attended, probabilities = yarqa_attention(
            q,
            key,
            value,
            query_canal_ids=canals,
            key_canal_ids=key_canals,
            causal=True,
            query_start=cache_before,
        )
    else:
        attended, probabilities = grouped_query_attention(
            q, key, value, causal=True, query_start=cache_before
        )

    attention_flat = attended.transpose(0, 2, 1, 3).reshape(batch, sequence, config.hidden_size)
    attention_output = _linear("decoder.o_proj", attention_flat, weights.o_proj)
    post_attention = np.ascontiguousarray(state + attention_output, dtype=np.float32)
    ffn_input = rms_norm(post_attention, weights.ffn_norm, eps=config.rms_norm_eps)
    mlp_output = swiglu_mlp(ffn_input, weights.gate_proj, weights.up_proj, weights.down_proj)
    output = np.ascontiguousarray(post_attention + mlp_output, dtype=np.float32)

    cache_after = sequence if cache is None else cache.length
    receipt_chain.append(
        "transformer_decoder_block_executed",
        {
            "execution_path": "software_reference_numpy",
            "execution_status": "SOFTWARE_EMULATED",
            "attention_mode": config.attention_mode,
            "batch": batch,
            "sequence": sequence,
            "hidden_size": config.hidden_size,
            "query_heads": config.num_attention_heads,
            "kv_heads": config.num_key_value_heads,
            "head_dim": config.head_dim,
            "intermediate_size": config.intermediate_size,
            "position_start": int(pos64[0]),
            "position_end": int(pos64[-1]),
            "cache_length_before": cache_before,
            "cache_length_after": cache_after,
            "input_commitment": input_commitment,
            "q_commitment": array_commitment(q),
            "k_new_commitment": array_commitment(k_new),
            "v_new_commitment": array_commitment(v_new),
            "attention_probability_commitment": array_commitment(probabilities),
            "attention_output_commitment": array_commitment(attention_output),
            "output_commitment": array_commitment(output),
            "energy_j": None,
            "energy_status": "UNAVAILABLE",
            "hardware_status": "UNAVAILABLE",
        },
    )
    receipt_chain.require_valid()
    return DecoderBlockResult(
        hidden=output,
        attention_output=attention_output,
        receipt_chain=receipt_chain,
        cache_length=cache_after,
    )
