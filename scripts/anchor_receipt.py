#!/usr/bin/env python3
"""Anchor a publication receipt on the SZL ledger — DRY-RUN STUB.

Intended live behaviour (NOT yet implemented — no network calls are made):

    POST {SZL_LEDGER_URL}/v1/receipts
    Authorization: Bearer $SZL_LEDGER_TOKEN          # OIDC-exchanged in CI
    Content-Type: application/json
    {"event": "model.published",
     "subject": "OWNER/MODEL@<git-sha>",
     "receipt_sha256": "<sha256 of run-manifest.json>",
     "receipt": { ...run manifest... },
     "prev_hash": "<last ledger entry hash>"}       # server verifies linkage

    Expected: 201 + {"entry_hash": ...}; 409 => receipt already anchored.

This stub VALIDATES all inputs, builds the exact payload, prints the intended
request, and exits 0 ONLY in --dry-run mode. Any other invocation exits 1 —
an unimplemented anchor must never be silently treated as done.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys


def die(msg: str) -> "SystemExit":
    print(f"::error::anchor_receipt: {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--receipt", required=True, help="release/run-manifest.json")
    ap.add_argument("--event", required=True, help="e.g. model.published")
    ap.add_argument("--subject", required=True, help="e.g. OWNER/MODEL@<git-sha>")
    ap.add_argument("--ledger-url", default=None, help="Overrides $SZL_LEDGER_URL")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print the intended request and exit 0. REQUIRED — "
                         "live anchoring is not implemented yet.")
    a = ap.parse_args()

    rp = pathlib.Path(a.receipt)
    if not rp.is_file():
        die(f"receipt not found: {rp}")
    try:
        receipt = json.loads(rp.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"receipt not valid JSON: {e}")
    if not isinstance(receipt, dict) or "schema" not in receipt:
        die("receipt does not look like an szl run manifest (no 'schema' field)")
    if not re.fullmatch(r"[a-z][\w.]*", a.event):
        die(f"--event not a dotted event name: {a.event!r}")
    if not re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{4,64}", a.subject):
        die(f"--subject must look like OWNER/MODEL@<git-sha>: {a.subject!r}")

    payload = {
        "event": a.event,
        "subject": a.subject,
        "receipt_sha256": hashlib.sha256(rp.read_bytes()).hexdigest(),
        "receipt": receipt,
        "prev_hash": (receipt.get("chain") or {}).get("prev_hash", "genesis"),
    }
    ledger = (a.ledger_url or "").rstrip("/") or "$SZL_LEDGER_URL"
    print(f"intended: POST {ledger}/v1/receipts")
    print(f"payload:  {json.dumps({k: (v if k != 'receipt' else '<manifest: see receipt_sha256>') for k, v in payload.items()}, indent=2)}")

    if not a.dry_run:
        die("live ledger anchoring is NOT IMPLEMENTED — refusing to claim success. "
            "Re-run with --dry-run. (Fail-closed by doctrine.)")
    print("dry-run: inputs valid; no network call made; exit 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
