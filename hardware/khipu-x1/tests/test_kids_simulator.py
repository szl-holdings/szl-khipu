from __future__ import annotations

import hashlib

import numpy as np
import pytest

from khipu_x1 import (
    Descriptor,
    KhipuExecutionError,
    KhipuSimulator,
    KhipuValidationError,
    Opcode,
)

DIGEST = hashlib.sha256(b"khipu-x1-wave-1").hexdigest()


def descriptor(
    sequence: int,
    opcode: Opcode,
    *,
    inputs=(),
    output=None,
    attrs=None,
    nonce=None,
) -> Descriptor:
    return Descriptor(
        sequence=sequence,
        nonce=sequence if nonce is None else nonce,
        opcode=opcode,
        model_digest=DIGEST,
        policy_digest=DIGEST,
        inputs=tuple(inputs),
        output=output,
        attrs=attrs or {},
    )


def test_int8_gemm_rmsnorm_and_receipt_chain() -> None:
    sim = KhipuSimulator()
    sim.register_buffer("a", np.array([[1, 2], [3, 4]], dtype=np.int8))
    sim.register_buffer("b", np.array([[2, 0], [1, 3]], dtype=np.int8))

    result = sim.execute(
        [
            descriptor(1, Opcode.GEMM_INT8, inputs=("a", "b"), output="mm"),
            descriptor(2, Opcode.RMSNORM, inputs=("mm",), output="norm", attrs={"eps": 1e-6}),
            descriptor(3, Opcode.SHA3_COMMIT, inputs=("norm",)),
        ]
    )

    assert result.status == "OK"
    np.testing.assert_array_equal(
        result.buffers["mm"],
        np.array([[4, 6], [10, 12]], dtype=np.int32),
    )
    assert np.isfinite(result.buffers["norm"]).all()
    assert result.chain.verify()[0]
    assert [event["kind"] for event in result.chain.events] == [
        "command_executed",
        "command_executed",
        "command_executed",
    ]
    assert result.energy_j is None


def test_reordering_is_rejected_before_admission() -> None:
    sim = KhipuSimulator()
    with pytest.raises(KhipuValidationError, match="replay or reordering"):
        sim.execute([descriptor(1, Opcode.NOP), descriptor(1, Opcode.NOP, nonce=2)])
    assert sim.chain.events == []


def test_replay_is_rejected_across_calls() -> None:
    sim = KhipuSimulator()
    sim.execute([descriptor(1, Opcode.NOP)])
    with pytest.raises(KhipuExecutionError, match="REPLAY_REJECTED"):
        sim.execute([descriptor(1, Opcode.NOP)])


def test_reserved_operation_never_silently_falls_back() -> None:
    sim = KhipuSimulator()
    with pytest.raises(KhipuExecutionError, match="UNIMPLEMENTED"):
        sim.execute([descriptor(1, Opcode.ATTN_YARQA)])
    assert sim.chain.verify()[0]
    assert sim.chain.events[-1]["kind"] == "command_blocked"
    assert "UNIMPLEMENTED" in sim.chain.events[-1]["payload"]["reason"]


def test_abort_fails_closed_and_records_abort() -> None:
    sim = KhipuSimulator()
    with pytest.raises(KhipuExecutionError, match="ABORTED"):
        sim.execute([descriptor(1, Opcode.ABORT, attrs={"reason": "operator stop"})])
    assert sim.aborted is True
    assert sim.chain.verify()[0]
    assert sim.chain.events[-1]["kind"] == "command_aborted"
    with pytest.raises(KhipuExecutionError, match="DEVICE_ABORTED"):
        sim.execute([descriptor(2, Opcode.NOP)])


def test_nonfinite_attrs_are_rejected() -> None:
    with pytest.raises(KhipuValidationError, match="non-finite"):
        descriptor(1, Opcode.RMSNORM, attrs={"eps": float("nan")}).validate()


def test_unavailable_hardware_path_cannot_be_claimed() -> None:
    with pytest.raises(KhipuExecutionError, match="UNAVAILABLE"):
        KhipuSimulator(execution_path="fpga")
