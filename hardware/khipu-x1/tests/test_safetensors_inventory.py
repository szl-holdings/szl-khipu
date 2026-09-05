from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

import pytest

from khipu_x1.safetensors_inventory import (
    SafetensorsInventoryError,
    inventory_local_model,
    inventory_safetensors_file,
)


def _write_safetensors(
    path: Path,
    tensors: list[tuple[str, str, tuple[int, ...], bytes]],
    *,
    metadata: dict[str, str] | None = None,
) -> bytes:
    header: dict[str, object] = {}
    body = bytearray()
    for name, dtype, shape, payload in tensors:
        start = len(body)
        body.extend(payload)
        header[name] = {
            "dtype": dtype,
            "shape": list(shape),
            "data_offsets": [start, len(body)],
        }
    if metadata:
        header["__metadata__"] = metadata
    raw = json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")
    raw += b" " * ((8 - len(raw) % 8) % 8)
    encoded = struct.pack("<Q", len(raw)) + raw + bytes(body)
    path.write_bytes(encoded)
    return encoded


def _write_raw(path: Path, header_raw: bytes, body: bytes) -> None:
    header_raw += b" " * ((8 - len(header_raw) % 8) % 8)
    path.write_bytes(struct.pack("<Q", len(header_raw)) + header_raw + body)


def test_single_file_inventory_exact_and_deterministic(tmp_path: Path) -> None:
    model = tmp_path / "model.safetensors"
    encoded = _write_safetensors(
        model,
        [
            ("a", "I8", (2, 2), bytes([1, 2, 3, 4])),
            ("b", "F32", (2,), struct.pack("<2f", 1.0, -2.0)),
        ],
        metadata={"format": "pt"},
    )

    first = inventory_safetensors_file(model, hash_file=True, hash_tensors=True)
    second = inventory_safetensors_file(model, hash_file=True, hash_tensors=True)

    assert first.tensor_count == 2
    assert first.parameter_count == 6
    assert first.data_size == 12
    assert first.parameters_by_dtype == {"I8": 4, "F32": 2}
    assert first.file_sha256 == hashlib.sha256(encoded).hexdigest()
    assert first.content_binding_status == "FULL_FILE_SHA256"
    assert first.as_dict() == second.as_dict()


def test_rejects_hole_overlap_and_duplicate_keys(tmp_path: Path) -> None:
    hole = tmp_path / "hole.safetensors"
    _write_raw(
        hole,
        b'{"a":{"dtype":"I8","shape":[1],"data_offsets":[1,2]}}',
        b"\x00\x01",
    )
    with pytest.raises(SafetensorsInventoryError, match="hole"):
        inventory_safetensors_file(hole)

    overlap = tmp_path / "overlap.safetensors"
    _write_raw(
        overlap,
        b'{"a":{"dtype":"I8","shape":[2],"data_offsets":[0,2]},'
        b'"b":{"dtype":"I8","shape":[1],"data_offsets":[1,2]}}',
        b"\x00\x01",
    )
    with pytest.raises(SafetensorsInventoryError, match="overlap"):
        inventory_safetensors_file(overlap)

    duplicate = tmp_path / "duplicate.safetensors"
    _write_raw(
        duplicate,
        b'{"a":{"dtype":"I8","shape":[1],"data_offsets":[0,1]},'
        b'"a":{"dtype":"I8","shape":[1],"data_offsets":[0,1]}}',
        b"\x00",
    )
    with pytest.raises(SafetensorsInventoryError, match="duplicate JSON key"):
        inventory_safetensors_file(duplicate)


def test_sharded_inventory_and_traversal_rejection(tmp_path: Path) -> None:
    _write_safetensors(
        tmp_path / "model-00001-of-00002.safetensors",
        [("a", "I8", (2,), b"\x01\x02")],
    )
    _write_safetensors(
        tmp_path / "model-00002-of-00002.safetensors",
        [("b", "F32", (1,), struct.pack("<f", 3.0))],
    )
    index = {
        "metadata": {"total_size": 6},
        "weight_map": {
            "a": "model-00001-of-00002.safetensors",
            "b": "model-00002-of-00002.safetensors",
        },
    }
    (tmp_path / "model.safetensors.index.json").write_text(
        json.dumps(index),
        encoding="utf-8",
    )

    inventory = inventory_local_model(
        tmp_path,
        hash_files=True,
        hash_tensors=True,
    )
    assert inventory.sharded is True
    assert inventory.shard_count == 2
    assert inventory.tensor_count == 2
    assert inventory.parameter_count == 3
    assert inventory.data_bytes == 6
    assert inventory.content_binding_status == "FULL_FILE_SHA256"

    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "model.safetensors.index.json").write_text(
        json.dumps(
            {
                "metadata": {},
                "weight_map": {"a": "../model-00001-of-00002.safetensors"},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(SafetensorsInventoryError, match="unsafe shard path"):
        inventory_local_model(bad)


def test_ambiguous_root_is_rejected(tmp_path: Path) -> None:
    _write_safetensors(
        tmp_path / "model.safetensors",
        [("a", "I8", (1,), b"\x00")],
    )
    (tmp_path / "model.safetensors.index.json").write_text(
        json.dumps(
            {
                "metadata": {},
                "weight_map": {"a": "shard.safetensors"},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(SafetensorsInventoryError, match="ambiguous"):
        inventory_local_model(tmp_path)


def test_symlinked_model_root_is_rejected(tmp_path: Path) -> None:
    real = tmp_path / "real-model"
    real.mkdir()
    _write_safetensors(
        real / "model.safetensors",
        [("a", "I8", (1,), b"\x00")],
    )
    alias = tmp_path / "model-alias"
    try:
        alias.symlink_to(real, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks unavailable on this platform: {exc}")

    with pytest.raises(SafetensorsInventoryError, match="model roots"):
        inventory_local_model(alias)


def test_symlinked_shard_directory_component_is_rejected(tmp_path: Path) -> None:
    real = tmp_path / "real-shards"
    real.mkdir()
    _write_safetensors(
        real / "part.safetensors",
        [("a", "I8", (1,), b"\x00")],
    )
    alias = tmp_path / "shards"
    try:
        alias.symlink_to(real, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks unavailable on this platform: {exc}")
    (tmp_path / "model.safetensors.index.json").write_text(
        json.dumps(
            {
                "metadata": {"total_size": 1},
                "weight_map": {"a": "shards/part.safetensors"},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(SafetensorsInventoryError, match="shard component"):
        inventory_local_model(tmp_path)
