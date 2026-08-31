#!/usr/bin/env python3
"""Generate a CycloneDX 1.5 Model BOM from a LOCAL model directory.

Adapted from the SZL estate audit tool (szl_audit/build_model_bom.py, which
built BOMs from enumerated Hub metadata) to run in CI against files on disk:
walks --model-dir, sha256-hashes every file, and reads optional model-card
YAML (HF-style frontmatter in <model-dir>/README.md or a standalone YAML via
--card) for base_model / license. Attaches the held-out eval result when
--eval is given.

Fail-closed: exits 1 if the model dir is missing/empty or the output cannot
be written. Stdlib only.

Usage:
  python scripts/build_model_bom.py \
    --model-dir artifacts/model \
    [--base-model SZLHOLDINGS/SZL-1-base] \
    [--dataset-manifest data/dataset-manifest.json] \
    [--eval release/heldout-eval.json] \
    [--materials git://<sha>]... \
    --out bom/model-bom.cdx.json
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import re
import sys
import uuid

SPEC_VERSION = "1.5"
TOOL = {"vendor": "SZL Holdings", "name": "build_model_bom", "version": "2.0.0"}

WEIGHT_EXTS = {"safetensors", "gguf", "bin"}


def die(msg: str, code: int = 1) -> "SystemExit":
    print(f"::error::build_model_bom: {msg}", file=sys.stderr)
    raise SystemExit(code)


def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_card_fields(model_dir: pathlib.Path, card_path: str | None) -> dict:
    """Best-effort read of HF-style YAML frontmatter for base_model/license.

    Uses a line parser (frontmatter only) so this stays stdlib-only; unknown
    fields degrade to 'undeclared' instead of failing the build.
    """
    src = None
    if card_path:
        src = pathlib.Path(card_path)
    else:
        cand = model_dir / "README.md"
        src = cand if cand.is_file() else None
    fields: dict[str, str] = {}
    if src is None:
        return fields
    text = src.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return fields
    for line in m.group(1).splitlines():
        kv = re.match(r"^([A-Za-z_][\w-]*):\s*(.+?)\s*$", line)
        if kv and kv.group(1) in ("base_model", "license", "version", "pipeline_tag", "model_name"):
            fields[kv.group(1)] = kv.group(2).strip("'\"")
    return fields


def role_for(ext: str) -> str:
    if ext in WEIGHT_EXTS:
        return "weights"
    if ext == "json":
        return "config"
    if ext == "md":
        return "documentation"
    return "support"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--base-model", default=None, help="Overrides card value; 'null'/'None' treated as unset.")
    ap.add_argument("--card", default=None, help="Optional YAML/MD file with model-card frontmatter.")
    ap.add_argument("--dataset-manifest", default=None)
    ap.add_argument("--eval", dest="eval_json", default=None, help="release/heldout-eval.json from gate 2.")
    ap.add_argument("--materials", action="append", default=[], help="e.g. git://<sha> (repeatable).")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    model_dir = pathlib.Path(a.model_dir)
    if not model_dir.is_dir():
        die(f"model dir not found: {model_dir}")
    files = sorted(p for p in model_dir.rglob("*") if p.is_file())
    if not files:
        die(f"model dir {model_dir} contains no files — refusing to emit an empty BOM")

    card = read_card_fields(model_dir, a.card)
    base = (a.base_model or "").strip()
    if base.lower() in ("", "null", "none", "undeclared"):
        base = card.get("base_model") or "undeclared"
    license_ = card.get("license", "other")
    name = card.get("model_name") or model_dir.resolve().name

    eval_prop = "MISSING — required before publication"
    eligible = "false"
    if a.eval_json:
        ep = pathlib.Path(a.eval_json)
        if ep.is_file():
            ev = json.loads(ep.read_text())
            eval_prop = f"pass_rate={ev.get('pass_rate')} heldout_passed={ev.get('heldout_passed')}"
            eligible = "true" if (ev.get("heldout_passed") and ev.get("refusal_no_regression")) else "false"
        else:
            print(f"::warning::eval file {ep} not found; szl:heldout_eval recorded as MISSING", file=sys.stderr)

    components, depends = [], []
    for p in files:
        rel = p.relative_to(model_dir).as_posix()
        ext = rel.rsplit(".", 1)[-1].lower() if "." in rel else ""
        components.append({
            "type": "file",
            "bom-ref": f"file:{rel}",
            "name": rel,
            "scope": "required",
            "hashes": [{"alg": "SHA-256", "content": sha256_file(p)}],
            "properties": [{"name": "szl:role", "value": role_for(ext)}],
        })
        depends.append(f"file:{rel}")

    for dm in ([a.dataset_manifest] if a.dataset_manifest else []):
        dp = pathlib.Path(dm)
        if dp.is_file():
            components.append({
                "type": "data",
                "bom-ref": f"data:{dp.name}",
                "name": dp.name,
                "scope": "required",
                "hashes": [{"alg": "SHA-256", "content": sha256_file(dp)}],
                "properties": [{"name": "szl:role", "value": "dataset-manifest"}],
            })
            depends.append(f"data:{dp.name}")
        else:
            print(f"::warning::dataset manifest {dp} not found; omitted from BOM", file=sys.stderr)

    declared_lic = ([{"license": {"id": license_}}] if license_ not in ("other", None)
                    else [{"license": {"name": str(license_)}}])
    serial_src = f"{model_dir.resolve()}@{next((m for m in a.materials if m.startswith('git://')), 'local')}"
    bom = {
        "bomFormat": "CycloneDX",
        "specVersion": SPEC_VERSION,
        "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, serial_src)}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "tools": [TOOL],
            "component": {
                "type": "machine-learning-model",
                "bom-ref": f"model:{name}",
                "name": name,
                "version": card.get("version", "unspecified"),
                "description": f"Local model dir {model_dir} — base model: {base}",
                "licenses": declared_lic,
                "properties": [
                    {"name": "szl:base_model", "value": str(base)},
                    {"name": "szl:pipeline_tag", "value": str(card.get("pipeline_tag", "unspecified"))},
                    {"name": "szl:heldout_eval", "value": str(eval_prop)},
                    {"name": "szl:publication_eligible", "value": eligible},
                ],
            },
        },
        "components": components,
        "dependencies": [{"ref": f"model:{name}", "dependsOn": depends}],
    }
    for m in a.materials:
        bom["metadata"].setdefault("externalReferences", []).append({"type": "build-meta", "url": m})

    out = pathlib.Path(a.out)
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(bom, indent=2) + "\n", encoding="utf-8")
    except OSError as e:
        die(f"cannot write {out}: {e}")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"OK {name}: {len(files)} model files hashed, BOM {out} sha256={digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
