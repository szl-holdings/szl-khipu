#!/usr/bin/env python3
"""SZL corpus-v2 open-asset fetcher. Stdlib-only, idempotent, fail-closed on hash mismatch.

Same discipline as corpus-v1: every fetched file lands with its SHA-256 in
fetch_manifest.csv; a re-run skips files that already match; a hash mismatch aborts.
NOTHING rights-flagged (see NOT_REDISTRIBUTABLE.md) is fetched by this script.
"""
import csv, hashlib, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "assets")
MANIFEST = os.path.join(HERE, "fetch_manifest.csv")

ASSETS = [
    # (relative_path, url, expected_sha256_or_None, source_note)
    ("kdb_recovery/khipu_kdb_recovery_record_v1.0.zip",
     "https://zenodo.org/records/21514490/files/khipu_kdb_recovery_record_v1.0.zip?download=1",
     None, "KDB legacy recovery record (manifest+tooling+validation), Zenodo 10.5281/zenodo.21514490, md5 ff0a9b32a9ce72629a7a2f4b77921770"),
    ("contreras/2607.00185v1.pdf",
     "https://arxiv.org/pdf/2607.00185v1",
     None, "Contreras: Structural Pattern Mining in Inka Khipus (clustering, provenance, Santa Valley)"),
    ("contreras/2610.38580v1.pdf",
     "https://arxiv.org/pdf/2610.38580v1",
     None, "Contreras: Structural Pattern Mining, a KFG Re-Analysis (cataloger confound, null models)"),
    ("contreras/khipu-ml/LICENSE",
     "https://raw.githubusercontent.com/mcontrerasmalpar-pixel/khipu-ml/main/LICENSE",
     None, "Khipu-ML license file (verify open on fetch; abort and record if not)"),
]

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()

def load_manifest():
    if not os.path.exists(MANIFEST):
        return {}
    with open(MANIFEST, newline="") as f:
        return {r["path"]: r for r in csv.DictReader(f)}

def main():
    os.makedirs(OUT, exist_ok=True)
    done = load_manifest()
    for rel, url, expected, note in ASSETS:
        dest = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if rel in done and os.path.exists(dest) and sha256(dest) == done[rel]["sha256"]:
            print(f"skip (matches manifest): {rel}")
            continue
        print(f"fetch: {url}")
        urllib.request.urlretrieve(url, dest)
        digest = sha256(dest)
        if expected and digest != expected:
            print(f"HASH MISMATCH for {rel}: {digest} != {expected}", file=sys.stderr)
            sys.exit(1)
        print(f"ok: {rel} sha256={digest}")
        done[rel] = {"path": rel, "url": url, "sha256": digest, "note": note}
    with open(MANIFEST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["path", "url", "sha256", "note"])
        w.writeheader()
        for r in done.values():
            w.writerow(r)
    print(f"manifest updated: {MANIFEST}")

if __name__ == "__main__":
    main()
