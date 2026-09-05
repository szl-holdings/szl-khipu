"""Normative KIDS-BIN v0.1 descriptor and batch encoding.

The wire ABI is target-independent and contains numeric buffer handles only. It
never carries host virtual addresses. The software codec is a conformance
reference, not evidence that an FPGA or ASIC implementation exists.
"""

from __future__ import annotations

import hashlib
import hmac
import math
import struct
from dataclasses import dataclass
from enum import IntEnum, IntFlag
from typing import Mapping, Sequence

from .kids import Descriptor, KhipuValidationError, Opcode

DESCRIPTOR_MAGIC = b"KX1D"
BATCH_MAGIC = b"KX1S"
WIRE_MAJOR = 0
WIRE_MINOR = 1
DESCRIPTOR_SIZE = 192
BATCH_HEADER_SIZE = 128
NONE_BUFFER = 0xFFFFFFFF
MAX_BUFFER_ID = NONE_BUFFER - 1
MAX_INPUTS = 3


class WireFormatError(ValueError):
    """Raised when binary KIDS data violates the normative v0.1 layout."""


class WireOpcode(IntEnum):
    NOP = 0x00
    LOAD = 0x01
    STORE = 0x02
    GEMM_INT8 = 0x10
    GEMM_BF16 = 0x11
    RMSNORM = 0x20
    ROPE = 0x21
    ATTN_CAUSAL = 0x30
    ATTN_YARQA = 0x31
    KV_GATHER = 0x40
    KV_SCATTER = 0x41
    SHA3_COMMIT = 0x50
    RECEIPT_EMIT = 0x51
    BARRIER = 0x60
    ZEROIZE = 0x70
    ABORT = 0x7F


class WireFlags(IntFlag):
    NONE = 0
    SCALE_PRESENT = 1 << 0
    EPS_PRESENT = 1 << 1
    GRAPH_BOUND = 1 << 2
    NODE_BOUND = 1 << 3
    LAST_IN_BATCH = 1 << 4


KNOWN_FLAG_MASK = int(
    WireFlags.SCALE_PRESENT
    | WireFlags.EPS_PRESENT
    | WireFlags.GRAPH_BOUND
    | WireFlags.NODE_BOUND
    | WireFlags.LAST_IN_BATCH
)

_OPCODE_TO_WIRE = {
    Opcode.NOP: WireOpcode.NOP,
    Opcode.LOAD: WireOpcode.LOAD,
    Opcode.STORE: WireOpcode.STORE,
    Opcode.GEMM_INT8: WireOpcode.GEMM_INT8,
    Opcode.GEMM_BF16: WireOpcode.GEMM_BF16,
    Opcode.RMSNORM: WireOpcode.RMSNORM,
    Opcode.ROPE: WireOpcode.ROPE,
    Opcode.ATTN_CAUSAL: WireOpcode.ATTN_CAUSAL,
    Opcode.ATTN_YARQA: WireOpcode.ATTN_YARQA,
    Opcode.KV_GATHER: WireOpcode.KV_GATHER,
    Opcode.KV_SCATTER: WireOpcode.KV_SCATTER,
    Opcode.SHA3_COMMIT: WireOpcode.SHA3_COMMIT,
    Opcode.RECEIPT_EMIT: WireOpcode.RECEIPT_EMIT,
    Opcode.BARRIER: WireOpcode.BARRIER,
    Opcode.ZEROIZE: WireOpcode.ZEROIZE,
    Opcode.ABORT: WireOpcode.ABORT,
}
_WIRE_TO_OPCODE = {value: key for key, value in _OPCODE_TO_WIRE.items()}

# Expected logical buffer arity for operations represented by this revision.
_ARITY: dict[Opcode, tuple[int, bool]] = {
    Opcode.NOP: (0, False),
    Opcode.GEMM_INT8: (2, True),
    Opcode.RMSNORM: (-1, True),  # one data input plus optional weight
    Opcode.SHA3_COMMIT: (1, False),
    Opcode.BARRIER: (0, False),
    Opcode.ABORT: (0, False),
}


@dataclass(frozen=True)
class WireDescriptor:
    opcode: Opcode
    sequence: int
    nonce: int
    input_ids: tuple[int, ...]
    output_id: int | None
    flags: WireFlags
    arg0: int
    arg1: int
    model_digest: str
    policy_digest: str
    graph_digest: str | None
    descriptor_digest: str

    @property
    def scale(self) -> float | None:
        if not self.flags & WireFlags.SCALE_PRESENT:
            return None
        return _u64_to_f32(self.arg0)

    @property
    def eps(self) -> float | None:
        if not self.flags & WireFlags.EPS_PRESENT:
            return None
        return _u64_to_f32(self.arg0)

    @property
    def node_tag(self) -> int | None:
        return self.arg1 if self.flags & WireFlags.NODE_BOUND else None

    def as_dict(self) -> dict[str, object]:
        return {
            "wire_version": f"{WIRE_MAJOR}.{WIRE_MINOR}",
            "opcode": self.opcode.value,
            "opcode_code": int(_OPCODE_TO_WIRE[self.opcode]),
            "sequence": self.sequence,
            "nonce": self.nonce,
            "input_ids": list(self.input_ids),
            "output_id": self.output_id,
            "flags": int(self.flags),
            "arg0": self.arg0,
            "arg1": self.arg1,
            "scale": self.scale,
            "eps": self.eps,
            "node_tag": self.node_tag,
            "model_digest": self.model_digest,
            "policy_digest": self.policy_digest,
            "graph_digest": self.graph_digest,
            "descriptor_digest": self.descriptor_digest,
        }


@dataclass(frozen=True)
class WireBatch:
    descriptors: tuple[WireDescriptor, ...]
    body_digest: str
    header_digest: str
    flags: int = 0

    def as_dict(self) -> dict[str, object]:
        return {
            "wire_version": f"{WIRE_MAJOR}.{WIRE_MINOR}",
            "descriptor_count": len(self.descriptors),
            "body_digest": self.body_digest,
            "header_digest": self.header_digest,
            "flags": self.flags,
            "descriptors": [descriptor.as_dict() for descriptor in self.descriptors],
        }


def opcode_code(opcode: Opcode) -> int:
    try:
        return int(_OPCODE_TO_WIRE[opcode])
    except KeyError as exc:
        raise WireFormatError(f"opcode has no KIDS-BIN assignment: {opcode}") from exc


def _require_u64(value: int, name: str) -> int:
    if not isinstance(value, int) or not 0 <= value <= 0xFFFFFFFFFFFFFFFF:
        raise WireFormatError(f"{name} must fit uint64")
    return value


def _require_buffer_id(value: int, name: str) -> int:
    if not isinstance(value, int) or not 0 <= value <= MAX_BUFFER_ID:
        raise WireFormatError(f"{name} must fit uint32 and cannot use NONE_BUFFER")
    return value


def _f32_to_u64(value: float, name: str, *, positive: bool = False) -> int:
    numeric = float(value)
    if not math.isfinite(numeric) or (positive and numeric <= 0.0):
        qualifier = "finite and positive" if positive else "finite"
        raise WireFormatError(f"{name} must be {qualifier}")
    # Reject values that overflow or underflow to a non-equivalent nonzero float32.
    packed = struct.pack("<f", numeric)
    decoded = struct.unpack("<f", packed)[0]
    if not math.isfinite(decoded):
        raise WireFormatError(f"{name} is not representable as float32")
    if numeric != 0.0 and decoded == 0.0:
        raise WireFormatError(f"{name} underflows float32")
    return struct.unpack("<I", packed)[0]


def _u64_to_f32(value: int) -> float:
    if value >> 32:
        raise WireFormatError("float argument has nonzero reserved upper bits")
    return struct.unpack("<f", struct.pack("<I", value & 0xFFFFFFFF))[0]


def _digest_bytes(value: str, name: str, *, allow_zero: bool = False) -> bytes:
    try:
        raw = bytes.fromhex(value)
    except (TypeError, ValueError) as exc:
        raise WireFormatError(f"{name} must be lowercase hex") from exc
    if len(raw) != 32 or value != value.lower():
        raise WireFormatError(f"{name} must be lowercase SHA-256 hex")
    if not allow_zero and raw == b"\x00" * 32:
        raise WireFormatError(f"{name} cannot be the all-zero digest")
    return raw


def _node_tag(node_id: str) -> int:
    if not isinstance(node_id, str) or not node_id or len(node_id.encode("utf-8")) > 128:
        raise WireFormatError("graph_node_id must be a non-empty bounded UTF-8 string")
    return int.from_bytes(hashlib.sha256(node_id.encode("utf-8")).digest()[:8], "little")


def _logical_flags(descriptor: Descriptor) -> WireFlags:
    flags = WireFlags.NONE
    known = {"LAST_IN_BATCH"}
    unknown = set(descriptor.flags) - known
    if unknown:
        raise WireFormatError(f"logical flags are not representable: {sorted(unknown)}")
    if "LAST_IN_BATCH" in descriptor.flags:
        flags |= WireFlags.LAST_IN_BATCH
    return flags


def _validate_arity(descriptor: Descriptor) -> None:
    expected = _ARITY.get(descriptor.opcode)
    if expected is None:
        # Reserved operations have numeric assignments but no v0.1 logical
        # encoding contract. Encoding them would silently invent semantics.
        raise WireFormatError(f"opcode {descriptor.opcode.value} is reserved in KIDS-BIN v0.1")
    input_count, requires_output = expected
    if descriptor.opcode is Opcode.RMSNORM:
        if len(descriptor.inputs) not in {1, 2}:
            raise WireFormatError("RMSNORM requires one or two input buffers")
    elif len(descriptor.inputs) != input_count:
        raise WireFormatError(
            f"{descriptor.opcode.value} requires {input_count} input buffers"
        )
    if requires_output != (descriptor.output is not None):
        state = "requires" if requires_output else "forbids"
        raise WireFormatError(f"{descriptor.opcode.value} {state} an output buffer")


def encode_descriptor(descriptor: Descriptor, buffer_ids: Mapping[str, int]) -> bytes:
    """Encode one logical descriptor into the normative 192-byte layout."""

    try:
        descriptor.validate()
    except KhipuValidationError as exc:
        raise WireFormatError(str(exc)) from exc
    _validate_arity(descriptor)
    if len(descriptor.inputs) > MAX_INPUTS:
        raise WireFormatError(f"at most {MAX_INPUTS} input buffers are encodable")

    referenced_names = list(descriptor.inputs)
    if descriptor.output is not None:
        referenced_names.append(descriptor.output)
    missing = [name for name in referenced_names if name not in buffer_ids]
    if missing:
        raise WireFormatError(f"buffer map is missing names: {missing}")
    normalized_ids: dict[str, int] = {
        name: _require_buffer_id(value, f"buffer_ids[{name!r}]")
        for name, value in buffer_ids.items()
    }
    referenced_pairs = [(name, normalized_ids[name]) for name in referenced_names]
    id_to_name: dict[int, str] = {}
    for name, value in referenced_pairs:
        other = id_to_name.get(value)
        if other is not None:
            raise WireFormatError(
                f"wire v0.1 forbids aliased buffer slots: {other!r} and {name!r} share id {value}"
            )
        id_to_name[value] = name

    flags = _logical_flags(descriptor)
    arg0 = 0
    arg1 = 0
    attrs = dict(descriptor.attrs)
    allowed_attrs = {"graph_digest", "graph_node_id"}

    if descriptor.opcode is Opcode.GEMM_INT8 and "scale" in attrs:
        arg0 = _f32_to_u64(attrs["scale"], "scale")
        flags |= WireFlags.SCALE_PRESENT
        allowed_attrs.add("scale")
    elif descriptor.opcode is Opcode.RMSNORM:
        arg0 = _f32_to_u64(attrs.get("eps", 1e-6), "eps", positive=True)
        flags |= WireFlags.EPS_PRESENT
        allowed_attrs.add("eps")
    elif descriptor.opcode is Opcode.ABORT:
        reason_code = attrs.get("reason_code", 0)
        if not isinstance(reason_code, int) or not 0 <= reason_code <= 0xFFFFFFFF:
            raise WireFormatError("reason_code must fit uint32")
        arg0 = reason_code
        allowed_attrs.add("reason_code")

    unknown_attrs = set(attrs) - allowed_attrs
    if unknown_attrs:
        raise WireFormatError(f"attrs are not representable: {sorted(unknown_attrs)}")

    graph_raw = b"\x00" * 32
    graph_digest = attrs.get("graph_digest")
    node_id = attrs.get("graph_node_id")
    if graph_digest is not None:
        graph_raw = _digest_bytes(str(graph_digest), "graph_digest")
        flags |= WireFlags.GRAPH_BOUND
    if node_id is not None:
        if graph_digest is None:
            raise WireFormatError("graph_node_id requires graph_digest")
        arg1 = _node_tag(node_id)
        flags |= WireFlags.NODE_BOUND

    raw = bytearray(DESCRIPTOR_SIZE)
    raw[0:4] = DESCRIPTOR_MAGIC
    raw[4] = WIRE_MAJOR
    raw[5] = WIRE_MINOR
    raw[6] = opcode_code(descriptor.opcode)
    raw[7] = len(descriptor.inputs)
    struct.pack_into("<H", raw, 8, int(flags))
    struct.pack_into("<H", raw, 10, DESCRIPTOR_SIZE)
    struct.pack_into("<I", raw, 12, DESCRIPTOR_SIZE)
    struct.pack_into("<Q", raw, 16, _require_u64(descriptor.sequence, "sequence"))
    struct.pack_into("<Q", raw, 24, _require_u64(descriptor.nonce, "nonce"))

    inputs = [normalized_ids[name] for name in descriptor.inputs]
    inputs.extend([NONE_BUFFER] * (MAX_INPUTS - len(inputs)))
    for index, value in enumerate(inputs):
        struct.pack_into("<I", raw, 32 + 4 * index, value)
    output_id = NONE_BUFFER if descriptor.output is None else normalized_ids[descriptor.output]
    struct.pack_into("<I", raw, 44, output_id)
    struct.pack_into("<Q", raw, 48, arg0)
    struct.pack_into("<Q", raw, 56, arg1)
    raw[64:96] = _digest_bytes(descriptor.model_digest, "model_digest")
    raw[96:128] = _digest_bytes(descriptor.policy_digest, "policy_digest")
    raw[128:160] = graph_raw
    raw[160:192] = hashlib.sha256(raw[:160]).digest()
    return bytes(raw)


def decode_descriptor(raw: bytes) -> WireDescriptor:
    """Validate and decode exactly one normative 192-byte descriptor."""

    if not isinstance(raw, bytes) or len(raw) != DESCRIPTOR_SIZE:
        raise WireFormatError(f"descriptor must be exactly {DESCRIPTOR_SIZE} bytes")
    if raw[:4] != DESCRIPTOR_MAGIC:
        raise WireFormatError("descriptor magic mismatch")
    if raw[4] != WIRE_MAJOR or raw[5] != WIRE_MINOR:
        raise WireFormatError("unsupported descriptor wire version")
    try:
        wire_opcode = WireOpcode(raw[6])
        opcode = _WIRE_TO_OPCODE[wire_opcode]
    except (ValueError, KeyError) as exc:
        raise WireFormatError(f"unknown wire opcode: {raw[6]}") from exc
    input_count = raw[7]
    if input_count > MAX_INPUTS:
        raise WireFormatError("input_count exceeds the wire limit")
    flags_value = struct.unpack_from("<H", raw, 8)[0]
    if flags_value & ~KNOWN_FLAG_MASK:
        raise WireFormatError("descriptor has nonzero reserved flag bits")
    flags = WireFlags(flags_value)
    if struct.unpack_from("<H", raw, 10)[0] != DESCRIPTOR_SIZE:
        raise WireFormatError("descriptor header size mismatch")
    if struct.unpack_from("<I", raw, 12)[0] != DESCRIPTOR_SIZE:
        raise WireFormatError("descriptor total size mismatch")

    expected_digest = hashlib.sha256(raw[:160]).digest()
    if not hmac.compare_digest(raw[160:192], expected_digest):
        raise WireFormatError("descriptor digest mismatch")

    sequence = struct.unpack_from("<Q", raw, 16)[0]
    nonce = struct.unpack_from("<Q", raw, 24)[0]
    all_inputs = tuple(
        struct.unpack_from("<I", raw, 32 + 4 * index)[0]
        for index in range(MAX_INPUTS)
    )
    input_ids = all_inputs[:input_count]
    if any(value == NONE_BUFFER for value in input_ids):
        raise WireFormatError("active input uses NONE_BUFFER")
    if any(value != NONE_BUFFER for value in all_inputs[input_count:]):
        raise WireFormatError("unused input slots must use NONE_BUFFER")
    output_raw = struct.unpack_from("<I", raw, 44)[0]
    output_id = None if output_raw == NONE_BUFFER else output_raw
    arg0 = struct.unpack_from("<Q", raw, 48)[0]
    arg1 = struct.unpack_from("<Q", raw, 56)[0]

    model_digest = raw[64:96].hex()
    policy_digest = raw[96:128].hex()
    _digest_bytes(model_digest, "model_digest")
    _digest_bytes(policy_digest, "policy_digest")
    graph_raw = raw[128:160]
    graph_bound = bool(flags & WireFlags.GRAPH_BOUND)
    graph_digest = graph_raw.hex() if graph_bound else None
    if graph_bound:
        _digest_bytes(graph_digest, "graph_digest")
    elif graph_raw != b"\x00" * 32:
        raise WireFormatError("unbound graph digest area must be zero")
    if flags & WireFlags.NODE_BOUND and not graph_bound:
        raise WireFormatError("NODE_BOUND requires GRAPH_BOUND")
    if not flags & WireFlags.NODE_BOUND and arg1 != 0:
        raise WireFormatError("unbound node tag must be zero")

    # Decode-time semantic checks ensure malformed hardware commands cannot be
    # mistaken for valid logical descriptors.
    pseudo = Descriptor(
        sequence=sequence,
        nonce=nonce,
        opcode=opcode,
        model_digest=model_digest,
        policy_digest=policy_digest,
        inputs=tuple(f"b{value}" for value in input_ids),
        output=None if output_id is None else f"b{output_id}",
        attrs={},
    )
    if opcode in _ARITY:
        _validate_arity(pseudo)
    else:
        raise WireFormatError(f"opcode {opcode.value} is reserved in KIDS-BIN v0.1")

    if opcode is Opcode.GEMM_INT8:
        if flags & WireFlags.EPS_PRESENT:
            raise WireFormatError("GEMM_INT8 cannot set EPS_PRESENT")
        if flags & WireFlags.SCALE_PRESENT:
            if not math.isfinite(_u64_to_f32(arg0)):
                raise WireFormatError("GEMM_INT8 scale is non-finite")
        elif arg0 != 0:
            raise WireFormatError("GEMM_INT8 arg0 must be zero without scale")
    elif opcode is Opcode.RMSNORM:
        if not flags & WireFlags.EPS_PRESENT or flags & WireFlags.SCALE_PRESENT:
            raise WireFormatError("RMSNORM requires EPS_PRESENT and forbids SCALE_PRESENT")
        eps = _u64_to_f32(arg0)
        if not math.isfinite(eps) or eps <= 0.0:
            raise WireFormatError("RMSNORM eps is invalid")
    elif opcode is Opcode.ABORT:
        if arg0 >> 32:
            raise WireFormatError("ABORT reason code has nonzero reserved bits")
        if flags & (WireFlags.SCALE_PRESENT | WireFlags.EPS_PRESENT):
            raise WireFormatError("ABORT has invalid numeric flags")
    else:
        if arg0 != 0:
            raise WireFormatError(f"{opcode.value} has nonzero reserved arg0")
        if flags & (WireFlags.SCALE_PRESENT | WireFlags.EPS_PRESENT):
            raise WireFormatError(f"{opcode.value} has invalid numeric flags")

    referenced = (*input_ids, *(() if output_id is None else (output_id,)))
    if len(referenced) != len(set(referenced)):
        raise WireFormatError("distinct logical buffers must not alias one wire id")

    return WireDescriptor(
        opcode=opcode,
        sequence=sequence,
        nonce=nonce,
        input_ids=input_ids,
        output_id=output_id,
        flags=flags,
        arg0=arg0,
        arg1=arg1,
        model_digest=model_digest,
        policy_digest=policy_digest,
        graph_digest=graph_digest,
        descriptor_digest=raw[160:192].hex(),
    )


def encode_batch(
    descriptors: Sequence[Descriptor],
    buffer_ids: Mapping[str, int],
    *,
    flags: int = 0,
) -> bytes:
    """Encode an ordered command batch with a 128-byte integrity header."""

    if not descriptors:
        raise WireFormatError("batch must contain at least one descriptor")
    if len(descriptors) > 0xFFFFFFFF:
        raise WireFormatError("batch contains too many descriptors")
    if not isinstance(flags, int) or not 0 <= flags <= 0xFFFF:
        raise WireFormatError("batch flags must fit uint16")
    if flags != 0:
        raise WireFormatError("KIDS-BIN v0.1 defines no nonzero batch flags")

    previous_sequence = -1
    previous_nonce = -1
    encoded: list[bytes] = []
    for index, descriptor in enumerate(descriptors):
        if descriptor.sequence <= previous_sequence or descriptor.nonce <= previous_nonce:
            raise WireFormatError("batch sequence/nonce must be strictly increasing")
        previous_sequence = descriptor.sequence
        previous_nonce = descriptor.nonce
        logical = descriptor
        if index == len(descriptors) - 1 and "LAST_IN_BATCH" not in logical.flags:
            logical = Descriptor(
                sequence=logical.sequence,
                nonce=logical.nonce,
                opcode=logical.opcode,
                model_digest=logical.model_digest,
                policy_digest=logical.policy_digest,
                inputs=logical.inputs,
                output=logical.output,
                attrs=logical.attrs,
                flags=(*logical.flags, "LAST_IN_BATCH"),
                version=logical.version,
            )
        elif index != len(descriptors) - 1 and "LAST_IN_BATCH" in logical.flags:
            raise WireFormatError("only the final descriptor may set LAST_IN_BATCH")
        encoded.append(encode_descriptor(logical, buffer_ids))

    body = b"".join(encoded)
    header = bytearray(BATCH_HEADER_SIZE)
    header[:4] = BATCH_MAGIC
    header[4] = WIRE_MAJOR
    header[5] = WIRE_MINOR
    struct.pack_into("<H", header, 6, flags)
    struct.pack_into("<H", header, 8, BATCH_HEADER_SIZE)
    struct.pack_into("<H", header, 10, DESCRIPTOR_SIZE)
    struct.pack_into("<I", header, 12, len(encoded))
    struct.pack_into("<Q", header, 16, descriptors[0].sequence)
    struct.pack_into("<Q", header, 24, descriptors[-1].sequence)
    struct.pack_into("<Q", header, 32, descriptors[0].nonce)
    struct.pack_into("<Q", header, 40, descriptors[-1].nonce)
    header[48:80] = hashlib.sha256(body).digest()
    # Bytes 80:96 are reserved and remain zero.
    header[96:128] = hashlib.sha256(header[:96]).digest()
    return bytes(header) + body


def decode_batch(raw: bytes) -> WireBatch:
    """Validate a complete command batch and every included descriptor."""

    if not isinstance(raw, bytes) or len(raw) < BATCH_HEADER_SIZE + DESCRIPTOR_SIZE:
        raise WireFormatError("batch is too short")
    if raw[:4] != BATCH_MAGIC:
        raise WireFormatError("batch magic mismatch")
    if raw[4] != WIRE_MAJOR or raw[5] != WIRE_MINOR:
        raise WireFormatError("unsupported batch wire version")
    flags = struct.unpack_from("<H", raw, 6)[0]
    if flags != 0:
        raise WireFormatError("batch has nonzero reserved flags")
    if struct.unpack_from("<H", raw, 8)[0] != BATCH_HEADER_SIZE:
        raise WireFormatError("batch header size mismatch")
    if struct.unpack_from("<H", raw, 10)[0] != DESCRIPTOR_SIZE:
        raise WireFormatError("batch descriptor size mismatch")
    count = struct.unpack_from("<I", raw, 12)[0]
    if count == 0:
        raise WireFormatError("batch descriptor count is zero")
    expected_size = BATCH_HEADER_SIZE + count * DESCRIPTOR_SIZE
    if len(raw) != expected_size:
        raise WireFormatError("batch byte length does not match descriptor count")
    if raw[80:96] != b"\x00" * 16:
        raise WireFormatError("batch reserved header bytes are nonzero")
    if not hmac.compare_digest(raw[96:128], hashlib.sha256(raw[:96]).digest()):
        raise WireFormatError("batch header digest mismatch")
    body = raw[BATCH_HEADER_SIZE:]
    body_digest = hashlib.sha256(body).digest()
    if not hmac.compare_digest(raw[48:80], body_digest):
        raise WireFormatError("batch body digest mismatch")

    descriptors = tuple(
        decode_descriptor(
            body[index * DESCRIPTOR_SIZE : (index + 1) * DESCRIPTOR_SIZE]
        )
        for index in range(count)
    )
    sequences = [descriptor.sequence for descriptor in descriptors]
    nonces = [descriptor.nonce for descriptor in descriptors]
    if any(
        current <= previous
        for previous, current in zip(sequences, sequences[1:])
    ):
        raise WireFormatError("batch descriptor sequence is not strictly increasing")
    if any(current <= previous for previous, current in zip(nonces, nonces[1:])):
        raise WireFormatError("batch descriptor nonce is not strictly increasing")
    if struct.unpack_from("<Q", raw, 16)[0] != sequences[0]:
        raise WireFormatError("batch first_sequence mismatch")
    if struct.unpack_from("<Q", raw, 24)[0] != sequences[-1]:
        raise WireFormatError("batch last_sequence mismatch")
    if struct.unpack_from("<Q", raw, 32)[0] != nonces[0]:
        raise WireFormatError("batch first_nonce mismatch")
    if struct.unpack_from("<Q", raw, 40)[0] != nonces[-1]:
        raise WireFormatError("batch last_nonce mismatch")
    for index, descriptor in enumerate(descriptors):
        is_last = bool(descriptor.flags & WireFlags.LAST_IN_BATCH)
        if is_last != (index == len(descriptors) - 1):
            raise WireFormatError("LAST_IN_BATCH marker is inconsistent")

    return WireBatch(
        descriptors=descriptors,
        body_digest=body_digest.hex(),
        header_digest=raw[96:128].hex(),
        flags=flags,
    )
