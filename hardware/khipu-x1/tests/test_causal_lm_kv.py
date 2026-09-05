from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from khipu_x1.causal_lm_kv import (
    CausalLMKVError,
    decode_causal_lm_step,
    greedy_generate_cached,
    prefill_causal_lm,
)
from khipu_x1.causal_lm_reference import (
    CausalLMWeights,
    greedy_generate,
    run_causal_lm,
)
from khipu_x1.transformer import TransformerSpec
from khipu_x1.transformer_reference import DecoderBlockWeights


def _spec(*, layers: int = 2) -> TransformerSpec:
    return TransformerSpec.from_hf_config(
        {
            "model_type": "qwen2",
            "architectures": ["Qwen2ForCausalLM"],
            "vocab_size": 19,
            "hidden_size": 8,
            "intermediate_size": 12,
            "num_hidden_layers": layers,
            "num_attention_heads": 4,
            "num_key_value_heads": 2,
            "max_position_embeddings": 16,
            "rms_norm_eps": 1e-6,
            "rope_theta": 10000.0,
            "hidden_act": "silu",
            "tie_word_embeddings": False,
            "attention_bias": False,
            "mlp_bias": False,
        }
    )


def _weights(spec: TransformerSpec) -> CausalLMWeights:
    rng = np.random.default_rng(707)

    def matrix(shape: tuple[int, ...], scale: float = 0.08) -> np.ndarray:
        return (rng.standard_normal(shape) * scale).astype(np.float32)

    layers = []
    q_width = spec.num_attention_heads * spec.head_dim
    kv_width = spec.num_key_value_heads * spec.head_dim
    for _ in range(spec.num_hidden_layers):
        layers.append(
            DecoderBlockWeights(
                attention_norm=np.ones((spec.hidden_size,), dtype=np.float32),
                q_proj=matrix((spec.hidden_size, q_width)),
                k_proj=matrix((spec.hidden_size, kv_width)),
                v_proj=matrix((spec.hidden_size, kv_width)),
                o_proj=matrix((q_width, spec.hidden_size)),
                ffn_norm=np.ones((spec.hidden_size,), dtype=np.float32),
                gate_proj=matrix((spec.hidden_size, spec.intermediate_size)),
                up_proj=matrix((spec.hidden_size, spec.intermediate_size)),
                down_proj=matrix((spec.intermediate_size, spec.hidden_size)),
            )
        )
    return CausalLMWeights(
        embedding=matrix((spec.vocab_size, spec.hidden_size), scale=0.2),
        layers=tuple(layers),
        final_norm=np.ones((spec.hidden_size,), dtype=np.float32),
        lm_head=matrix((spec.hidden_size, spec.vocab_size), scale=0.2),
        tie_word_embeddings=False,
    )


def test_prefill_matches_complete_forward_and_freezes_state() -> None:
    spec = _spec()
    weights = _weights(spec)
    prompt = np.array([[1, 2, 3, 4]], dtype=np.int64)

    full = run_causal_lm(prompt, weights, spec)
    cached = prefill_causal_lm(prompt, weights, spec)

    np.testing.assert_allclose(cached.logits, full.logits, rtol=2e-5, atol=2e-5)
    np.testing.assert_allclose(cached.hidden, full.hidden, rtol=2e-5, atol=2e-5)
    assert cached.state.sequence_length == 4
    assert cached.state.receipt_chain.verify()[0]
    assert cached.state.receipt_head == cached.state.receipt_chain.head
    for layer in cached.state.layers:
        assert layer.k.flags.writeable is False
        assert layer.v.flags.writeable is False
        assert layer.length == 4


def test_single_token_decode_matches_full_recomputation_without_mutating_prior_state() -> None:
    spec = _spec()
    weights = _weights(spec)
    prompt = np.array([[1, 2, 3]], dtype=np.int64)
    prefill = prefill_causal_lm(prompt, weights, spec)
    prior_depth = len(prefill.state.receipt_chain.events)
    prior_digest = prefill.state.state_digest
    prior_head = prefill.state.receipt_head

    step = decode_causal_lm_step(
        np.array([[4]], dtype=np.int64),
        prefill.state,
        weights,
        spec,
    )
    full = run_causal_lm(
        np.array([[1, 2, 3, 4]], dtype=np.int64),
        weights,
        spec,
    )

    np.testing.assert_allclose(
        step.logits[:, 0, :],
        full.logits[:, -1, :],
        rtol=3e-5,
        atol=3e-5,
    )
    assert step.state.sequence_length == 4
    assert prefill.state.sequence_length == 3
    assert prefill.state.state_digest == prior_digest
    assert prefill.state.receipt_head == prior_head
    assert len(prefill.state.receipt_chain.events) == prior_depth
    assert step.state.receipt_chain.verify()[0]


def test_cached_generation_matches_full_recomputation() -> None:
    spec = _spec(layers=1)
    weights = _weights(spec)
    prompt = np.array([[2, 5, 7]], dtype=np.int64)

    full = greedy_generate(prompt, weights, spec, max_new_tokens=3)
    cached = greedy_generate_cached(prompt, weights, spec, max_new_tokens=3)

    np.testing.assert_array_equal(cached.token_ids, full.token_ids)
    np.testing.assert_array_equal(
        cached.generated_token_ids,
        full.generated_token_ids,
    )
    assert cached.state.sequence_length == prompt.shape[1] + 3
    assert cached.state.receipt_chain.verify()[0]
    assert cached.energy_j is None


def test_yarqa_cached_decode_matches_full_sequence() -> None:
    spec = _spec(layers=1)
    weights = _weights(spec)
    prompt = np.array([[1, 2, 3]], dtype=np.int64)
    prompt_canals = np.array([0, 1, 0], dtype=np.int64)
    prefill = prefill_causal_lm(
        prompt,
        weights,
        spec,
        attention_mode="yarqa",
        canal_ids=prompt_canals,
    )
    step = decode_causal_lm_step(
        np.array([[4]], dtype=np.int64),
        prefill.state,
        weights,
        spec,
        canal_id=0,
    )
    full = run_causal_lm(
        np.array([[1, 2, 3, 4]], dtype=np.int64),
        weights,
        spec,
        attention_mode="yarqa",
        canal_ids=np.array([0, 1, 0, 0], dtype=np.int64),
    )
    np.testing.assert_allclose(
        step.logits[:, 0, :],
        full.logits[:, -1, :],
        rtol=3e-5,
        atol=3e-5,
    )
    assert step.state.layers[0].canal_ids is not None
    np.testing.assert_array_equal(
        step.state.layers[0].canal_ids,
        np.array([0, 1, 0, 0], dtype=np.int64),
    )


def test_state_digest_weight_and_receipt_bindings_fail_closed() -> None:
    spec = _spec(layers=1)
    weights = _weights(spec)
    prefill = prefill_causal_lm(np.array([[1, 2]], dtype=np.int64), weights, spec)

    with pytest.raises(CausalLMKVError, match="state digest mismatch"):
        decode_causal_lm_step(
            np.array([[3]], dtype=np.int64),
            replace(prefill.state, state_digest="0" * 64),
            weights,
            spec,
        )

    changed_weights = replace(
        weights,
        embedding=np.ascontiguousarray(weights.embedding + 0.001),
    )
    with pytest.raises(CausalLMKVError, match="weight manifest"):
        decode_causal_lm_step(
            np.array([[3]], dtype=np.int64),
            prefill.state,
            changed_weights,
            spec,
        )

    with pytest.raises(CausalLMKVError, match="receipt-head"):
        decode_causal_lm_step(
            np.array([[3]], dtype=np.int64),
            replace(prefill.state, receipt_head="0" * 64),
            weights,
            spec,
        )


def test_step_canal_capacity_and_generation_contracts_fail_closed() -> None:
    spec = _spec(layers=1)
    weights = _weights(spec)
    prefill = prefill_causal_lm(np.array([[1, 2]], dtype=np.int64), weights, spec)
    with pytest.raises(CausalLMKVError, match="exactly one token"):
        decode_causal_lm_step(
            np.array([[3, 4]], dtype=np.int64),
            prefill.state,
            weights,
            spec,
        )

    yarqa = prefill_causal_lm(
        np.array([[1, 2]], dtype=np.int64),
        weights,
        spec,
        attention_mode="yarqa",
        canal_ids=np.array([0, 1], dtype=np.int64),
    )
    with pytest.raises(CausalLMKVError, match="canal_id"):
        decode_causal_lm_step(
            np.array([[3]], dtype=np.int64),
            yarqa.state,
            weights,
            spec,
        )

    full_prompt = np.ones((1, spec.max_position_embeddings), dtype=np.int64)
    full_state = prefill_causal_lm(full_prompt, weights, spec).state
    with pytest.raises(CausalLMKVError, match="reached"):
        decode_causal_lm_step(
            np.array([[1]], dtype=np.int64),
            full_state,
            weights,
            spec,
        )
    with pytest.raises(CausalLMKVError, match="generation budget"):
        greedy_generate_cached(
            full_prompt,
            weights,
            spec,
            max_new_tokens=1,
        )
