#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""One-shot patch for the KHIPU-X1 safetensors symlink boundary."""
from __future__ import annotations

from pathlib import Path


def replace_exact(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one replacement target, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> int:
    common = Path("hardware/khipu-x1/src/khipu_x1/_safetensors_common.py")
    replace_exact(
        common,
        '''    candidate = root.joinpath(*pure.parts)
    if candidate.is_symlink():
        raise SafetensorsInventoryError(
            f"symbolic-link shard is forbidden: {relative}"
        )
    resolved_root = root.resolve(strict=True)
''',
        '''    candidate = root
    for part in pure.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise SafetensorsInventoryError(
                f"symbolic-link shard component is forbidden: {relative}"
            )
    resolved_root = root.resolve(strict=True)
''',
    )

    inventory = Path("hardware/khipu-x1/src/khipu_x1/safetensors_inventory.py")
    replace_exact(
        inventory,
        '''    root = Path(model_root).resolve(strict=True)
    if not root.is_dir():
''',
        '''    supplied_root = Path(model_root)
    if supplied_root.is_symlink():
        raise SafetensorsInventoryError("symbolic-link model roots are forbidden")
    try:
        root = supplied_root.resolve(strict=True)
    except OSError as exc:
        raise SafetensorsInventoryError("model_root is unavailable") from exc
    if not root.is_dir():
''',
    )

    tests = Path("hardware/khipu-x1/tests/test_safetensors_inventory.py")
    text = tests.read_text(encoding="utf-8")
    if "test_symlinked_model_root_is_rejected" in text:
        raise SystemExit("symlink regression tests already exist")
    addition = r'''


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
'''
    tests.write_text(text.rstrip() + addition + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
