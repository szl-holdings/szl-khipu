"""KIDS v0.1 logical descriptor definitions.

This is a deterministic software-reference encoding, not a hardware wire format.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class KhipuValidationError(ValueError):
    """Raised when a KIDS descriptor violates the v0.1 contract."""


class Opcode(str, Enum):
    NOP = "NOP"
    GEMM_INT8 = "GEMM_INT8"
    RMSNORM = "RMSNORM"
    SHA3_COMMIT = "SHA3_COMMIT"
    BARRIER = "BARRIER"
    ABORT = "ABORT"

    # Reserved for later, explicit implementations.
    LOAD = "LOAD"
    STORE = "STORE"
    GEMM_BF16 = "GEMM_BF16"
    ROPE = "ROPE"
    ATTN_CAUSAL = "ATTN_CAUSAL"
    ATTN_YARQA = "ATTN_YARQA"
    KV_GATHER = "KV_GATHER"
    KV_SCATTER = "KV_SCATTER"
    RECEIPT_EMIT = "RECEIPT_EMIT"
    ZEROIZE = "ZEROIZE"


IMPLEMENTED_OPCODES = {
    Opcode.NOP,
    Opcode.GEMM_INT8,
    Opcode.RMSNORM,
    Opcode.SHA3_COMMIT,
    Opcode.BARRIER,
    Opcode.ABORT,
}


def _validate_finite(value: Any, path: str = "attrs") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise KhipuValidationError(f"{path} contains a non-finite float")
    if isinstance(value, Mapping):
        for key, child in value.items():
            _validate_finite(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _validate_finite(child, f"{path}[{index}]")


def canonical_json_bytes(value: Any) -> bytes:
    _validate_finite(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


@dataclass(frozen=True)
class Descriptor:
    sequence: int
    nonce: int
    opcode: Opcode
    model_digest: str
    policy_digest: str
    inputs: tuple[str, ...] = field(default_factory=tuple)
    output: str | None = None
    attrs: Mapping[str, Any] = field(default_factory=dict)
    flags: tuple[str, ...] = field(default_factory=tuple)
    version: str = "0.1"

    def validate(self) -> None:
        if self.version != "0.1":
            raise KhipuValidationError(f"unsupported KIDS version: {self.version}")
        if not isinstance(self.sequence, int) or self.sequence < 0:
            raise KhipuValidationError("sequence must be a non-negative integer")
        if not isinstance(self.nonce, int) or self.nonce < 0:
            raise KhipuValidationError("nonce must be a non-negative integer")
        if not _HEX64.fullmatch(self.model_digest):
            raise KhipuValidationError("model_digest must be lowercase hex SHA-256")
        if not _HEX64.fullmatch(self.policy_digest):
            raise KhipuValidationError("policy_digest must be lowercase hex SHA-256")
        for name in self.inputs:
            if not isinstance(name, str) or not name or len(name) > 128:
                raise KhipuValidationError("input buffer names must be 1..128 characters")
        if self.output is not None and (not isinstance(self.output, str) or not self.output):
            raise KhipuValidationError("output must be a non-empty string or null")
        _validate_finite(self.attrs)

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "version": self.version,
            "sequence": self.sequence,
            "nonce": self.nonce,
            "opcode": self.opcode.value,
            "model_digest": self.model_digest,
            "policy_digest": self.policy_digest,
            "inputs": list(self.inputs),
            "output": self.output,
            "attrs": dict(self.attrs),
            "flags": list(self.flags),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Descriptor":
        try:
            descriptor = cls(
                version=str(data.get("version", "0.1")),
                sequence=int(data["sequence"]),
                nonce=int(data["nonce"]),
                opcode=Opcode(str(data["opcode"])),
                model_digest=str(data["model_digest"]),
                policy_digest=str(data["policy_digest"]),
                inputs=tuple(str(item) for item in data.get("inputs", [])),
                output=None if data.get("output") is None else str(data["output"]),
                attrs=dict(data.get("attrs", {})),
                flags=tuple(str(item) for item in data.get("flags", [])),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise KhipuValidationError(f"invalid descriptor: {exc}") from exc
        descriptor.validate()
        return descriptor


def validate_stream(descriptors: Sequence[Descriptor]) -> None:
    last_sequence = -1
    last_nonce = -1
    for descriptor in descriptors:
        descriptor.validate()
        if descriptor.sequence <= last_sequence:
            raise KhipuValidationError("descriptor sequence replay or reordering detected")
        if descriptor.nonce <= last_nonce:
            raise KhipuValidationError("descriptor nonce replay or reordering detected")
        last_sequence = descriptor.sequence
        last_nonce = descriptor.nonce
