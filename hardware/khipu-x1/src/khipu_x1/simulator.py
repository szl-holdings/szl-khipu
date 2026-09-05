"""Deterministic NumPy golden simulator for KIDS v0.1.

The only qualified execution path in wave 1 is ``software_emulator``. Requests
for FPGA or ASIC execution fail closed until a measured backend exists.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np

from .kids import Descriptor, IMPLEMENTED_OPCODES, Opcode, validate_stream
from .receipt import ReceiptChain


class KhipuExecutionError(RuntimeError):
    """Raised when a command cannot be executed under the declared contract."""


def array_commitment(array: np.ndarray) -> str:
    """Commit to dtype, shape and exact C-order bytes with SHA3-256."""

    contiguous = np.ascontiguousarray(array)
    header = f"{contiguous.dtype.str}|{','.join(map(str, contiguous.shape))}|".encode("utf-8")
    return hashlib.sha3_256(header + contiguous.tobytes(order="C")).hexdigest()


@dataclass
class ExecutionResult:
    path: str
    buffers: dict[str, np.ndarray]
    chain: ReceiptChain
    elapsed_ns: int
    energy_j: float | None
    status: str

    def summary(self) -> dict[str, Any]:
        ok, first_break, reason = self.chain.verify()
        return {
            "execution_path": self.path,
            "status": self.status,
            "elapsed_ns": self.elapsed_ns,
            "energy_j": self.energy_j,
            "energy_status": "UNAVAILABLE" if self.energy_j is None else "MEASURED",
            "receipt_head": self.chain.head,
            "receipt_depth": len(self.chain.events),
            "receipt_verified": ok,
            "first_break": first_break,
            "verification_reason": reason,
            "buffer_commitments": {
                name: array_commitment(value) for name, value in sorted(self.buffers.items())
            },
        }


class KhipuSimulator:
    """Stateful KIDS command-stream reference.

    Sequence and nonce state persist across calls. Once a descriptor is admitted,
    its identifiers are consumed even when execution is blocked, preventing a
    failed command from being replayed under the same identity.
    """

    def __init__(self, execution_path: str = "software_emulator") -> None:
        if execution_path != "software_emulator":
            raise KhipuExecutionError(
                f"UNAVAILABLE: execution path {execution_path!r} has no qualified backend"
            )
        self.execution_path = execution_path
        self.buffers: dict[str, np.ndarray] = {}
        self.chain = ReceiptChain()
        self.last_sequence = -1
        self.last_nonce = -1
        self.aborted = False

    def register_buffer(self, name: str, value: np.ndarray | Iterable[Any]) -> None:
        if not name or len(name) > 128:
            raise ValueError("buffer name must be 1..128 characters")
        array = np.asarray(value)
        if array.dtype.kind in {"f", "c"} and not np.all(np.isfinite(array)):
            raise KhipuExecutionError(f"NONFINITE_INPUT: buffer {name}")
        self.buffers[name] = np.ascontiguousarray(array)

    def _get(self, name: str) -> np.ndarray:
        try:
            return self.buffers[name]
        except KeyError as exc:
            raise KhipuExecutionError(f"BUFFER_NOT_FOUND: {name}") from exc

    @staticmethod
    def _descriptor_receipt_fields(descriptor: Descriptor, execution_path: str) -> dict[str, Any]:
        return {
            "kids_version": descriptor.version,
            "sequence": descriptor.sequence,
            "nonce": descriptor.nonce,
            "opcode": descriptor.opcode.value,
            "execution_path": execution_path,
            "model_digest": descriptor.model_digest,
            "policy_digest": descriptor.policy_digest,
            "attrs": dict(descriptor.attrs),
        }

    def _execute_one(self, descriptor: Descriptor) -> None:
        if descriptor.opcode not in IMPLEMENTED_OPCODES:
            raise KhipuExecutionError(f"UNIMPLEMENTED: {descriptor.opcode.value}")

        input_commitments = {
            name: array_commitment(self._get(name)) for name in descriptor.inputs
        }
        output_commitment: str | None = None

        if descriptor.opcode is Opcode.NOP:
            pass

        elif descriptor.opcode is Opcode.GEMM_INT8:
            if len(descriptor.inputs) != 2 or descriptor.output is None:
                raise KhipuExecutionError("INVALID_DESCRIPTOR: GEMM_INT8 requires two inputs and one output")
            left = self._get(descriptor.inputs[0])
            right = self._get(descriptor.inputs[1])
            if left.dtype != np.int8 or right.dtype != np.int8:
                raise KhipuExecutionError("DTYPE_MISMATCH: GEMM_INT8 requires int8 inputs")
            if left.ndim < 2 or right.ndim != 2 or left.shape[-1] != right.shape[0]:
                raise KhipuExecutionError("SHAPE_MISMATCH: GEMM_INT8")
            result = np.matmul(left.astype(np.int32), right.astype(np.int32))
            scale = descriptor.attrs.get("scale")
            if scale is not None:
                scale_value = float(scale)
                if not np.isfinite(scale_value):
                    raise KhipuExecutionError("NONFINITE_INPUT: scale")
                result = result.astype(np.float32) * scale_value
            self.buffers[descriptor.output] = np.ascontiguousarray(result)
            output_commitment = array_commitment(self.buffers[descriptor.output])

        elif descriptor.opcode is Opcode.RMSNORM:
            if len(descriptor.inputs) not in {1, 2} or descriptor.output is None:
                raise KhipuExecutionError(
                    "INVALID_DESCRIPTOR: RMSNORM requires data, optional weight, and output"
                )
            data = self._get(descriptor.inputs[0])
            if data.dtype.kind != "f":
                data = data.astype(np.float32)
            if not np.all(np.isfinite(data)):
                raise KhipuExecutionError("NONFINITE_INPUT: RMSNORM data")
            eps = float(descriptor.attrs.get("eps", 1e-6))
            if not np.isfinite(eps) or eps <= 0:
                raise KhipuExecutionError("INVALID_DESCRIPTOR: eps must be finite and positive")
            denom = np.sqrt(
                np.mean(np.square(data, dtype=np.float64), axis=-1, keepdims=True) + eps
            )
            result = data / denom
            if len(descriptor.inputs) == 2:
                weight = self._get(descriptor.inputs[1])
                if weight.ndim != 1 or weight.shape[0] != data.shape[-1]:
                    raise KhipuExecutionError("SHAPE_MISMATCH: RMSNORM weight")
                if not np.all(np.isfinite(weight)):
                    raise KhipuExecutionError("NONFINITE_INPUT: RMSNORM weight")
                result = result * weight
            self.buffers[descriptor.output] = np.ascontiguousarray(result.astype(np.float32))
            output_commitment = array_commitment(self.buffers[descriptor.output])

        elif descriptor.opcode is Opcode.SHA3_COMMIT:
            if len(descriptor.inputs) != 1:
                raise KhipuExecutionError(
                    "INVALID_DESCRIPTOR: SHA3_COMMIT requires exactly one input"
                )
            output_commitment = input_commitments[descriptor.inputs[0]]

        elif descriptor.opcode is Opcode.BARRIER:
            pass

        elif descriptor.opcode is Opcode.ABORT:
            self.aborted = True
            self.chain.append(
                "command_aborted",
                {
                    **self._descriptor_receipt_fields(descriptor, self.execution_path),
                    "reason": str(descriptor.attrs.get("reason", "explicit abort")),
                },
            )
            raise KhipuExecutionError("ABORTED")

        self.chain.append(
            "command_executed",
            {
                **self._descriptor_receipt_fields(descriptor, self.execution_path),
                "input_commitments": input_commitments,
                "output": descriptor.output,
                "output_commitment": output_commitment,
                "energy_j": None,
                "energy_status": "UNAVAILABLE",
            },
        )

    def execute(self, descriptors: list[Descriptor]) -> ExecutionResult:
        if self.aborted:
            raise KhipuExecutionError("DEVICE_ABORTED: create a new simulator instance after abort")
        if not descriptors:
            raise KhipuExecutionError("INVALID_DESCRIPTOR: command stream is empty")

        validate_stream(descriptors)
        first = descriptors[0]
        if first.sequence <= self.last_sequence or first.nonce <= self.last_nonce:
            raise KhipuExecutionError("REPLAY_REJECTED: sequence or nonce was already consumed")

        started = time.perf_counter_ns()
        for descriptor in descriptors:
            # Consume identity before execution. A blocked command cannot be retried
            # under the same sequence/nonce pair.
            self.last_sequence = descriptor.sequence
            self.last_nonce = descriptor.nonce
            try:
                self._execute_one(descriptor)
            except KhipuExecutionError as exc:
                if descriptor.opcode is not Opcode.ABORT:
                    self.chain.append(
                        "command_blocked",
                        {
                            **self._descriptor_receipt_fields(descriptor, self.execution_path),
                            "reason": str(exc),
                        },
                    )
                self.chain.require_valid()
                raise

        elapsed = time.perf_counter_ns() - started
        self.chain.require_valid()
        return ExecutionResult(
            path=self.execution_path,
            buffers={name: value.copy() for name, value in self.buffers.items()},
            chain=self.chain,
            elapsed_ns=elapsed,
            energy_j=None,
            status="OK",
        )
