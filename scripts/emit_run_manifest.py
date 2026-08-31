#!/usr/bin/env python3
"""Assemble release/run-manifest.json — the object the final publish job asserts.

Emits exactly the schema the model-publish-gate publish job checks:
  eval.heldout_passed            (from release/heldout-eval.json)
  eval.refusal_no_regression     (from heldout-eval.json merged w/ refusal evidence)
  model_bom_sha256               (sha256 of the CycloneDX BOM file)
  signatures.manifest            (True only with --signed-manifest, set by the
                                  sign job AFTER cosign sign-blob succeeds)
  conformance.all_vectors_passed (True only with --conformance-passed, set by
                                  the conformance job after run_vectors.py)
  release.kind                   (patch|minor|major; 'major' needs allow_major)

Fail-closed: exit 1 if required inputs are missing/malformed.
Stdlib only. Timestamps are UTC ISO-8601; canonical JSON (sorted keys) so the
DSSE PAE over this file is stable across runs (see conformance vectors).
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import sys


def die(msg: str) -> "SystemExit":
    print(f"::error::emit_run_manifest: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load_json(p: str, label: str) -> dict:
    fp = pathlib.Path(p)
    if not fp.is_file():
        die(f"{label} not found: {fp}")
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{label} is not valid JSON: {e}")


def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--eval", dest="eval_json", required=True, help="release/heldout-eval.json")
    ap.add_argument("--bom", required=True, help="bom/model-bom.cdx.json")
    ap.add_argument("--git-sha", required=True)
    ap.add_argument("--workflow-run", required=True, help="URL of the GH Actions run (provenance)")
    ap.add_argument("--release-kind", default="patch", choices=["patch", "minor", "major"])
    ap.add_argument("--signed-manifest", action="store_true",
                    help="Set ONLY by the sign job after cosign sign-blob succeeded.")
    ap.add_argument("--conformance-passed", action="store_true",
                    help="Set ONLY by the conformance job after run_vectors --require-all-pass.")
    ap.add_argument("--prev-hash", default=None,
                    help="sha256 of the previous run manifest (receipt-chain linkage); "
                         "'genesis' for the first publication of this model line.")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    md = pathlib.Path(a.model_dir)
    if not md.is_dir():
        die(f"model dir not found: {md}")
    ev = load_json(a.eval_json, "held-out eval result")
    for field in ("pass_rate", "heldout_passed", "refusal_no_regression"):
        if field not in ev:
            die(f"held-out eval result missing required field: {field}")
    bp = pathlib.Path(a.bom)
    if not bp.is_file():
        die(f"BOM not found: {bp}")
    bom_sha = sha256_file(bp)
    git_sha = a.git_sha.strip()
    if not (4 <= len(git_sha) <= 64 and all(c in "0123456789abcdef" for c in git_sha.lower())):
        die(f"--git-sha does not look like a hex sha: {git_sha!r}")

    manifest = {
        "schema": "szl.run-manifest/v1",
        "issued_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "subject": {
            "model_dir": str(md),
            "git_sha": git_sha,
            "workflow_run": a.workflow_run,
        },
        "eval": {
            "pass_rate": ev["pass_rate"],
            "heldout_passed": bool(ev["heldout_passed"]),
            "refusal_no_regression": bool(ev["refusal_no_regression"]),
        },
        "model_bom_sha256": bom_sha,
        "signatures": {"manifest": bool(a.signed_manifest)},
        "conformance": {"all_vectors_passed": bool(a.conformance_passed)},
        "release": {"kind": a.release_kind},
        "chain": {"prev_hash": a.prev_hash or "genesis"},
    }
    op = pathlib.Path(a.out)
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {op} (bom sha256 {bom_sha[:16]}..., kind={a.release_kind})")
    if not a.signed_manifest:
        print("::notice::signatures.manifest=false — sign job must re-emit with --signed-manifest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
