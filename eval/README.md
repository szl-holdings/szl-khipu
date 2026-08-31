# eval/ — held-out generation + refusal probes (model-publish-gate, Gate 2)

- `heldout_generate.yaml` — the held-out generation eval set. These prompts
  must be withheld from every training split. `eval/run_heldout.py` fails
  closed (exit 1) if this file is missing.
- `run_heldout.py` --config <yaml> --model <dir> [--results <json>] \
    [--assert-min-pass-rate 0.80] --out release/heldout-eval.json
  Modes: score a pre-computed results file, or run a local transformers model
  CPU-only. If neither is possible the gate fails closed.
- `run_refusal.py` --model <dir> --assert-no-regression — compares against
  `baselines/refusal.json` (written on first run; commit it).
- `baselines/` — committed refusal baselines.
