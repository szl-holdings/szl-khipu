#!/usr/bin/env python3
"""Deployment-equivalence check — DRY-RUN STUB.

Verifies a deployed HF Space actually serves the weights this release signed.
Intended live behaviour (NOT yet implemented — no network calls are made):

    for sha, rel in parse(--weights):                # sha256sum format
        GET https://huggingface.co/spaces/{SPACE}/resolve/main/{rel}
        stream -> sha256 digest must equal `sha`
    # relaxations planned: Spaces that mount the model repo read-only may
    # instead resolve from the MODEL repo; the space's app.py is fetched to
    # resolve which weight paths it loads before comparing.

This stub VALIDATES all inputs (space id format; weights file exists and
parses as sha256sum output), prints the intended requests, and exits 0 ONLY
in --dry-run mode. Anything else exits 1 — never claim equivalence silently.
"""
import argparse
import pathlib
import re
import sys


def die(msg: str) -> "SystemExit":
    print(f"::error::check_deploy_equivalence: {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--space", required=True, help="HF space id, e.g. SZLHOLDINGS/prove-it")
    ap.add_argument("--weights", required=True, help="release/weights.sha256 (sha256sum format)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print intended requests and exit 0. REQUIRED — live "
                         "comparison is not implemented yet.")
    a = ap.parse_args()

    if not re.fullmatch(r"[\w.-]+/[\w.-]+", a.space):
        die(f"--space must look like OWNER/NAME: {a.space!r}")
    wp = pathlib.Path(a.weights)
    if not wp.is_file():
        die(f"weights digest file not found: {wp}")
    pairs = []
    for i, line in enumerate(wp.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        m = re.fullmatch(r"([0-9a-f]{64})[ \*]+(.+)", line)
        if not m:
            die(f"{wp}:{i} not in sha256sum format ('<64-hex>  <path>'): {line!r}")
        pairs.append((m.group(1), m.group(2).strip()))
    if not pairs:
        die(f"{wp} lists no weights — nothing to check equivalence against")

    print(f"deployment-equivalence (intended): space {a.space}, {len(pairs)} weight file(s)")
    for sha, rel in pairs:
        print(f"  GET https://huggingface.co/spaces/{a.space}/resolve/main/{rel} == {sha[:16]}...")

    if not a.dry_run:
        die("live equivalence checking is NOT IMPLEMENTED — refusing to claim success. "
            "Re-run with --dry-run. (Fail-closed by doctrine.)")
    print("dry-run: inputs valid; no network call made; exit 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
