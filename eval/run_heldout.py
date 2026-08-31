#!/usr/bin/env python3
"""Run the held-out generation eval (Gate 2) and write release/heldout-eval.json.

FAIL-CLOSED by design:
  * exit 1 if the eval config (default eval/heldout_generate.yaml) is missing
    or malformed — no eval set, no publication;
  * exit 1 if prompts cannot be executed (no --results file AND no local
    transformers/model available) — an eval that cannot run is a failed gate.

Execution modes (CPU-safe):
  --results <json> : [{"id": ..., "output": ...}, ...] from an upstream run.
  otherwise        : try `transformers` on CPU against --model (a local dir or
                     HF id); falls through to FAIL if unavailable.

Output schema (consumed by the publish job):
  {"pass_rate": float, "n_passed": int, "n_total": int,
   "heldout_passed": bool, "refusal_no_regression": false,   # proven separately
   "model": str, "mode": "results-file"|"transformers-cpu", "results": [...]}

`heldout_passed` defaults to False and only becomes True when --min-pass-rate
is explicitly asserted here; the workflow re-checks the rate itself, and the
publish job requires heldout_passed === true in the run manifest.
"""
import argparse
import json
import os
import pathlib
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    print("::error::run_heldout: pyyaml is required (pip install pyyaml)", file=sys.stderr)
    raise SystemExit(1)


def die(msg: str) -> "SystemExit":
    print(f"::error::run_heldout: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load_config(path: str) -> dict:
    cp = pathlib.Path(path)
    if not cp.is_file():
        die(f"held-out eval set missing: {cp} (fail-closed)")
    try:
        cfg = yaml.safe_load(cp.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        die(f"eval config not valid YAML: {e}")
    if not isinstance(cfg, dict) or not isinstance(cfg.get("prompts"), list) or not cfg["prompts"]:
        die("eval config has no non-empty 'prompts' list")
    for p in cfg["prompts"]:
        if not (isinstance(p, dict) and p.get("id") and p.get("prompt") and p.get("expected")):
            die(f"malformed prompt entry (need id/prompt/expected): {p!r}")
    return cfg


def matches(output: str, prompt: dict) -> bool:
    mode = prompt.get("matching", "contains")
    out = output or ""
    for exp in prompt["expected"]:
        if mode == "exact" and out.strip() == str(exp).strip():
            return True
        if mode == "contains" and str(exp).lower() in out.lower():
            return True
    return False


def run_transformers_cpu(model_ref: str, prompts: list) -> list:
    """Generate outputs with a local/Hub model on CPU. Raises on any failure
    so the caller can fail closed."""
    import torch  # noqa: F401  (transformers needs it; import error -> fail closed)
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_ref)
    model = AutoModelForCausalLM.from_pretrained(model_ref)  # CPU by default
    outs = []
    for p in prompts:
        ids = tok(p["prompt"], return_tensors="pt")
        gen = model.generate(**ids, max_new_tokens=64, do_sample=False)
        outs.append(tok.decode(gen[0][ids["input_ids"].shape[1]:], skip_special_tokens=True))
    return outs


def emit(out_path: str, doc: dict) -> None:
    op = pathlib.Path(out_path)
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {op}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, help="Local model dir or HF id.")
    ap.add_argument("--config", default="eval/heldout_generate.yaml")
    ap.add_argument("--results", default=None, help="Optional pre-computed outputs JSON.")
    ap.add_argument("--out", default="release/heldout-eval.json")
    ap.add_argument("--assert-min-pass-rate", type=float, default=None,
                    help="If set, heldout_passed=pass_rate>=this; else heldout_passed stays false.")
    a = ap.parse_args()

    cfg = load_config(a.config)
    prompts = cfg["prompts"]

    outputs: dict[str, str] = {}
    mode = None
    if a.results:
        rp = pathlib.Path(a.results)
        if not rp.is_file():
            die(f"--results file not found: {rp}")
        data = json.loads(rp.read_text(encoding="utf-8"))
        rows = data.get("results", data) if isinstance(data, dict) else data
        if not isinstance(rows, list):
            die("--results must be a list of {id, output} or {'results': [...]}")
        outputs = {str(r["id"]): str(r.get("output", "")) for r in rows if isinstance(r, dict) and "id" in r}
        missing = [p["id"] for p in prompts if p["id"] not in outputs]
        if missing:
            die(f"results file missing outputs for prompt ids: {missing}")
        mode = "results-file"
    else:
        try:
            outs = run_transformers_cpu(a.model, prompts)
            outputs = {p["id"]: o for p, o in zip(prompts, outs)}
            mode = "transformers-cpu"
        except Exception as e:  # model dir absent, transformers absent, OOM...
            die(f"cannot execute held-out prompts (no --results; transformers run failed: {e}). "
                "Fail-closed: no eval, no publication.")

    results, n_passed = [], 0
    for p in prompts:
        ok = matches(outputs[p["id"]], p)
        n_passed += ok
        results.append({"id": p["id"], "passed": bool(ok),
                        "output_head": outputs[p["id"]][:160]})
    n_total = len(prompts)
    pass_rate = n_passed / n_total if n_total else 0.0
    heldout_passed = (a.assert_min_pass_rate is not None
                      and pass_rate >= a.assert_min_pass_rate)

    doc = {
        "model": a.model,
        "config": a.config,
        "mode": mode,
        "n_total": n_total,
        "n_passed": n_passed,
        "pass_rate": round(pass_rate, 6),
        "heldout_passed": bool(heldout_passed),
        "refusal_no_regression": False,  # set true only by eval/run_refusal.py evidence
        "results": results,
    }
    emit(a.out, doc)
    print(f"held-out pass rate: {pass_rate:.4f} ({n_passed}/{n_total}), mode={mode}")
    print(f"heldout_passed={heldout_passed} (asserted threshold: {a.assert_min_pass_rate})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
