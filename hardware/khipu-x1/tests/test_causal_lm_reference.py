from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np
import pytest

from khipu_x1.causal_lm_mapping import (
    CausalLMMappingError,
    CausalLMTensorNames,
    map_causal_lm,
)
from khipu_x1.causal_lm_reference import (
    CausalLMReferenceError,
    greedy_generate,
    greedy_next_token,
    run_causal_lm,
)
from khipu_x1.safetensors_inventory import inventory_local_model
from khipu_x1.safetensors_mapping import DecoderLayerTensorNames
from khipu_x1.transformer import TransformerSpec


def _spec(*, tied: bool = False, layers: int = 2) -> TransformerSpec:
    return TransformerSpec.from_hf_config(
        {
            "model_type": "qwen2",
            "architectures": ["Qwen2ForCausalLM"],
            "vocab_size": 16,
            "hidden_size": 8,
            "intermediate_size": 12,
            "num_hidden_layers": layers,
            "num_attention_heads": 4,
            "num_key_value_heads": 2,
            "max_position_embeddings": 16,
            "rms_norm_eps": 1e-6,
            "rope_theta": 10000.0,
            "hidden_act": "silu",
            "tie_word_embeddings": tied,
            "attention_bias": False,
            "mlp_bias": False,
        }
    )


def _arrays(spec: TransformerSpec) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(101)
    global_names = CausalLMTensorNames()

    def matrix(shape: tuple[int, ...], scale: float = 0.05) -> np.ndarray:
        return (rng.standard_normal(shape) * scale).astype("<f4")

    arrays: dict[str, np.ndarray] = {
        global_names.embedding: matrix((spec.vocab_size, spec.hidden_size)),
        global_names.final_norm: np.ones((spec.hidden_size,), dtype="<f4"),
    }
    if not spec.tie_word_embeddings:
        arrays[global_names.lm_head] = matrix((spec.vocab_size, spec.hidden_size))

    q_width = spec.num_attention_heads * spec.head_dim
    kv_width = spec.num_key_value_heads * spec.head_dim
    for index in range(spec.num_hidden_layers):
        names = DecoderLayerTensorNames.hf_dense(index)
        arrays.update(
            {
                names.attention_norm: np.ones((spec.hidden_size,), dtype="<f4"),
                names.q_proj: matrix((q_width, spec.hidden_size)),
                names.k_proj: matrix((kv_width, spec.hidden_size)),
                names.v_proj: matrix((kv_width, spec.hidden_size)),
                names.o_proj: matrix((spec.hidden_size, q_width)),
                names.ffn_norm: np.ones((spec.hidden_size,), dtype="<f4"),
                names.gate_proj: matrix((spec.intermediate_size, spec.hidden_size)),
                names.up_proj: matrix((spec.intermediate_size, spec.hidden_size)),
                names.down_proj: matrix((spec.hidden_size, spec.intermediate_size)),
            }
        )
    return arrays


def _write_safetensors(path: Path, arrays: dict[str, np.ndarray]) -> None:
    header: dict[str, object] = {}
    body = bytearray()
    for name in sorted(arrays):
        array = np.ascontiguousarray(arrays[name].astype("<f4", copy=False))
        start = len(body)
        payload = array.tobytes(order="C")
        body.extend(payload)
        header[name] = {
            "dtype": "F32",
            "shape": list(array.shape),
            "data_offsets": [start, len(body)],
        }
    raw = json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")
    raw += b" " * ((8 - len(raw) % 8) % 8)
    path.write_bytes(struct.pack("<Q", len(raw)) + raw + bytes(body))


def _mapped(tmp_path: Path, spec: TransformerSpec):
    _write_safetensors(tmp_path / "model.safetensors", _arrays(spec))
    inventory = inventory_local_model(tmp_path, hash_files=True, hash_tensors=True)
    return map_causal_lm(tmp_path, inventory, spec)


def test_complete_untied_model_maps_runs_and_generates(tmp_path: Path) -> None:
    spec = _spec(tied=False)
    mapped = _mapped(tmp_path, spec)

    assert len(mapped.weights.layers) == 2
    assert len(mapped.bindings) == 2 + 9 * 2 + 1
    assert mapped.receipt_chain.verify()[0]
    assert mapped.report()["tokenizer_status"] == "UNAVAILABLE"

    prompt = np.array([[1, 2, 3]], dtype=np.int64)
    forward = run_causal_lm(
        prompt,
        mapped.weights,
        spec,
        chain=mapped.receipt_chain,
    )
    assert forward.logits.shape == (1, 3, spec.vocab_size)
    assert forward.hidden.shape == (1, 3, spec.hidden_size)
    assert forward.receipt_chain.verify()[0]
    assert len(forward.receipt_chain.events) == 1 + spec.num_hidden_layers + 1

    generated = greedy_generate(
        prompt,
        mapped.weights,
        spec,
        max_new_tokens=2,
        chain=forward.receipt_chain,
    )
    assert generated.token_ids.shape == (1, 5)
    assert generated.generated_token_ids.shape == (1, 2)
    assert generated.receipt_chain.verify()[0]
    assert generated.energy_j is None


def test_tied_model_derives_exact_lm_head_without_separate_tensor(tmp_path: Path) -> None:
    spec = _spec(tied=True, layers=1)
    mapped = _mapped(tmp_path, spec)

    np.testing.assert_array_equal(mapped.weights.lm_head, mapped.weights.embedding.T)
    assert mapped.weights.tie_word_embeddings is True
    assert any(binding.logical_role == "lm_head_tied" for binding in mapped.bindings)
    result = run_causal_lm(np.array([[0, 1]], dtype=np.int64), mapped.weights, spec)
    assert result.logits.shape == (1, 2, spec.vocab_size)


def test_yarqa_complete_model_blocks_cross_canal_influence(tmp_path: Path) -> None:
    spec = _spec(tied=True, layers=1)
    _write_safetensors(tmp_path / "model.safetensors", _arrays(spec))
    inventory = inventory_local_model(tmp_path, hash_files=True, hash_tensors=True)
    mapped = map_causal_lm(tmp_path, inventory, spec, attention_mode="yarqa")

    ids = np.array([[1, 2, 3, 4]], dtype=np.int64)
    canals = np.array([0, 1, 0, 1], dtype=np.int64)
    result = run_causal_lm(
        ids,
        mapped.weights,
        spec,
        attention_mode="yarqa",
        canal_ids=canals,
        chain=mapped.receipt_chain,
    )
    assert result.logits.shape == (1, 4, spec.vocab_size)
    assert result.receipt_chain.verify()[0]


def test_global_mapping_and_resource_bounds_fail_closed(tmp_path: Path) -> None:
    spec = _spec(tied=False, layers=1)
    arrays = _arrays(spec)
    arrays.pop(CausalLMTensorNames().final_norm)
    _write_safetensors(tmp_path / "model.safetensors", arrays)
    inventory = inventory_local_model(tmp_path, hash_files=True, hash_tensors=True)
    with pytest.raises(CausalLMMappingError, match="required tensor is missing"):
        map_causal_lm(tmp_path, inventory, spec)

    other = tmp_path / "layers"
    other.mkdir()
    spec_two = _spec(layers=2)
    _write_safetensors(other / "model.safetensors", _arrays(spec_two))
    inventory = inventory_local_model(other, hash_files=True, hash_tensors=True)
    with pytest.raises(CausalLMMappingError, match="exceeds max_layers"):
        map_causal_lm(other, inventory, spec_two, max_layers=1)


def test_token_and_generation_contracts_fail_closed(tmp_path: Path) -> None:
    spec = _spec(tied=True, layers=1)
    mapped = _mapped(tmp_path, spec)
    with pytest.raises(CausalLMReferenceError, match="outside"):
        run_causal_lm(np.array([[spec.vocab_size]], dtype=np.int64), mapped.weights, spec)
    with pytest.raises(CausalLMReferenceError, match="max_new_tokens"):
        greedy_generate(
            np.array([[1]], dtype=np.int64),
            mapped.weights,
            spec,
            max_new_tokens=0,
        )
    with pytest.raises(CausalLMReferenceError, match="generation budget"):
        greedy_generate(
            np.ones((1, spec.max_position_embeddings), dtype=np.int64),
            mapped.weights,
            spec,
            max_new_tokens=1,
        )
    with pytest.raises(CausalLMReferenceError, match="YARQA mode requires"):
        run_causal_lm(
            np.array([[1, 2]], dtype=np.int64),
            mapped.weights,
            spec,
            attention_mode="yarqa",
        )


def test_greedy_tie_break_is_lowest_index() -> None:
    logits = np.zeros((2, 3, 5), dtype=np.float32)
    logits[0, -1, 1] = 4.0
    logits[0, -1, 3] = 4.0
    logits[1, -1, 2] = 5.0
    np.testing.assert_array_equal(greedy_next_token(logits), np.array([1, 2]))
