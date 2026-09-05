from __future__ import annotations

import numpy as np
import pytest

from khipu_x1.transformer_reference import (
    DecoderBlockConfig,
    DecoderBlockWeights,
    KVCache,
    TransformerReferenceError,
    apply_rope,
    embedding_lookup,
    grouped_query_attention,
    run_decoder_block,
    yarqa_attention,
)


def _weights(config: DecoderBlockConfig, seed: int = 7) -> DecoderBlockWeights:
    rng = np.random.default_rng(seed)

    def matrix(shape: tuple[int, ...]) -> np.ndarray:
        return (rng.standard_normal(shape) * 0.08).astype(np.float32)

    return DecoderBlockWeights(
        attention_norm=np.ones((config.hidden_size,), dtype=np.float32),
        q_proj=matrix((config.hidden_size, config.num_attention_heads * config.head_dim)),
        k_proj=matrix((config.hidden_size, config.num_key_value_heads * config.head_dim)),
        v_proj=matrix((config.hidden_size, config.num_key_value_heads * config.head_dim)),
        o_proj=matrix((config.num_attention_heads * config.head_dim, config.hidden_size)),
        ffn_norm=np.ones((config.hidden_size,), dtype=np.float32),
        gate_proj=matrix((config.hidden_size, config.intermediate_size)),
        up_proj=matrix((config.hidden_size, config.intermediate_size)),
        down_proj=matrix((config.intermediate_size, config.hidden_size)),
    )


def test_embedding_lookup_is_bounded() -> None:
    table = np.arange(20, dtype=np.float32).reshape(5, 4)
    output = embedding_lookup(table, np.array([[0, 4], [2, 1]], dtype=np.int64))
    assert output.shape == (2, 2, 4)
    np.testing.assert_array_equal(output[0, 1], table[4])
    with pytest.raises(TransformerReferenceError, match="outside"):
        embedding_lookup(table, np.array([5], dtype=np.int64))


def test_rope_position_zero_is_identity_and_preserves_pair_norm() -> None:
    rng = np.random.default_rng(1)
    q = rng.standard_normal((1, 4, 2, 4)).astype(np.float32)
    k = rng.standard_normal((1, 2, 2, 4)).astype(np.float32)
    qr, kr = apply_rope(q, k, np.array([0, 3], dtype=np.int64))
    np.testing.assert_allclose(qr[:, :, 0], q[:, :, 0], rtol=0, atol=1e-7)
    np.testing.assert_allclose(kr[:, :, 0], k[:, :, 0], rtol=0, atol=1e-7)
    np.testing.assert_allclose(
        np.sum(np.square(qr[..., :4]), axis=-1),
        np.sum(np.square(q[..., :4]), axis=-1),
        rtol=1e-6,
        atol=1e-6,
    )


def test_gqa_causal_attention_blocks_future_values() -> None:
    q = np.ones((1, 4, 3, 2), dtype=np.float32)
    k = np.ones((1, 2, 3, 2), dtype=np.float32)
    v = np.arange(12, dtype=np.float32).reshape(1, 2, 3, 2)
    base, probabilities = grouped_query_attention(q, k, v, causal=True)
    changed = v.copy()
    changed[:, :, 2, :] += 10_000
    other, _ = grouped_query_attention(q, k, changed, causal=True)
    np.testing.assert_allclose(base[:, :, :2], other[:, :, :2], rtol=0, atol=1e-6)
    assert probabilities.shape == (1, 4, 3, 3)
    assert np.all(probabilities[:, :, 0, 1:] == 0)


def test_yarqa_blocks_cross_canal_influence() -> None:
    q = np.ones((1, 2, 4, 2), dtype=np.float32)
    k = np.ones((1, 1, 4, 2), dtype=np.float32)
    v = np.arange(8, dtype=np.float32).reshape(1, 1, 4, 2)
    canals = np.array([0, 1, 0, 1], dtype=np.int64)
    base, probabilities = yarqa_attention(
        q, k, v, query_canal_ids=canals, key_canal_ids=canals
    )
    changed = v.copy()
    changed[:, :, canals == 1, :] += 10_000
    other, _ = yarqa_attention(
        q, k, changed, query_canal_ids=canals, key_canal_ids=canals
    )
    np.testing.assert_allclose(base[:, :, canals == 0], other[:, :, canals == 0], atol=1e-6)
    assert np.all(probabilities[:, :, canals == 0][:, :, :, canals == 1] == 0)


def test_incremental_kv_cache_matches_full_causal_block() -> None:
    config = DecoderBlockConfig(
        hidden_size=8,
        num_attention_heads=4,
        num_key_value_heads=2,
        head_dim=2,
        intermediate_size=12,
    )
    weights = _weights(config)
    hidden = np.random.default_rng(11).standard_normal((1, 4, 8)).astype(np.float32)

    full = run_decoder_block(
        hidden, weights, config, positions=np.arange(4, dtype=np.int64)
    )

    cache = KVCache(batch_size=1, kv_heads=2, max_sequence=4, head_dim=2)
    pieces = []
    chain = None
    for index in range(4):
        result = run_decoder_block(
            hidden[:, index : index + 1],
            weights,
            config,
            positions=np.array([index], dtype=np.int64),
            cache=cache,
            chain=chain,
        )
        chain = result.receipt_chain
        pieces.append(result.hidden)
    incremental = np.concatenate(pieces, axis=1)

    np.testing.assert_allclose(full.hidden, incremental, rtol=2e-5, atol=2e-5)
    assert cache.length == 4
    assert chain is not None and chain.verify()[0]
    assert len(chain.events) == 4
    assert result.energy_j is None
    assert result.execution_status == "SOFTWARE_EMULATED"


def test_decoder_rejects_invalid_contracts() -> None:
    config = DecoderBlockConfig(
        hidden_size=8,
        num_attention_heads=3,
        num_key_value_heads=2,
        head_dim=2,
        intermediate_size=12,
    )
    with pytest.raises(TransformerReferenceError, match="divisible"):
        config.validate()

    cache = KVCache(batch_size=1, kv_heads=1, max_sequence=1, head_dim=2)
    cache.append(
        np.zeros((1, 1, 1, 2), dtype=np.float32),
        np.zeros((1, 1, 1, 2), dtype=np.float32),
    )
    with pytest.raises(TransformerReferenceError, match="capacity"):
        cache.append(
            np.zeros((1, 1, 1, 2), dtype=np.float32),
            np.zeros((1, 1, 1, 2), dtype=np.float32),
        )
