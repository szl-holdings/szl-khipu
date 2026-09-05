from __future__ import annotations

import json
from dataclasses import replace

import numpy as np
import pytest

from khipu_x1 import lower_graph
from khipu_x1.quantization import (
    QuantizationError,
    dequantize_symmetric_int8,
    quantize_symmetric_int8,
)
from khipu_x1.transformer import (
    TargetBudget,
    TransformerImportError,
    TransformerSpec,
    assess_target_budget,
    build_projection_probe_graph,
    inspect_transformer_config,
)


def tiny_config() -> dict[str, object]:
    return {
        "model_type": "khipu-test",
        "architectures": ["KhipuForCausalLM"],
        "vocab_size": 32,
        "hidden_size": 8,
        "intermediate_size": 16,
        "num_hidden_layers": 2,
        "num_attention_heads": 2,
        "num_key_value_heads": 1,
        "max_position_embeddings": 128,
        "rms_norm_eps": 1e-5,
        "rope_theta": 10000.0,
        "tie_word_embeddings": True,
        "attention_bias": False,
        "mlp_bias": False,
    }


def test_symmetric_int8_quantization_is_deterministic() -> None:
    source = np.array([[-2.0, -0.5, 0.0, 0.5, 2.0]], dtype=np.float32)
    first = quantize_symmetric_int8(source)
    second = quantize_symmetric_int8(source.copy())
    np.testing.assert_array_equal(first.values, second.values)
    np.testing.assert_array_equal(first.scales, second.scales)
    assert first.values.tolist() == [[-127, -32, 0, 32, 127]]
    assert first.receipt_digest == second.receipt_digest
    restored = dequantize_symmetric_int8(first)
    assert restored.shape == source.shape
    assert np.max(np.abs(restored - source)) == pytest.approx(first.max_abs_error)
    assert set(first.payloads("probe")) == {
        "weights/probe.int8.bin",
        "weights/probe.scale.f32le.bin",
        "weights/probe.quant.json",
    }


def test_per_axis_and_zero_range_are_explicit() -> None:
    source = np.array([[0.0, 0.0], [1.0, -1.0]], dtype=np.float32)
    result = quantize_symmetric_int8(source, axis=0)
    assert result.scales.shape == (2,)
    assert result.zero_range_count == 1
    np.testing.assert_array_equal(result.values[0], np.array([0, 0], dtype=np.int8))
    np.testing.assert_allclose(dequantize_symmetric_int8(result), source, atol=1e-6)


def test_quantization_rejects_nonfinite_and_tampered_commitments() -> None:
    with pytest.raises(QuantizationError, match="non-finite"):
        quantize_symmetric_int8(np.array([[np.nan]], dtype=np.float32))
    result = quantize_symmetric_int8(np.array([[1.0, 2.0]], dtype=np.float32))
    tampered = replace(result, values=result.values.copy())
    tampered.values[0, 0] = 0
    with pytest.raises(QuantizationError, match="commitment mismatch"):
        dequantize_symmetric_int8(tampered)


def test_transformer_config_estimates_and_blocks_missing_ops() -> None:
    config = tiny_config()
    spec = TransformerSpec.from_hf_config(config)
    # embedding 256 + 2 * (attention 192 + MLP 384 + norms 16) + final norm 8
    assert spec.hidden_act == "silu"
    assert spec.parameter_estimate == 1448
    assert spec.ideal_weight_bytes(8) == 1448
    assert spec.kv_cache_bytes(context_tokens=16, bytes_per_element=2) == 512

    report = inspect_transformer_config(config, context_tokens=16)
    assert report.status == "BLOCKED_UNSUPPORTED_DEVICE_OPS"
    assert report.implemented_device_ops == (
        "GEMM_INT8",
        "RMSNORM",
        "SHA3_COMMIT",
    )
    assert "ATTN_CAUSAL" in report.missing_device_ops
    assert "ADD" in report.missing_device_ops
    assert "RECEIPT_EMIT" in report.missing_device_ops
    assert report.as_dict()["performance_status"] == "UNMEASURED"


def test_yarqa_mode_substitutes_attention_requirement() -> None:
    report = inspect_transformer_config(
        tiny_config(), context_tokens=16, attention_mode="yarqa"
    )
    assert "ATTN_YARQA" in report.required_device_ops
    assert "ATTN_CAUSAL" not in report.required_device_ops


def test_transformer_config_rejects_invalid_head_topology() -> None:
    config = tiny_config()
    config["num_attention_heads"] = 3
    with pytest.raises(TransformerImportError, match="divide evenly"):
        TransformerSpec.from_hf_config(config)


def test_projection_probe_is_lowerable_but_not_full_model() -> None:
    spec = TransformerSpec.from_hf_config(tiny_config())
    graph = build_projection_probe_graph(spec)
    lowered = lower_graph(
        graph,
        model_digest=spec.source_config_digest,
        policy_digest=spec.source_config_digest,
    )
    assert graph.name == "transformer_projection_probe"
    assert len(lowered.descriptors) == 3
    assert [item.opcode.value for item in lowered.descriptors] == [
        "GEMM_INT8",
        "RMSNORM",
        "SHA3_COMMIT",
    ]


def test_target_budget_is_a_labeled_analytic_worksheet() -> None:
    report = inspect_transformer_config(tiny_config(), context_tokens=16)
    target = TargetBudget(
        name="candidate-fpga",
        external_memory_bytes=4096,
        on_chip_sram_bytes=512,
        sustainable_memory_bandwidth_bytes_s=1024,
        reserved_memory_bytes=256,
    )
    assessment = assess_target_budget(report, target)
    assert assessment["fits_external_memory"] is True
    assert assessment["stream_bound_status"] == "ANALYTIC_LOWER_BOUND_NOT_PERFORMANCE"
    assert assessment["hardware_status"] == "DATASHEET_INPUT_NOT_MEASURED_BY_SZL"

    # Report remains canonical JSON serializable for receipts and package metadata.
    json.dumps(report.as_dict(), sort_keys=True, allow_nan=False)


def test_transformer_config_rejects_non_json_extension_data() -> None:
    config = tiny_config()
    config["untrusted_extension"] = {"not", "json"}
    with pytest.raises(TransformerImportError, match="canonical JSON"):
        TransformerSpec.from_hf_config(config)
