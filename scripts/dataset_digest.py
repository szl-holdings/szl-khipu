#!/usr/bin/env python3
"""Compute a sha256 manifest of the dataset files listed in a manifest JSON.

Fail-closed: exits 1 if the manifest is missing/malformed, a listed file is
missing, or a listed file carries a recorded sha256 that does not match the
recomputed digest. Stdlib only.

Manifest format (data/dataset-manifest.json):
  {"files": ["path/rel/to/manifest", ...]}                       # digest-only
  {"files": [{"path": "...", "sha256": "<64 hex>"}, ...]}        # also verifies

Output (--out):
  {"manifest": <path>, "algorithm": "sha256", "file_count": N,
   "files": [{"path": ..., "sha256": ..., "bytes": ...}, ...],
   "dataset_digest": "<sha256 over canonical file list>"}
"""
import argparse
import hashlib
import json
import pathlib
import sys


def die(msg: str) -> "SystemExit":
    print(f"::error::dataset_digest: {msg}", file=sys.stderr)
    raise SystemExit(1)


def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", required=True, help="data/dataset-manifest.json")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    mp = pathlib.Path(a.manifest)
    if not mp.is_file():
        die(f"manifest not found: {mp} (fail-closed: no manifest, no publication)")
    try:
        m = json.loads(mp.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"manifest is not valid JSON: {e}")
    entries = m.get("files")
    if not isinstance(entries, list) or not entries:
        die("manifest has no non-empty 'files' list")

    base = mp.parent
    out_files = []
    for e in entries:
        if isinstance(e, str):
            rel, recorded = e, None
        elif isinstance(e, dict) and isinstance(e.get("path"), str):
            rel, recorded = e["path"], e.get("sha256")
        else:
            die(f"bad manifest entry (need string or {{path, sha256?}}): {e!r}")
        fp = (base / rel).resolve()
        if not fp.is_file():
            die(f"listed dataset file missing: {rel}")
        digest = sha256_file(fp)
        if recorded is not None and recorded.lower() != digest:
            die(f"sha256 mismatch for {rel}: recorded {recorded}, computed {digest}")
        out_files.append({"path": rel, "sha256": digest, "bytes": fp.stat().st_size})

    out_files.sort(key=lambda f: f["path"])
    agg = hashlib.sha256()
    for f in out_files:
        agg.update(f["path"].encode())
        agg.update(b"\0")
        agg.update(f["sha256"].encode())
        agg.update(b"\n")

    doc = {
        "manifest": str(mp),
        "algorithm": "sha256",
        "file_count": len(out_files),
        "files": out_files,
        "dataset_digest": agg.hexdigest(),
    }
    op = pathlib.Path(a.out)
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"OK {len(out_files)} files, dataset_digest={doc['dataset_digest'][:16]}... -> {op}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
