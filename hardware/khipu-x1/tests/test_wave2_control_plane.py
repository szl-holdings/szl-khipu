from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from khipu_x1 import Descriptor, Opcode
from khipu_x1.graph import BufferSpec, GraphNode, GraphPlan, GraphValidationError, lower_graph
from khipu_x1.package import KhipuPackageError, build_package, verify_package
from khipu_x1.rc1 import RC1Emulator, RC1Mode, issue_hmac_authorization
from khipu_x1.source_lock import SourceLockError, load_source_lock, validate_source_lock

DIGEST = hashlib.sha256(b"wave2").hexdigest()
SECRET = b"0123456789abcdef0123456789abcdef"


def graph_plan() -> GraphPlan:
    return GraphPlan(
        name="tiny_decode",
        inputs=(
            BufferSpec("a", (2, 2), "int8"),
            BufferSpec("b", (2, 3), "int8"),
        ),
        nodes=(
            GraphNode("project", Opcode.GEMM_INT8, ("a", "b"), "mm", {"scale": 0.25}),
            GraphNode("normalize", Opcode.RMSNORM, ("mm",), "norm", {"eps": 1e-6}),
            GraphNode("commit", Opcode.SHA3_COMMIT, ("norm",), None, {}),
        ),
        outputs=("norm",),
    )


def test_graph_lowering_is_stable_and_infers_buffers() -> None:
    plan = graph_plan()
    result = lower_graph(plan, model_digest=DIGEST, policy_digest=DIGEST)
    assert [item.opcode for item in result.descriptors] == [
        Opcode.GEMM_INT8,
        Opcode.RMSNORM,
        Opcode.SHA3_COMMIT,
    ]
    assert result.buffers["mm"].shape == (2, 3)
    assert result.buffers["mm"].dtype == "float32"
    assert result.buffers["norm"].shape == (2, 3)
    assert result.graph_digest == plan.digest
    assert all(item.attrs["graph_digest"] == plan.digest for item in result.descriptors)


def test_graph_rejects_undefined_input_and_output_overwrite() -> None:
    plan = GraphPlan(
        name="bad",
        inputs=(BufferSpec("a", (2, 2), "int8"),),
        nodes=(GraphNode("badnode", Opcode.GEMM_INT8, ("a", "missing"), "a", {}),),
        outputs=("a",),
    )
    with pytest.raises(GraphValidationError):
        lower_graph(plan, model_digest=DIGEST, policy_digest=DIGEST)


def test_package_build_is_deterministic_and_verifiable(tmp_path: Path) -> None:
    first = tmp_path / "first.khipu"
    second = tmp_path / "second.khipu"
    kwargs = dict(
        package_id="tiny-decode-v1",
        model_digest=DIGEST,
        policy_digest=DIGEST,
        graph=graph_plan(),
        payloads={"weights/tiny.bin": b"weights", "config/model.json": b"{}\n"},
        roles={"weights/tiny.bin": "weights", "config/model.json": "config"},
        required_ops=(Opcode.GEMM_INT8, Opcode.RMSNORM, Opcode.SHA3_COMMIT),
    )
    report_one = build_package(first, **kwargs)
    report_two = build_package(second, **kwargs)
    assert first.read_bytes() == second.read_bytes()
    assert report_one.package_digest == report_two.package_digest
    assert report_one.verified is True
    assert report_one.execution_status == "PACKAGE_VERIFIED_ONLY"
    assert verify_package(first).files_verified == 3


def test_package_rejects_zip_slip_and_duplicate_names() -> None:
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w") as archive:
        archive.writestr("../escape", b"bad")
        archive.writestr("manifest.json", b"{}")
    with pytest.raises(KhipuPackageError, match="unsafe archive path"):
        verify_package(raw.getvalue())

    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w") as archive:
        archive.writestr("manifest.json", b"{}")
        archive.writestr("manifest.json", b"{}")
    with pytest.raises(KhipuPackageError, match="duplicate"):
        verify_package(raw.getvalue())


def descriptors() -> tuple[Descriptor, ...]:
    lowered = lower_graph(graph_plan(), model_digest=DIGEST, policy_digest=DIGEST)
    return lowered.descriptors


def test_rc1_allows_once_then_blocks_replay() -> None:
    stream = descriptors()
    envelope = issue_hmac_authorization(
        secret=SECRET,
        authorization_id="auth-1",
        device_id="rc1-test",
        issued_at=100,
        expires_at=200,
        sequence=1,
        nonce=1,
        descriptors=stream,
        allowed_opcodes=[item.opcode for item in stream],
        mode=RC1Mode.ACT,
        key_id="test-key",
    )
    rc1 = RC1Emulator(device_id="rc1-test", key_id="test-key", secret=SECRET)
    allowed = rc1.authorize(envelope, stream, now=150)
    replay = rc1.authorize(envelope, stream, now=150)
    assert allowed.allowed is True
    assert allowed.reason == "AUTHORIZED_EMULATOR_ONLY"
    assert replay.allowed is False
    assert replay.reason == "REPLAY_REJECTED"
    assert rc1.chain.verify()[0]
    assert [event["kind"] for event in rc1.chain.events] == [
        "authorization_allowed",
        "authorization_blocked",
    ]


def test_rc1_blocks_tamper_mode_and_physical_claim() -> None:
    stream = descriptors()
    envelope = issue_hmac_authorization(
        secret=SECRET,
        authorization_id="auth-2",
        device_id="rc1-test",
        issued_at=100,
        expires_at=200,
        sequence=2,
        nonce=2,
        descriptors=stream,
        allowed_opcodes=[item.opcode for item in stream],
        mode=RC1Mode.OBSERVE,
        key_id="test-key",
    )
    rc1 = RC1Emulator(device_id="rc1-test", key_id="test-key", secret=SECRET)
    assert rc1.authorize(replace(envelope, signature="0" * 64), stream, now=150).reason == "SIGNATURE_INVALID"
    assert rc1.authorize(envelope, stream, now=150).reason == "MODE_NOT_ACT"

    physical = issue_hmac_authorization(
        secret=SECRET,
        authorization_id="auth-3",
        device_id="rc1-test",
        issued_at=100,
        expires_at=200,
        sequence=3,
        nonce=3,
        descriptors=stream,
        allowed_opcodes=[item.opcode for item in stream],
        mode=RC1Mode.ACT,
        key_id="test-key",
        constraints={"physical_actuation": True},
    )
    assert rc1.authorize(physical, stream, now=150).reason == "PHYSICAL_ACTUATION_UNAVAILABLE"


def test_source_lock_is_exact_sorted_and_offline_valid() -> None:
    path = Path(__file__).parents[1] / "source-lock.json"
    lock = load_source_lock(path)
    assert lock["hardware_status"] == "UNAVAILABLE"
    assert any(item["repository"] == "szl-holdings/szl-khipu" for item in lock["repositories"])

    broken = json.loads(json.dumps(lock))
    broken["repositories"][0]["commit"] = "main"
    with pytest.raises(SourceLockError):
        validate_source_lock(broken)
