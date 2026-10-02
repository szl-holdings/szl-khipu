#!/usr/bin/env python3
"""Publish one reviewed synthetic-fixture card from immutable GitHub source.

Dry runs are offline. Apply requires an exact source SHA, reviewed Hub parent and
README digest. Only README.md is managed; fixtures, receipts and model admission
are preserved. Failed/ambiguous mutations are recorded and never retried.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "szl-holdings/szl-khipu"
MODELS = ("chakana", "qantu", "tinku", "waman")
CLIENT_VERSION = "1.29.0"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
MAX_CARD_BYTES = 100_000
HUB_ENDPOINT = "https://huggingface.co"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _git(*args: str) -> bytes:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True,
                          capture_output=True, timeout=40).stdout


def source_card(model: str, source_sha: str) -> bytes:
    if model not in MODELS or not SHA40.fullmatch(source_sha):
        raise ValueError("fixed model allowlist and immutable source SHA required")
    if _git("rev-parse", "HEAD").decode().strip() != source_sha:
        raise ValueError("source SHA must equal checked-out Git HEAD")
    cards = []
    for directory in ("atelier/hf", "atelier-space/cards"):
        path = f"{directory}/{model}.md"
        mode = _git("ls-tree", source_sha, "--", path).split(None, 1)[0]
        if mode != b"100644":
            raise ValueError("card must be a regular immutable Git file")
        raw = _git("show", f"{source_sha}:{path}")
        if len(raw) > MAX_CARD_BYTES:
            raise ValueError("oversized card")
        cards.append(raw)
    if cards[0] != cards[1]:
        raise ValueError("paired immutable card copies differ")
    facts = metadata(cards[0])
    szl = facts.get("szl", {})
    if (facts.get("license") != "apache-2.0" or "test-fixture" not in facts.get("tags", [])
            or szl.get("artifact_class") != "SYNTHETIC_NUMPY_SILHOUETTE"
            or szl.get("synthetic_silhouette") != model + ".npz"
            or szl.get("publication_eligible") is not False
            or szl.get("production_weights") != "UNAVAILABLE"):
        raise ValueError("source card lacks the reviewed synthetic-fixture boundaries")
    return cards[0]


def require_fresh_source(source_sha: str) -> None:
    result = _git("ls-remote", f"https://github.com/{REPOSITORY}.git", "refs/heads/main")
    expected = f"{source_sha}\trefs/heads/main".encode()
    if result.strip() != expected:
        raise ValueError("source SHA is not current canonical main")
    if _git("rev-parse", "HEAD").decode().strip() != source_sha:
        raise ValueError("checked-out source changed")
    if _git("show", f"{source_sha}:scripts/publish_reference_card.py") != Path(__file__).read_bytes().replace(b"\r\n", b"\n"):
        raise ValueError("executed publisher differs from immutable source")


def metadata(raw: bytes) -> dict:
    import yaml
    class UniqueLoader(yaml.SafeLoader):
        pass
    def mapping(loader, node, deep=False):
        pairs = loader.construct_pairs(node, deep=deep)
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate card metadata key")
            result[key] = value
        return result
    UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    lines = raw.decode("utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("YAML card metadata required")
    closing = lines.index("---", 1)
    parsed = yaml.load("\n".join(lines[1:closing]), Loader=UniqueLoader)
    if not isinstance(parsed, dict):
        raise ValueError("card metadata must be a mapping")
    return parsed


def preserve_metadata(before: dict, after: dict, path: tuple = ()) -> None:
    for key, value in before.items():
        current = path + (key,)
        if key not in after:
            raise ValueError("published metadata field would be removed")
        replacement = after[key]
        if isinstance(value, dict):
            if not isinstance(replacement, dict):
                raise ValueError("published metadata mapping would be replaced")
            preserve_metadata(value, replacement, current)
        elif current == ("tags",):
            if not isinstance(replacement, list) or not set(value).issubset(set(replacement)):
                raise ValueError("published metadata tag would be removed")
        elif current == ("szl", "receipt_hash_binding"):
            if replacement != value and replacement != "CHECKED_AT_EXACT_REVISION_2026_10_02":
                raise ValueError("unreviewed receipt binding change")
        elif replacement != value:
            raise ValueError("published metadata value would be changed")


def file_manifest(info) -> dict:
    result = {}
    for entry in info.siblings or []:
        name = entry.rfilename
        if name in result or not entry.blob_id:
            raise ValueError("provider file metadata is missing or ambiguous")
        lfs = getattr(entry, "lfs", None)
        result[name] = {"blob_id": entry.blob_id, "size": entry.size,
                        "lfs_sha256": getattr(lfs, "sha256", None)}
    if "README.md" not in result:
        raise ValueError("reviewed README is missing")
    return result


def require_bounded_readme(manifest: dict) -> None:
    size = manifest["README.md"]["size"]
    if type(size) is not int or not 0 <= size <= MAX_CARD_BYTES:
        raise ValueError("provider README size is unavailable or oversized")


def publish_one(api, download, add_operation, *, model: str, source_sha: str,
                expected_parent: str, expected_readme_sha256: str,
                card: bytes, checkpoint, freshness=require_fresh_source) -> dict:
    if model not in MODELS or not SHA40.fullmatch(source_sha):
        raise ValueError("immutable allowlisted target required")
    if not SHA40.fullmatch(expected_parent) or not SHA256.fullmatch(expected_readme_sha256):
        raise ValueError("reviewed immutable provider parent and README digest required")
    repo_id = "SZLHOLDINGS/" + model
    freshness(source_sha)
    before = api.model_info(repo_id, files_metadata=True, timeout=30)
    if before.sha != expected_parent:
        raise ValueError("provider head changed from reviewed parent")
    before_files = file_manifest(before)
    require_bounded_readme(before_files)
    old = Path(download(repo_id=repo_id, repo_type="model", filename="README.md",
                        revision=expected_parent, token=api.token,
                        endpoint=HUB_ENDPOINT)).read_bytes()
    if len(old) > MAX_CARD_BYTES or digest(old) != expected_readme_sha256:
        raise ValueError("reviewed README bytes changed")
    preserve_metadata(metadata(old), metadata(card))
    receipt = {"schema": "szl.reference-card-publication/v1",
               "source_repository": REPOSITORY, "source_sha": source_sha,
               "source_path": f"atelier/hf/{model}.md", "repo_id": repo_id,
               "expected_hf_parent": expected_parent,
               "before_readme_sha256": digest(old), "source_readme_sha256": digest(card),
               "managed_files": ["README.md"], "model_admission_changed": False,
               "metadata_preserved": True, "state": "PREPARED"}
    checkpoint(receipt)
    freshness(source_sha)
    if old == card:
        if api.model_info(repo_id, timeout=30).sha != expected_parent:
            raise ValueError("provider head changed during unchanged readback")
        receipt.update(state="ALREADY_MATCHED", hf_revision=expected_parent,
                       immutable_byte_parity=True, unmanaged_files_preserved=True,
                       mutation_confirmed=False)
        checkpoint(receipt)
        return receipt
    operation = add_operation(path_in_repo="README.md", path_or_fileobj=card)
    # This private marker is reviewed against one exact pinned SDK. create_commit
    # may return a no-op shortcut after a race without submitting a parent-CAS.
    if getattr(operation, "_is_committed", None) is not False:
        raise ValueError("pinned SDK commit-confirmation capability unavailable")
    if api.model_info(repo_id, timeout=30).sha != expected_parent:
        raise ValueError("provider head changed before conditional mutation")
    freshness(source_sha)
    receipt["state"] = "MUTATION_ATTEMPTED"
    checkpoint(receipt)
    result = api.create_commit(repo_id=repo_id, repo_type="model", revision="main",
                               create_pr=False, parent_commit=expected_parent,
                               operations=[operation],
                               commit_message=f"mirror reviewed fixture card {model} from {source_sha}")
    revision = str(getattr(result, "oid", ""))
    receipt.update(hf_revision=revision, mutation_confirmed=operation._is_committed is True)
    checkpoint(receipt)
    if not SHA40.fullmatch(revision) or revision == expected_parent or operation._is_committed is not True:
        raise ValueError("conditional mutation was not confirmed; reconcile provider before retry")
    current = api.model_info(repo_id, revision=revision, files_metadata=True, timeout=30)
    if current.sha != revision:
        raise ValueError("provider returned a different immutable revision")
    after_files = file_manifest(current)
    require_bounded_readme(after_files)
    if {k: v for k, v in before_files.items() if k != "README.md"} != {
            k: v for k, v in after_files.items() if k != "README.md"}:
        raise ValueError("unmanaged provider files changed")
    observed = Path(download(repo_id=repo_id, repo_type="model", filename="README.md",
                             revision=revision, token=api.token,
                             endpoint=HUB_ENDPOINT)).read_bytes()
    if observed != card or api.model_info(repo_id, timeout=30).sha != revision:
        raise ValueError("immutable bytes or current provider head differ")
    freshness(source_sha)
    receipt.update(state="PUBLISHED_AND_READ_BACK", immutable_byte_parity=True,
                   unmanaged_files_preserved=True)
    checkpoint(receipt)
    return receipt


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--expected-hf-parent")
    parser.add_argument("--expected-readme-sha256")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    card = source_card(args.model, args.source_sha)
    if not args.apply:
        metadata(card)
        print(json.dumps({"state": "OFFLINE_SOURCE_VALIDATED", "model": args.model,
                          "source_sha": args.source_sha, "readme_sha256": digest(card)}))
        return 0
    if not (args.expected_hf_parent and SHA40.fullmatch(args.expected_hf_parent)
            and args.expected_readme_sha256 and SHA256.fullmatch(args.expected_readme_sha256)
            and args.receipt):
        raise ValueError("apply requires reviewed parent, README digest and a new receipt path")
    if args.receipt.exists() or not args.receipt.parent.is_dir():
        raise ValueError("receipt must be new and its parent must already exist")
    require_fresh_source(args.source_sha)
    if importlib.metadata.version("huggingface-hub") != CLIENT_VERSION:
        raise ValueError("install the reviewed exact Hub client version before apply")
    lock = ROOT / ".szl-reference-card.lock"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.close(fd)
        from huggingface_hub import HfApi, CommitOperationAdd, hf_hub_download, get_token
        token = get_token()
        if not token:
            raise ValueError("authorized Hub credential unavailable")
        last_written = None
        def checkpoint(receipt):
            nonlocal last_written
            receipt["observed_at"] = datetime.now(timezone.utc).isoformat()
            encoded = (json.dumps(receipt, indent=2) + "\n").encode("utf-8")
            if last_written is None:
                with args.receipt.open("xb") as handle:
                    handle.write(encoded)
                last_written = encoded
                return
            if args.receipt.read_bytes() != last_written:
                raise ValueError("publication receipt changed outside this invocation")
            temp = args.receipt.with_name(args.receipt.name + f".{os.getpid()}.tmp")
            with temp.open("xb") as handle:
                handle.write(encoded)
            os.replace(temp, args.receipt)
            last_written = encoded
        receipt = publish_one(HfApi(token=token, endpoint=HUB_ENDPOINT),
                              hf_hub_download, CommitOperationAdd, model=args.model,
                              source_sha=args.source_sha, expected_parent=args.expected_hf_parent,
                              expected_readme_sha256=args.expected_readme_sha256,
                              card=card, checkpoint=checkpoint)
        print(json.dumps({"state": receipt["state"], "hf_revision": receipt["hf_revision"],
                          "receipt": str(args.receipt)}))
        return 0
    finally:
        lock.unlink()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        status = getattr(getattr(error, "response", None), "status_code", None)
        print(json.dumps({"state": "BLOCKED", "error_type": type(error).__name__,
                          "http_status": status}), file=sys.stderr)
        raise SystemExit(2)
