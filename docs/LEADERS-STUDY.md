# Domain Leader Study — szl-khipu (live Python kernels, knotted proof)

OUROBOROS phase-3, cohort-02 tranche-1, Kimi ruling W26-C2T1-KIMI-20261123-ASK (GO). PROPOSE-ONLY study card: documentation only, no implementation in this PR.

## Current state (repo inspection 2026-11-23)
Python repo; description: live Python kernels and tiny trained silhouettes; knot the run, hash the proof, fail closed. Topics: attention, doctrine-v11, governed-ai, khipu, lambda-gate. Companion HF space observed in estate census.

## Domain leaders studied
| Leader | What they have | Key sources |
| --- | --- | --- |
| Jupyter kernel protocol (jupyter_client messaging spec) | The canonical execution-request/reply lifecycle over zmq shell/iopub/stdin channels with parent_header msg_id binding, status messages busy/idle, and error semantics — the industry standard for governing live kernel execution | jupyter-client.readthedocs.io/en/latest/messaging.html (accessed 2026-11-23) |
| nbclient (Project Jupyter) | Headless, deterministic notebook execution engine behind papermill: execution-count discipline, cell timeout policy, per-cell error capture — receipts-grade run harness for kernels | github.com/jupyter/nbclient (accessed 2026-11-23) |

## What the leaders do better
- Every execution is bound to its request by msg_id in parent_header — any downstream artifact is attributable to exactly one request. That is the leader version of our knot-the-run.
- Busy/idle status messages make kernel state transition explicit and observable, so fail-closed has something real to close on rather than silence.
- nbclient proves deterministic headless execution with per-cell timeouts and error capture: runs are replayable, not vibes.

## Gaps
- Khipu knots bind the run's hash but the card found no documented binding to a kernel-protocol-standard execution identifier (msg_id/parent_header class).
- No documented busy/idle-style state-transition disclosure per execution on the knot surface.

## Ranked #1 absorb proposal (NOT implemented in this PR)
Adopt Jupyter parent_header msg_id as the execution identifier inside khipu knot records: each knot cites the kernel msg_id it seals, plus busy/idle transition timestamps. Expected benefit: knot provenance becomes verifiable by any Jupyter-standard tool, not only estate code. Cost/risk: low; schema addition to knot records, additive and backward-compatible. Validation: one kernel session producing knots whose msg_ids replay against jupyter_client's model. Rollback: identifier field is optional; emitting it can stop without invalidating old knots.

## Sources
- Jupyter messaging spec: https://jupyter-client.readthedocs.io/en/latest/messaging.html (accessed 2026-11-23)
- nbclient: https://github.com/jupyter/nbclient (accessed 2026-11-23)
