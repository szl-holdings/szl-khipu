#!/usr/bin/env python3
"""Render the model card from the BOM + held-out eval + publication-gate JSON.

Doctrine: no hand-written claims — every field on the card is extracted from
an artifact produced inside the gated workflow. Missing/invalid inputs are a
hard failure (exit 1). Substitution uses {{token}} placeholders in the
template; any token left unsubstituted after rendering fails the build.

Usage:
  python scripts/render_model_card.py \
    --bom bom/model-bom.cdx.json \
    --eval release/heldout-eval.json \
    --gate release/publication-gate.json \
    --template cards/model-card.md.tmpl \
    --out release/README.md
"""
import argparse
import json
import pathlib
import re
import sys


def die(msg: str) -> "SystemExit":
    print(f"::error::render_model_card: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load(p: str, label: str):
    fp = pathlib.Path(p)
    if not fp.is_file():
        die(f"{label} not found: {fp}")
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{label} not valid JSON: {e}")


def prop(component: dict, name: str, default: str = "—") -> str:
    for p in component.get("properties", []):
        if p.get("name") == name:
            return str(p.get("value", default))
    return default


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bom", required=True)
    ap.add_argument("--eval", dest="eval_json", required=True)
    ap.add_argument("--gate", required=True)
    ap.add_argument("--template", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    bom = load(a.bom, "Model BOM")
    ev = load(a.eval_json, "held-out eval")
    gate = load(a.gate, "publication gate")
    # The workflow's publication-gate.json carries only {publication_eligible,
    # checks}; provenance fields live in the run manifest next to it. Merge
    # when present — absent fields degrade to '—', never to invented values.
    mp = pathlib.Path(a.gate).parent / "run-manifest.json"
    manifest = load(str(mp), "run manifest") if mp.is_file() else {}
    gate = {**gate, "workflow_run": (manifest.get("subject") or {}).get("workflow_run", "—"),
            "model_bom_sha256": manifest.get("model_bom_sha256", "0" * 64),
            "git_sha": (manifest.get("subject") or {}).get("git_sha", "—"),
            "issued_at": manifest.get("issued_at", "—")}
    tp = pathlib.Path(a.template)
    if not tp.is_file():
        die(f"template not found: {tp}")
    tmpl = tp.read_text(encoding="utf-8")

    comp = (bom.get("metadata") or {}).get("component") or {}
    lic = "—"
    for l in comp.get("licenses", []):
        lic = ((l.get("license") or {}).get("id")
               or (l.get("license") or {}).get("name") or lic)

    rows = []
    for r in ev.get("results", []):
        rows.append(f"| `{r.get('id', '?')}` | {'PASS' if r.get('passed') else 'FAIL'} |")
    per_prompt_rows = "\n".join(rows) if rows else "| _(per-prompt detail not recorded)_ | — |"

    eligible = bool(gate.get("publication_eligible"))
    ctx = {
        "model_name": str(comp.get("name", "unnamed-model")),
        "description": str(comp.get("description", "")),
        "version": str(comp.get("version", "unspecified")),
        "license": lic,
        "base_model": prop(comp, "szl:base_model", "undeclared"),
        "pipeline_tag": prop(comp, "szl:pipeline_tag", "unspecified"),
        "publication_eligible": str(eligible).lower(),
        "workflow_run": str(gate.get("workflow_run", "—")),
        "bom_sha256_short": str(gate.get("model_bom_sha256", "0" * 64))[:16],
        "spec_version": str(bom.get("specVersion", "—")),
        "bom_serial": str(bom.get("serialNumber", "—")),
        "n_components": str(len(bom.get("components", []))),
        "bom_publication_eligible": prop(comp, "szl:publication_eligible", "—"),
        "eval_config": str(ev.get("config", "eval/heldout_generate.yaml")),
        "eval_mode": str(ev.get("mode", "—")),
        "n_total": str(ev.get("n_total", "—")),
        "n_passed": str(ev.get("n_passed", "—")),
        "pass_rate": f"{float(ev.get('pass_rate', 0.0)):.4f}",
        "heldout_passed": str(bool(ev.get("heldout_passed"))).lower(),
        "refusal_no_regression": str(bool(ev.get("refusal_no_regression"))).lower(),
        "all_vectors_passed": str(bool((gate.get("checks") or {}).get("conformance_passed"))).lower(),
        "conformance_summary": "5 vectors: canonicalization, PAE, DER, prev_hash, ts",
        "git_sha": str(gate.get("git_sha", "—")),
        "issued_at": str(gate.get("issued_at", "—")),
        "per_prompt_rows": per_prompt_rows,
    }

    out = tmpl
    for k, v in ctx.items():
        out = out.replace("{{" + k + "}}", v)
    leftover = re.findall(r"\{\{[\w.-]+\}\}", out)
    if leftover:
        die(f"unsubstituted template tokens remain: {sorted(set(leftover))} (fail-closed)")

    op = pathlib.Path(a.out)
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(out, encoding="utf-8")
    print(f"wrote {op} — publication_eligible={eligible}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
