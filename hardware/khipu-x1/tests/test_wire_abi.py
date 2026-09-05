from __future__ import annotations

import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path

import pytest

from khipu_x1 import Descriptor, Opcode
from khipu_x1.wire import (
    BATCH_HEADER_SIZE,
    DESCRIPTOR_SIZE,
    WireFlags,
    WireFormatError,
    decode_batch,
    decode_descriptor,
    encode_batch,
    encode_descriptor,
)

DIGEST = hashlib.sha256(b"wire-test").hexdigest()
GRAPH = hashlib.sha256(b"wire-graph").hexdigest()
BUFFERS = {"a": 1, "b": 2, "out": 3}


def desc(opcode: Opcode = Opcode.GEMM_INT8, **kwargs) -> Descriptor:
    base = dict(
        sequence=1,
        nonce=10,
        opcode=opcode,
        model_digest=DIGEST,
        policy_digest=DIGEST,
        inputs=("a", "b"),
        output="out",
        attrs={"scale": 0.25, "graph_digest": GRAPH, "graph_node_id": "project"},
    )
    base.update(kwargs)
    return Descriptor(**base)


def test_descriptor_layout_and_roundtrip() -> None:
    raw = encode_descriptor(desc(), BUFFERS)
    parsed = decode_descriptor(raw)
    assert len(raw) == DESCRIPTOR_SIZE
    assert raw[:4] == b"KX1D"
    assert parsed.opcode is Opcode.GEMM_INT8
    assert parsed.input_ids == (1, 2)
    assert parsed.output_id == 3
    assert parsed.scale == pytest.approx(0.25)
    assert parsed.graph_digest == GRAPH
    assert parsed.flags & WireFlags.GRAPH_BOUND
    assert parsed.flags & WireFlags.NODE_BOUND
    assert parsed.descriptor_digest == hashlib.sha256(raw[:160]).hexdigest()


def test_descriptor_tamper_and_reserved_bits_fail_closed() -> None:
    raw = bytearray(encode_descriptor(desc(), BUFFERS))
    raw[64] ^= 1
    with pytest.raises(WireFormatError, match="digest mismatch"):
        decode_descriptor(bytes(raw))

    raw = bytearray(encode_descriptor(desc(), BUFFERS))
    flags = struct.unpack_from("<H", raw, 8)[0] | (1 << 15)
    struct.pack_into("<H", raw, 8, flags)
    raw[160:192] = hashlib.sha256(raw[:160]).digest()
    with pytest.raises(WireFormatError, match="reserved flag"):
        decode_descriptor(bytes(raw))


def test_unrepresentable_attrs_flags_and_aliases_are_rejected() -> None:
    with pytest.raises(WireFormatError, match="attrs are not representable"):
        encode_descriptor(desc(attrs={"scale": 1.0, "mystery": 7}), BUFFERS)
    with pytest.raises(WireFormatError, match="logical flags"):
        encode_descriptor(desc(flags=("UNKNOWN",)), BUFFERS)
    with pytest.raises(WireFormatError, match="aliased buffer"):
        encode_descriptor(desc(), {"a": 1, "b": 1, "out": 3})


def test_reserved_opcode_cannot_be_encoded() -> None:
    reserved = desc(
        opcode=Opcode.ATTN_YARQA,
        inputs=("a",),
        output="out",
        attrs={},
    )
    with pytest.raises(WireFormatError, match="reserved"):
        encode_descriptor(reserved, BUFFERS)


def test_batch_header_integrity_order_and_last_marker() -> None:
    descriptors = [
        desc(sequence=1, nonce=10),
        desc(
            opcode=Opcode.RMSNORM,
            sequence=2,
            nonce=11,
            inputs=("out",),
            output="a",
            attrs={"eps": 1e-5, "graph_digest": GRAPH, "graph_node_id": "norm"},
        ),
    ]
    raw = encode_batch(descriptors, BUFFERS)
    parsed = decode_batch(raw)
    assert len(raw) == BATCH_HEADER_SIZE + 2 * DESCRIPTOR_SIZE
    assert raw[:4] == b"KX1S"
    assert len(parsed.descriptors) == 2
    assert not parsed.descriptors[0].flags & WireFlags.LAST_IN_BATCH
    assert parsed.descriptors[1].flags & WireFlags.LAST_IN_BATCH

    tampered = bytearray(raw)
    tampered[-1] ^= 1
    with pytest.raises(WireFormatError, match="body digest"):
        decode_batch(bytes(tampered))


def test_batch_rejects_reordering_and_early_last_marker() -> None:
    with pytest.raises(WireFormatError, match="strictly increasing"):
        encode_batch(
            [desc(sequence=2, nonce=10), desc(sequence=1, nonce=11)], BUFFERS
        )
    with pytest.raises(WireFormatError, match="only the final"):
        encode_batch(
            [
                desc(sequence=1, nonce=10, flags=("LAST_IN_BATCH",)),
                desc(sequence=2, nonce=11),
            ],
            BUFFERS,
        )


def test_golden_vectors_are_current() -> None:
    root = Path(__file__).parents[1]
    golden = json.loads(
        (root / "golden" / "kids-bin-v0.1.json").read_text(encoding="utf-8")
    )
    assert golden["schema"] == "kids-bin-golden/v0.1"
    assert golden["hardware_status"] == "UNAVAILABLE"
    single = bytes.fromhex(golden["single"]["hex"])
    batch = bytes.fromhex(golden["batch"]["hex"])
    assert hashlib.sha256(single).hexdigest() == golden["single"]["sha256"]
    assert hashlib.sha256(batch).hexdigest() == golden["batch"]["sha256"]
    assert decode_descriptor(single).as_dict() == golden["single"]["decoded"]
    assert decode_batch(batch).as_dict() == golden["batch"]["decoded"]

    decoders = {"descriptor": decode_descriptor, "batch": decode_batch}
    for mutation in golden["negative"]:
        with pytest.raises(WireFormatError, match=mutation["expected_error"]):
            decoders[mutation["decoder"]](bytes.fromhex(mutation["hex"]))

    check = subprocess.run(
        [sys.executable, str(root / "tools" / "generate_wire_golden.py"), "--check"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert check.returncode == 0, check.stdout + check.stderr
