from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np
import pytest

from khipu_x1.safetensors_inventory import inventory_local_model
from khipu_x1.safetensors_mapping import (
    DecoderLayerTensorNames,
    SafetensorsMappingError,
    map_decoder_layer,
)
from khipu_x1.transformer import TransformerSpec
from khipu_x1.transformer_reference import run_decoder_block


def _spec(*, attention_bias: bool = False, hidden_act: str = "silu") -> TransformerSpec:
    return TransformerSpec.from_hf_config(
        {
            "model_type": "qwen2",
            "architectures": ["Qwen2ForCausalLM"],
            "vocab_size": 32,
            "hidden_size": 8,
            "intermediate_size": 12,
            "num_hidden_layers": 2,
            "num_attention_heads": 4,
            "num_key_value_heads": 2,
            "max_position_embeddings": 64,
            "rms_norm_eps": 1e-6,
            "rope_theta": 10000.0,
            "hidden_act": hidden_act,
            "tie_word_embeddings": False,
            "attention_bias": attention_bias,
            "mlp_bias": False,
        }
    )


def _layer_arrays(spec: TransformerSpec, *, layer_index: int = 0) -> dict[str, np.ndarray]:
    names = DecoderLayerTensorNames.hf_dense(layer_index)
    rng = np.random.default_rng(23)
    q_width = spec.num_attention_heads * spec.head_dim
    kv_width = spec.num_key_value_heads * spec.head_dim

    def matrix(shape: tuple[int, ...]) -> np.ndarray:
        return (rng.standard_normal(shape) * 0.05).astype("<f4")

    return {
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


def _write_safetensors(
    path: Path,
    arrays: dict[str, np.ndarray],
    *,
    dtype_overrides: dict[str, str] | None = None,
) -> None:
    header: dict[str, object] = {}
    body = bytearray()
    for name in sorted(arrays):
        array = np.ascontiguousarray(arrays[name])
        dtype = (dtype_overrides or {}).get(name, "F32")
        if dtype == "F32":
            payload = array.astype("<f4", copy=False).tobytes(order="C")
        elif dtype == "I8":
            payload = array.astype("i1").tobytes(order="C")
        else:
            raise AssertionError(f"unsupported fixture dtype: {dtype}")
        start = len(body)
        body.extend(payload)
        header[name] = {
            "dtype": dtype,
            "shape": list(array.shape),
            "data_offsets": [start, len(body)],
        }
    raw = json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")
    raw += b" " * ((8 - len(raw) % 8) % 8)
    path.write_bytes(struct.pack("<Q", len(raw)) + raw + bytes(body))


def _inventory_model(tmp_path: Path, arrays: dict[str, np.ndarray]):
    _write_safetensors(tmp_path / "model.safetensors", arrays)
    return inventory_local_model(tmp_path, hash_files=True, hash_tensors=True)


def test_maps_exact_layer_and_runs_reference_block(tmp_path: Path) -> None:
    spec = _spec()
    arrays = _layer_arrays(spec)
    inventory = _inventory_model(tmp_path, arrays)

    mapped = map_decoder_layer(tmp_path, inventory, spec, 0)

    names = DecoderLayerTensorNames.hf_dense(0)
    np.testing.assert_array_equal(mapped.weights.q_proj, arrays[names.q_proj].T)
    np.testing.assert_array_equal(mapped.weights.k_proj, arrays[names.k_proj].T)
    np.testing.assert_array_equal(mapped.weights.down_proj, arrays[names.down_proj].T)
    assert mapped.status == "LOCAL_STATIC_WEIGHT_MAPPING"
    assert len(mapped.bindings) == 9
    assert mapped.receipt_chain.verify()[0]
    assert mapped.report()["content_binding"] == "FULL_FILE_SHA256_REVERIFIED"

    hidden = np.random.default_rng(5).standard_normal((1, 3, 8)).astype(np.float32)
    result = run_decoder_block(
        hidden,
        mapped.weights,
        mapped.config,
        positions=np.arange(3, dtype=np.int64),
        chain=mapped.receipt_chain,
    )
    assert result.hidden.shape == hidden.shape
    assert result.receipt_chain.verify()[0]
    assert len(result.receipt_chain.events) == 2


def test_requires_full_file_binding_and_detects_post_inventory_tamper(tmp_path: Path) -> None:
    spec = _spec()
    arrays = _layer_arrays(spec)
    _write_safetensors(tmp_path / "model.safetensors", arrays)
    weak = inventory_local_model(tmp_path, hash_files=False, hash_tensors=True)
    with pytest.raises(SafetensorsMappingError, match="full-file SHA-256"):
        map_decoder_layer(tmp_path, weak, spec, 0)

    strong = inventory_local_model(tmp_path, hash_files=True, hash_tensors=True)
    model = tmp_path / "model.safetensors"
    changed = bytearray(model.read_bytes())
    changed[-1] ^= 0x01
    model.write_bytes(changed)
    with pytest.raises(SafetensorsMappingError, match="file SHA-256 mismatch"):
        map_decoder_layer(tmp_path, strong, spec, 0)


def test_missing_tensor_and_wrong_shape_fail_closed(tmp_path: Path) -> None:
    spec = _spec()
    names = DecoderLayerTensorNames.hf_dense(0)
    arrays = _layer_arrays(spec)
    arrays.pop(names.down_proj)
    inventory = _inventory_model(tmp_path, arrays)
    with pytest.raises(SafetensorsMappingError, match="required tensor is missing"):
        map_decoder_layer(tmp_path, inventory, spec, 0)

    other = tmp_path / "shape"
    other.mkdir()
    arrays = _layer_arrays(spec)
    arrays[names.q_proj] = np.zeros((7, 8), dtype=np.float32)
    inventory = _inventory_model(other, arrays)
    with pytest.raises(SafetensorsMappingError, match="shape"):
        map_decoder_layer(other, inventory, spec, 0)


def test_unsupported_dtype_and_byte_bound_fail_closed(tmp_path: Path) -> None:
    spec = _spec()
    names = DecoderLayerTensorNames.hf_dense(0)
    arrays = _layer_arrays(spec)
    _write_safetensors(
        tmp_path / "model.safetensors",
        arrays,
        dtype_overrides={names.attention_norm: "I8"},
    )
    inventory = inventory_local_model(tmp_path, hash_files=True, hash_tensors=True)
    with pytest.raises(SafetensorsMappingError, match="unsupported decoder weight dtype"):
        map_decoder_layer(tmp_path, inventory, spec, 0)

    bounded = tmp_path / "bounded"
    bounded.mkdir()
    inventory = _inventory_model(bounded, _layer_arrays(spec))
    with pytest.raises(SafetensorsMappingError, match="total byte bound"):
        map_decoder_layer(bounded, inventory, spec, 0, max_total_loaded_bytes=16)


def test_layer_range_bias_activation_and_names_are_bounded(tmp_path: Path) -> None:
    spec = _spec()
    inventory = _inventory_model(tmp_path, _layer_arrays(spec))
    with pytest.raises(SafetensorsMappingError, match="outside"):
        map_decoder_layer(tmp_path, inventory, spec, 2)

    biased = _spec(attention_bias=True)
    with pytest.raises(SafetensorsMappingError, match="bias-bearing"):
        map_decoder_layer(tmp_path, inventory, biased, 0)

    gelu = _spec(hidden_act="gelu")
    with pytest.raises(SafetensorsMappingError, match="unsupported decoder activation"):
        map_decoder_layer(tmp_path, inventory, gelu, 0)

    duplicate = DecoderLayerTensorNames(
        attention_norm="x",
        q_proj="x",
        k_proj="k",
        v_proj="v",
        o_proj="o",
        ffn_norm="f",
        gate_proj="g",
        up_proj="u",
        down_proj="d",
    )
    with pytest.raises(SafetensorsMappingError, match="unique"):
        map_decoder_layer(tmp_path, inventory, spec, 0, names=duplicate)
