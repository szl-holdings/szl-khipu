from __future__ import annotations

import json
from pathlib import Path

import pytest

from khipu_x1.tokenizer_binding import (
    TokenizerBindingError,
    bind_tokenizer_artifacts,
    verify_tokenizer_binding,
)


def _write_fixture(root: Path) -> None:
    (root / "vocab.json").write_text(
        json.dumps({"<pad>": 0, "<s>": 1, "</s>": 2, "hello": 3}),
        encoding="utf-8",
    )
    (root / "merges.txt").write_text("#version: 0.2\nh e\n", encoding="utf-8")
    (root / "tokenizer_config.json").write_text(
        json.dumps(
            {
                "bos_token": "<s>",
                "bos_token_id": 1,
                "eos_token": "</s>",
                "eos_token_id": 2,
                "pad_token": "<pad>",
                "pad_token_id": 0,
                "chat_template": "{% for message in messages %}{{ message.content }}{% endfor %}",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (root / "special_tokens_map.json").write_text(
        json.dumps(
            {
                "bos_token": "<s>",
                "eos_token": "</s>",
                "pad_token": "<pad>",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (root / "chat_template.jinja").write_text(
        "{% for message in messages %}{{ message.content }}{% endfor %}",
        encoding="utf-8",
    )


def test_binding_is_deterministic_and_reverifiable(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    first = bind_tokenizer_artifacts(tmp_path)
    second = bind_tokenizer_artifacts(tmp_path)

    assert first.manifest_digest == second.manifest_digest
    assert first.total_bytes > 0
    assert first.receipt_chain.verify()[0]
    assert first.tokenizer_execution == "NOT_PERFORMED"
    assert len(first.chat_templates) == 2
    tokens = {token.name: token for token in first.special_tokens}
    assert tokens["bos_token"].token_id == 1
    assert tokens["eos_token"].token_id == 2
    assert tokens["pad_token"].token_id == 0
    assert tokens["eos_token"].sources == (
        "special_tokens_map.json",
        "tokenizer_config.json",
    )

    observed = verify_tokenizer_binding(tmp_path, first)
    assert observed.manifest_digest == first.manifest_digest


def test_post_binding_tamper_is_detected(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    binding = bind_tokenizer_artifacts(tmp_path)
    (tmp_path / "vocab.json").write_text(
        json.dumps({"<pad>": 0, "changed": 1}),
        encoding="utf-8",
    )
    with pytest.raises(TokenizerBindingError, match="manifest mismatch"):
        verify_tokenizer_binding(tmp_path, binding)


def test_duplicate_json_and_conflicting_special_tokens_fail_closed(tmp_path: Path) -> None:
    (tmp_path / "vocab.json").write_text("{}", encoding="utf-8")
    (tmp_path / "tokenizer_config.json").write_text(
        '{"eos_token":"</s>","eos_token":"<end>"}',
        encoding="utf-8",
    )
    with pytest.raises(TokenizerBindingError, match="duplicate JSON key"):
        bind_tokenizer_artifacts(tmp_path)

    other = tmp_path / "conflict"
    other.mkdir()
    (other / "vocab.json").write_text("{}", encoding="utf-8")
    (other / "tokenizer_config.json").write_text(
        json.dumps({"eos_token": "</s>"}),
        encoding="utf-8",
    )
    (other / "special_tokens_map.json").write_text(
        json.dumps({"eos_token": "<end>"}),
        encoding="utf-8",
    )
    with pytest.raises(TokenizerBindingError, match="conflicting"):
        bind_tokenizer_artifacts(other)


def test_missing_vocabulary_and_resource_bounds_fail_closed(tmp_path: Path) -> None:
    (tmp_path / "tokenizer_config.json").write_text("{}", encoding="utf-8")
    with pytest.raises(TokenizerBindingError, match="no supported"):
        bind_tokenizer_artifacts(tmp_path)

    bounded = tmp_path / "bounded"
    bounded.mkdir()
    (bounded / "vocab.txt").write_text("a\nb\nc\n", encoding="utf-8")
    with pytest.raises(TokenizerBindingError, match="exceeds byte bound"):
        bind_tokenizer_artifacts(bounded, max_file_bytes=2)


def test_symbolic_link_artifact_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "real-vocab.json"
    target.write_text("{}", encoding="utf-8")
    link = tmp_path / "vocab.json"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links unavailable on this platform")
    with pytest.raises(TokenizerBindingError, match="symbolic-link"):
        bind_tokenizer_artifacts(tmp_path)


def test_special_token_id_must_be_non_negative_integer(tmp_path: Path) -> None:
    (tmp_path / "vocab.json").write_text("{}", encoding="utf-8")
    (tmp_path / "tokenizer_config.json").write_text(
        json.dumps({"eos_token": "</s>", "eos_token_id": True}),
        encoding="utf-8",
    )
    with pytest.raises(TokenizerBindingError, match="non-negative integer"):
        bind_tokenizer_artifacts(tmp_path)


@pytest.mark.parametrize("total_bound,expected_hashed", [(1, []), (6, ["vocab.json"])])
def test_aggregate_limit_is_enforced_before_hashing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    total_bound: int, expected_hashed: list[str],
) -> None:
    import khipu_x1.tokenizer_binding as binder

    (tmp_path / "vocab.json").write_bytes(b"{}")
    (tmp_path / "merges.txt").write_bytes(b"abcde")
    hashed: list[str] = []
    original_hash = binder._hash_file

    def record_hash(path: Path, *, max_file_bytes: int):
        hashed.append(path.name)
        return original_hash(path, max_file_bytes=max_file_bytes)

    monkeypatch.setattr(binder, "_hash_file", record_hash)
    with pytest.raises(TokenizerBindingError, match="total byte bound"):
        bind_tokenizer_artifacts(tmp_path, max_total_bytes=total_bound)
    assert hashed == expected_hashed


def test_standalone_template_above_capture_limit_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import khipu_x1.tokenizer_binding as binder

    monkeypatch.setattr(binder, "_MAX_CAPTURE_BYTES", 8)
    (tmp_path / "vocab.json").write_bytes(b"{}")
    (tmp_path / "chat_template.jinja").write_bytes(b"123456789")
    with pytest.raises(TokenizerBindingError, match="chat-template parsing ceiling"):
        bind_tokenizer_artifacts(tmp_path)


def test_standalone_template_at_capture_limit_is_bound_and_utf8_checked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import khipu_x1.tokenizer_binding as binder

    monkeypatch.setattr(binder, "_MAX_CAPTURE_BYTES", 8)
    (tmp_path / "vocab.json").write_bytes(b"{}")
    template = tmp_path / "chat_template.jinja"
    template.write_bytes(b"12345678")
    binding = bind_tokenizer_artifacts(tmp_path)
    assert len(binding.chat_templates) == 1
    assert binding.chat_templates[0].byte_count == 8
    template.write_bytes(b"1234567\xff")
    with pytest.raises(TokenizerBindingError, match="not UTF-8"):
        bind_tokenizer_artifacts(tmp_path)
