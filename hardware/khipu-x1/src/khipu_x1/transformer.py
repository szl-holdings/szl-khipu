"""Bounded Hugging Face-style transformer configuration inspection.

The importer reads a plain configuration mapping only. It performs no network
access, dynamic imports or model-code execution. A readiness report is not a
model conversion and does not establish that KHIPU-X1 can execute the model.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Any, Mapping

from .graph import BufferSpec, GraphNode, GraphPlan
from .kids import Opcode, canonical_json_bytes

_MODEL_TYPE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_DEVICE_OPS_INT8 = (
    "EMBED_GATHER",
    "RMSNORM",
    "GEMM_INT8",
    "ROPE",
    "ATTN_CAUSAL",
    "KV_GATHER",
    "KV_SCATTER",
    "ADD",
    "SILU",
    "MUL",
    "SHA3_COMMIT",
    "RECEIPT_EMIT",
)
_CURRENT_DEVICE_OPS = ("GEMM_INT8", "RMSNORM", "SHA3_COMMIT")
_HOST_OPS = ("TOKENIZE", "LOGITS_PROCESS", "SAMPLE", "DETOKENIZE")


class TransformerImportError(ValueError):
    """Raised when a transformer configuration is malformed or unsupported."""


def _bounded_int(
    config: Mapping[str, Any],
    name: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    value = config.get(name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise TransformerImportError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise TransformerImportError(f"{name} must be in [{minimum}, {maximum}]")
    return value


def _finite_float(
    config: Mapping[str, Any],
    name: str,
    default: float,
    *,
    positive: bool,
) -> float:
    value = config.get(name, default)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TransformerImportError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0.0):
        raise TransformerImportError(f"{name} must be finite and positive")
    return result


def _bool(config: Mapping[str, Any], name: str, default: bool) -> bool:
    value = config.get(name, default)
    if not isinstance(value, bool):
        raise TransformerImportError(f"{name} must be boolean")
    return value


@dataclass(frozen=True)
class TransformerSpec:
    model_type: str
    vocab_size: int
    hidden_size: int
    intermediate_size: int
    num_hidden_layers: int
    num_attention_heads: int
    num_key_value_heads: int
    head_dim: int
    max_position_embeddings: int
    rms_norm_eps: float
    rope_theta: float
    tie_word_embeddings: bool
    attention_bias: bool
    mlp_bias: bool
    architectures: tuple[str, ...]
    source_config_digest: str

    @classmethod
    def from_hf_config(cls, config: Mapping[str, Any]) -> "TransformerSpec":
        if not isinstance(config, Mapping):
            raise TransformerImportError("configuration must be a mapping")
        if len(config) > 4096 or any(not isinstance(key, str) for key in config):
            raise TransformerImportError("configuration keys must be bounded strings")

        model_type = config.get("model_type")
        if not isinstance(model_type, str) or not _MODEL_TYPE.fullmatch(model_type):
            raise TransformerImportError("model_type must be a bounded identifier")

        vocab = _bounded_int(
            config,
            "vocab_size",
            minimum=1,
            maximum=10_000_000,
        )
        hidden = _bounded_int(
            config,
            "hidden_size",
            minimum=1,
            maximum=131_072,
        )
        intermediate = _bounded_int(
            config,
            "intermediate_size",
            minimum=1,
            maximum=1_048_576,
        )
        layers = _bounded_int(
            config,
            "num_hidden_layers",
            minimum=1,
            maximum=1_024,
        )
        heads = _bounded_int(
            config,
            "num_attention_heads",
            minimum=1,
            maximum=16_384,
        )

        kv_heads_raw = config.get("num_key_value_heads", heads)
        if not isinstance(kv_heads_raw, int) or isinstance(kv_heads_raw, bool):
            raise TransformerImportError("num_key_value_heads must be an integer")
        kv_heads = int(kv_heads_raw)
        if not 1 <= kv_heads <= heads or heads % kv_heads != 0:
            raise TransformerImportError(
                "num_key_value_heads must divide num_attention_heads"
            )

        head_dim_raw = config.get("head_dim")
        if head_dim_raw is None:
            if hidden % heads != 0:
                raise TransformerImportError(
                    "hidden_size must divide evenly by num_attention_heads"
                )
            head_dim = hidden // heads
        elif isinstance(head_dim_raw, int) and not isinstance(head_dim_raw, bool):
            head_dim = head_dim_raw
        else:
            raise TransformerImportError(
                "head_dim must be an integer when supplied"
            )
        if not 1 <= head_dim <= 16_384 or hidden != heads * head_dim:
            raise TransformerImportError(
                "hidden_size must equal num_attention_heads * head_dim"
            )

        context = _bounded_int(
            config,
            "max_position_embeddings",
            minimum=1,
            maximum=100_000_000,
        )
        eps = _finite_float(config, "rms_norm_eps", 1e-6, positive=True)
        rope_theta = _finite_float(
            config,
            "rope_theta",
            10_000.0,
            positive=True,
        )
        tied = _bool(config, "tie_word_embeddings", False)
        attention_bias = _bool(config, "attention_bias", False)
        mlp_bias = _bool(config, "mlp_bias", False)

        architectures_raw = config.get("architectures", [])
        if (
            not isinstance(architectures_raw, list)
            or len(architectures_raw) > 256
            or any(
                not isinstance(item, str) or not item or len(item) > 128
                for item in architectures_raw
            )
        ):
            raise TransformerImportError(
                "architectures must be a bounded string list"
            )

        try:
            config_bytes = canonical_json_bytes(dict(config))
        except (TypeError, ValueError) as exc:
            raise TransformerImportError(
                f"configuration is not canonical JSON data: {exc}"
            ) from exc
        if len(config_bytes) > 1_048_576:
            raise TransformerImportError("configuration exceeds the 1 MiB bound")
        digest = hashlib.sha256(config_bytes).hexdigest()

        return cls(
            model_type=model_type,
            vocab_size=vocab,
            hidden_size=hidden,
            intermediate_size=intermediate,
            num_hidden_layers=layers,
            num_attention_heads=heads,
            num_key_value_heads=kv_heads,
            head_dim=head_dim,
            max_position_embeddings=context,
            rms_norm_eps=eps,
            rope_theta=rope_theta,
            tie_word_embeddings=tied,
            attention_bias=attention_bias,
            mlp_bias=mlp_bias,
            architectures=tuple(architectures_raw),
            source_config_digest=digest,
        )

    @property
    def parameter_estimate(self) -> int:
        """Return a Llama-like estimate, not an inspected weight count."""

        hidden = self.hidden_size
        kv_width = self.num_key_value_heads * self.head_dim
        embedding = self.vocab_size * hidden
        attention_weights = (
            hidden * hidden
            + hidden * kv_width
            + hidden * kv_width
            + hidden * hidden
        )
        mlp_weights = 3 * hidden * self.intermediate_size
        norms = 2 * hidden
        attention_biases = (
            2 * hidden + 2 * kv_width if self.attention_bias else 0
        )
        mlp_biases = (
            2 * self.intermediate_size + hidden if self.mlp_bias else 0
        )
        per_layer = (
            attention_weights
            + mlp_weights
            + norms
            + attention_biases
            + mlp_biases
        )
        final_norm = hidden
        untied_head = 0 if self.tie_word_embeddings else self.vocab_size * hidden
        return (
            embedding
            + self.num_hidden_layers * per_layer
            + final_norm
            + untied_head
        )

    def ideal_weight_bytes(self, bits_per_parameter: int) -> int:
        if (
            not isinstance(bits_per_parameter, int)
            or bits_per_parameter not in {4, 8, 16, 32}
        ):
            raise TransformerImportError(
                "bits_per_parameter must be one of 4, 8, 16, 32"
            )
        return (self.parameter_estimate * bits_per_parameter + 7) // 8

    def kv_cache_bytes(
        self,
        *,
        context_tokens: int,
        batch_size: int = 1,
        bytes_per_element: int = 2,
    ) -> int:
        for name, value, maximum in (
            ("context_tokens", context_tokens, self.max_position_embeddings),
            ("batch_size", batch_size, 65_536),
            ("bytes_per_element", bytes_per_element, 8),
        ):
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or not 1 <= value <= maximum
            ):
                raise TransformerImportError(f"{name} is outside its bound")
        return (
            2
            * self.num_hidden_layers
            * self.num_key_value_heads
            * self.head_dim
            * context_tokens
            * batch_size
            * bytes_per_element
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_type": self.model_type,
            "architectures": list(self.architectures),
            "vocab_size": self.vocab_size,
            "hidden_size": self.hidden_size,
            "intermediate_size": self.intermediate_size,
            "num_hidden_layers": self.num_hidden_layers,
            "num_attention_heads": self.num_attention_heads,
            "num_key_value_heads": self.num_key_value_heads,
            "head_dim": self.head_dim,
            "max_position_embeddings": self.max_position_embeddings,
            "rms_norm_eps": self.rms_norm_eps,
            "rope_theta": self.rope_theta,
            "tie_word_embeddings": self.tie_word_embeddings,
            "attention_bias": self.attention_bias,
            "mlp_bias": self.mlp_bias,
            "source_config_digest": self.source_config_digest,
        }


@dataclass(frozen=True)
class TransformerReadinessReport:
    spec: TransformerSpec
    attention_mode: str
    context_tokens: int
    batch_size: int
    parameter_estimate: int
    weight_bytes: Mapping[str, int]
    kv_cache_bytes: Mapping[str, int]
    required_device_ops: tuple[str, ...]
    implemented_device_ops: tuple[str, ...]
    missing_device_ops: tuple[str, ...]
    host_ops: tuple[str, ...]
    status: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "khipu-transformer-readiness/v0.1",
            "truth": "CONFIG_INSPECTION_AND_ANALYTIC_ESTIMATE",
            "spec": self.spec.as_dict(),
            "attention_mode": self.attention_mode,
            "context_tokens": self.context_tokens,
            "batch_size": self.batch_size,
            "parameter_estimate": self.parameter_estimate,
            "parameter_count_status": "ANALYTIC_ESTIMATE_NOT_WEIGHT_INSPECTION",
            "weight_bytes": dict(self.weight_bytes),
            "weight_memory_status": (
                "IDEAL_PAYLOAD_ONLY_EXCLUDES_SCALES_METADATA_RUNTIME"
            ),
            "kv_cache_bytes": dict(self.kv_cache_bytes),
            "required_device_ops": list(self.required_device_ops),
            "implemented_device_ops": list(self.implemented_device_ops),
            "missing_device_ops": list(self.missing_device_ops),
            "host_ops": list(self.host_ops),
            "status": self.status,
            "hardware_status": "UNAVAILABLE",
            "performance_status": "UNMEASURED",
        }

    @property
    def digest(self) -> str:
        return hashlib.sha256(canonical_json_bytes(self.as_dict())).hexdigest()


@dataclass(frozen=True)
class TargetBudget:
    name: str
    external_memory_bytes: int
    on_chip_sram_bytes: int
    sustainable_memory_bandwidth_bytes_s: int
    reserved_memory_bytes: int = 0

    def validate(self) -> None:
        if not isinstance(self.name, str) or not _MODEL_TYPE.fullmatch(self.name):
            raise TransformerImportError(
                "target name must be a bounded identifier"
            )
        for field_name, value in (
            ("external_memory_bytes", self.external_memory_bytes),
            ("on_chip_sram_bytes", self.on_chip_sram_bytes),
            (
                "sustainable_memory_bandwidth_bytes_s",
                self.sustainable_memory_bandwidth_bytes_s,
            ),
            ("reserved_memory_bytes", self.reserved_memory_bytes),
        ):
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise TransformerImportError(
                    f"{field_name} must be a non-negative integer"
                )
        if (
            self.external_memory_bytes <= 0
            or self.sustainable_memory_bandwidth_bytes_s <= 0
        ):
            raise TransformerImportError(
                "target external memory and bandwidth must be positive"
            )
        if self.reserved_memory_bytes >= self.external_memory_bytes:
            raise TransformerImportError(
                "reserved memory leaves no usable external memory"
            )


def inspect_transformer_config(
    config: Mapping[str, Any],
    *,
    context_tokens: int,
    batch_size: int = 1,
    attention_mode: str = "causal",
) -> TransformerReadinessReport:
    spec = TransformerSpec.from_hf_config(config)
    if attention_mode not in {"causal", "yarqa"}:
        raise TransformerImportError("attention_mode must be causal or yarqa")
    if not isinstance(context_tokens, int) or isinstance(context_tokens, bool):
        raise TransformerImportError("context_tokens must be an integer")
    if not 1 <= context_tokens <= spec.max_position_embeddings:
        raise TransformerImportError("context_tokens exceeds the model bound")
    if (
        not isinstance(batch_size, int)
        or isinstance(batch_size, bool)
        or not 1 <= batch_size <= 65_536
    ):
        raise TransformerImportError("batch_size is outside its bound")

    required = list(_DEVICE_OPS_INT8)
    required[required.index("ATTN_CAUSAL")] = (
        "ATTN_CAUSAL" if attention_mode == "causal" else "ATTN_YARQA"
    )
    required_tuple = tuple(required)
    missing = tuple(
        operation
        for operation in required_tuple
        if operation not in _CURRENT_DEVICE_OPS
    )
    status = (
        "READY_FOR_SOFTWARE_LOWERING"
        if not missing
        else "BLOCKED_UNSUPPORTED_DEVICE_OPS"
    )

    return TransformerReadinessReport(
        spec=spec,
        attention_mode=attention_mode,
        context_tokens=context_tokens,
        batch_size=batch_size,
        parameter_estimate=spec.parameter_estimate,
        weight_bytes={
            "fp32": spec.ideal_weight_bytes(32),
            "bf16": spec.ideal_weight_bytes(16),
            "int8_ideal": spec.ideal_weight_bytes(8),
            "int4_ideal": spec.ideal_weight_bytes(4),
        },
        kv_cache_bytes={
            "bf16": spec.kv_cache_bytes(
                context_tokens=context_tokens,
                batch_size=batch_size,
                bytes_per_element=2,
            ),
            "int8_ideal": spec.kv_cache_bytes(
                context_tokens=context_tokens,
                batch_size=batch_size,
                bytes_per_element=1,
            ),
        },
        required_device_ops=required_tuple,
        implemented_device_ops=_CURRENT_DEVICE_OPS,
        missing_device_ops=missing,
        host_ops=_HOST_OPS,
        status=status,
    )


def assess_target_budget(
    report: TransformerReadinessReport,
    target: TargetBudget,
    *,
    weight_format: str = "int8_ideal",
    kv_format: str = "bf16",
) -> dict[str, Any]:
    target.validate()
    if (
        weight_format not in report.weight_bytes
        or kv_format not in report.kv_cache_bytes
    ):
        raise TransformerImportError(
            "requested memory format is absent from the report"
        )
    weights = report.weight_bytes[weight_format]
    kv = report.kv_cache_bytes[kv_format]
    usable = target.external_memory_bytes - target.reserved_memory_bytes
    total = weights + kv
    minimum_stream_seconds = (
        weights / target.sustainable_memory_bandwidth_bytes_s
    )
    return {
        "schema": "khipu-target-budget/v0.1",
        "target": target.name,
        "source_report_digest": report.digest,
        "weight_format": weight_format,
        "kv_format": kv_format,
        "usable_external_memory_bytes": usable,
        "estimated_weight_bytes": weights,
        "estimated_kv_cache_bytes": kv,
        "estimated_total_bytes": total,
        "memory_headroom_bytes": usable - total,
        "fits_external_memory": total <= usable,
        "minimum_full_weight_stream_seconds": minimum_stream_seconds,
        "stream_bound_status": "ANALYTIC_LOWER_BOUND_NOT_PERFORMANCE",
        "on_chip_sram_bytes": target.on_chip_sram_bytes,
        "hardware_status": "DATASHEET_INPUT_NOT_MEASURED_BY_SZL",
    }


def build_projection_probe_graph(spec: TransformerSpec) -> GraphPlan:
    """Build a tiny supported-subset probe, never a full transformer graph."""

    hidden = spec.hidden_size
    return GraphPlan(
        name="transformer_projection_probe",
        inputs=(
            BufferSpec("hidden", (1, hidden), "int8"),
            BufferSpec("projection_weight", (hidden, hidden), "int8"),
        ),
        nodes=(
            GraphNode(
                "projection",
                Opcode.GEMM_INT8,
                ("hidden", "projection_weight"),
                "projected",
                {"scale": 1.0},
            ),
            GraphNode(
                "projection_norm",
                Opcode.RMSNORM,
                ("projected",),
                "normalized",
                {"eps": spec.rms_norm_eps},
            ),
            GraphNode(
                "projection_commit",
                Opcode.SHA3_COMMIT,
                ("normalized",),
                None,
                {},
            ),
        ),
        outputs=("normalized",),
    )
