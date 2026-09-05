"""Deterministic symmetric INT8 quantization reference for KHIPU-X1.

This module produces software-reference artifacts and error measurements. It
does not establish model quality, FPGA compatibility, speed or energy use.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

import numpy as np

from .kids import canonical_json_bytes

_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class QuantizationError(ValueError):
    """Raised when a tensor cannot be quantized under the v0.1 contract."""


def tensor_sha256(value: np.ndarray) -> str:
    """Hash dtype, shape and exact C-order bytes using SHA-256."""

    array = np.ascontiguousarray(value)
    header = canonical_json_bytes(
        {"dtype": array.dtype.str, "shape": list(array.shape), "order": "C"}
    )
    return hashlib.sha256(header + b"\x00" + array.tobytes(order="C")).hexdigest()


@dataclass(frozen=True)
class Int8QuantizedTensor:
    values: np.ndarray
    scales: np.ndarray
    axis: int | None
    source_shape: tuple[int, ...]
    source_dtype: str
    source_digest: str
    quantized_digest: str
    scales_digest: str
    mse: float
    max_abs_error: float
    endpoint_count: int
    zero_range_count: int
    scheme: str = "symmetric_absmax_int8_v0.1"

    def metadata(self) -> dict[str, Any]:
        return {
            "schema": "khipu-int8-quant/v0.1",
            "scheme": self.scheme,
            "axis": self.axis,
            "source_shape": list(self.source_shape),
            "source_dtype": self.source_dtype,
            "quantized_dtype": "int8",
            "scale_dtype": "float32-le",
            "source_digest": self.source_digest,
            "quantized_digest": self.quantized_digest,
            "scales_digest": self.scales_digest,
            "mse": self.mse,
            "max_abs_error": self.max_abs_error,
            "endpoint_count": self.endpoint_count,
            "zero_range_count": self.zero_range_count,
            "rounding": "nearest_ties_to_even_numpy_rint",
            "integer_range": [-127, 127],
            "zero_point": 0,
            "evidence": "SOFTWARE_REFERENCE_MEASUREMENT",
            "hardware_status": "UNAVAILABLE",
        }

    @property
    def receipt_digest(self) -> str:
        return hashlib.sha256(canonical_json_bytes(self.metadata())).hexdigest()

    def payloads(self, name: str) -> dict[str, bytes]:
        """Return deterministic payloads suitable for a bounded `.khipu` file."""

        if not isinstance(name, str) or not _NAME.fullmatch(name):
            raise QuantizationError("payload name must be a bounded identifier")
        metadata = {**self.metadata(), "receipt_digest": self.receipt_digest}
        return {
            f"weights/{name}.int8.bin": np.ascontiguousarray(self.values).tobytes(order="C"),
            f"weights/{name}.scale.f32le.bin": np.asarray(
                self.scales, dtype="<f4"
            ).tobytes(order="C"),
            f"weights/{name}.quant.json": canonical_json_bytes(metadata) + b"\n",
        }


def _normalize_axis(axis: int | None, ndim: int) -> int | None:
    if axis is None:
        return None
    if not isinstance(axis, int) or isinstance(axis, bool):
        raise QuantizationError("axis must be an integer or null")
    normalized = axis + ndim if axis < 0 else axis
    if not 0 <= normalized < ndim:
        raise QuantizationError("axis is outside the tensor rank")
    return normalized


def _broadcast_scales(scales: np.ndarray, axis: int | None, shape: tuple[int, ...]) -> np.ndarray:
    if axis is None:
        if scales.shape != (1,):
            raise QuantizationError("per-tensor scales must have shape (1,)")
        return scales.reshape((1,) * len(shape))
    if scales.shape != (shape[axis],):
        raise QuantizationError("per-axis scale count does not match tensor shape")
    broadcast_shape = [1] * len(shape)
    broadcast_shape[axis] = shape[axis]
    return scales.reshape(broadcast_shape)


def quantize_symmetric_int8(
    value: np.ndarray,
    *,
    axis: int | None = None,
) -> Int8QuantizedTensor:
    """Quantize a finite non-empty tensor with symmetric abs-max INT8."""

    source = np.asarray(value)
    if source.ndim == 0 or source.size == 0:
        raise QuantizationError("source tensor must be non-empty and non-scalar")
    if source.ndim > 8:
        raise QuantizationError("source tensor rank exceeds the v0.1 bound")
    if source.dtype.kind not in {"f", "i", "u"}:
        raise QuantizationError("source tensor must be numeric")
    work = np.ascontiguousarray(source, dtype=np.float32)
    if not np.all(np.isfinite(work)):
        raise QuantizationError("source tensor contains non-finite values")

    normalized_axis = _normalize_axis(axis, work.ndim)
    if normalized_axis is None:
        max_abs = np.asarray([np.max(np.abs(work))], dtype=np.float32)
    else:
        reduce_axes = tuple(index for index in range(work.ndim) if index != normalized_axis)
        max_abs = np.max(np.abs(work), axis=reduce_axes).astype(np.float32, copy=False)
        max_abs = np.ascontiguousarray(max_abs.reshape(-1))

    zero_ranges = max_abs == 0.0
    scales = np.where(zero_ranges, np.float32(1.0), max_abs / np.float32(127.0))
    scales = np.ascontiguousarray(scales, dtype=np.float32)
    if not np.all(np.isfinite(scales)) or np.any(scales <= 0.0):
        raise QuantizationError("derived scale is invalid")

    broadcast = _broadcast_scales(scales, normalized_axis, tuple(work.shape))
    rounded = np.rint(work / broadcast)
    clipped = np.clip(rounded, -127.0, 127.0)
    quantized = np.ascontiguousarray(clipped.astype(np.int8))
    restored = quantized.astype(np.float32) * broadcast
    error = restored.astype(np.float64) - work.astype(np.float64)

    scales_le = np.asarray(scales, dtype="<f4")
    return Int8QuantizedTensor(
        values=quantized,
        scales=scales,
        axis=normalized_axis,
        source_shape=tuple(int(dim) for dim in source.shape),
        source_dtype=source.dtype.str,
        source_digest=tensor_sha256(np.ascontiguousarray(source)),
        quantized_digest=tensor_sha256(quantized),
        scales_digest=tensor_sha256(scales_le),
        mse=float(np.mean(np.square(error), dtype=np.float64)),
        max_abs_error=float(np.max(np.abs(error))),
        endpoint_count=int(np.count_nonzero(np.abs(quantized.astype(np.int16)) == 127)),
        zero_range_count=int(np.count_nonzero(zero_ranges)),
    )


def dequantize_symmetric_int8(tensor: Int8QuantizedTensor) -> np.ndarray:
    """Reconstruct float32 values from a validated reference tensor."""

    values = np.asarray(tensor.values)
    scales = np.asarray(tensor.scales, dtype=np.float32)
    if values.dtype != np.int8 or tuple(values.shape) != tensor.source_shape:
        raise QuantizationError("quantized values do not match their metadata")
    if tensor_sha256(np.ascontiguousarray(values)) != tensor.quantized_digest:
        raise QuantizationError("quantized value commitment mismatch")
    scales_le = np.asarray(scales, dtype="<f4")
    if tensor_sha256(scales_le) != tensor.scales_digest:
        raise QuantizationError("scale commitment mismatch")
    if not np.all(np.isfinite(scales)) or np.any(scales <= 0.0):
        raise QuantizationError("scales must be finite and positive")
    broadcast = _broadcast_scales(scales, tensor.axis, tensor.source_shape)
    return np.ascontiguousarray(values.astype(np.float32) * broadcast)
