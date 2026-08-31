#!/usr/bin/env python3
"""Assert a computed dataset digest matches the dataset-admission receipt.

Compares the `dataset_digest` field of --computed (output of
scripts/dataset_digest.py) against the digest recorded in
receipts/dataset-admission.json. The receipt field may be `dataset_digest`
or `digest` at the top level or under a `payload`/`subject` object.
Fail-closed: exit 1 on missing files, missing digest fields, or any mismatch.

Usage:
  python scripts/assert_digest.py \
    --computed /tmp/dataset.digest.json \
    --receipt receipts/dataset-admission.json
"""
import argparse
import json
import pathlib
import sys


def die(msg: str) -> "SystemExit":
    print(f"::error::assert_digest: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load(p: str) -> dict:
    fp = pathlib.Path(p)
    if not fp.is_file():
        die(f"file not found: {fp}")
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{fp} is not valid JSON: {e}")


def find_digest(doc: dict, label: str) -> str:
    for scope in (doc, doc.get("payload") or {}, doc.get("subject") or {}):
        for key in ("dataset_digest", "digest"):
            v = scope.get(key) if isinstance(scope, dict) else None
            if isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdefABCDEF" for c in v):
                return v.lower()
    die(f"{label} carries no sha256 digest field (looked for dataset_digest/digest)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--computed", required=True)
    ap.add_argument("--receipt", required=True)
    a = ap.parse_args()

    computed = find_digest(load(a.computed), "computed digest JSON")
    receipt = find_digest(load(a.receipt), "admission receipt")

    print(f"computed: {computed}")
    print(f"receipt:  {receipt}")
    if computed != receipt:
        die("MISMATCH — dataset digest does not match the admission receipt; pipeline blocked")
    print("OK digest matches the dataset-admission receipt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
