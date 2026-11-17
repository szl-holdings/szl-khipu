---
title: Khipu Proof Loom 3D
emoji: 🪢
colorFrom: blue
colorTo: yellow
sdk: gradio
sdk_version: 6.31.0
python_version: '3.11'
app_file: app.py
pinned: false
license: apache-2.0
short_description: Exact finite mathematics in Python 3D
---

# Khipu Proof Loom — research preview

Authoritative source: [szl-holdings/szl-khipu](https://github.com/szl-holdings/szl-khipu).
This space uses only Python application source. Gradio packages the browser-side WebGL renderer.
It shows **mathematical torus knots** and a separate **modern decimal cord sketch** as illustrations.
Neither is a reconstruction or decipherment of historical Andean khipu objects.

The exact finite Rogers–Ramanujan coefficients are computed by independent integer recurrences,
with source-bound integrity hashes and explicit negative-control tests. The **Sequence Scout**
section **optionally** fits a bounded CPU symbolic model across 1,573 hypothesis candidates
using modern synthetic coefficients 0–32, freezes the model, then compares independent
degrees 33–128. It is **OFF by default**: open the accordion, check the explicit
opt-in box and click Train. The published receipt and source bytes are SHA-256
checked at startup, without fitting any model. The complete experiment is
replayed only after opt-in. Unchecking clears displayed results; direct API
requests without opt-in return DISABLED without training. Opting out
cancels queued training events; an already-running synchronous callback may
complete (it cannot be forcibly interrupted). A negative-control option
deliberately corrupts a count and must return HOLD.

## Resource and admission envelope

- The public Gradio queue admits at most 32 pending items. Mathematics and
  3D generation share one CPU execution lane (`concurrency_limit=1`). The
  user-facing Train button is disabled until explicitly opted in.
- Gradio-generated request-cache objects older than two hours are cleaned
  hourly using the supported `delete_cache=(3600,7200)` setting. Source GLB
  files are in a Python `TemporaryDirectory` owned for the application
  lifetime and removed at normal interpreter shutdown. Crash-killed processes
  or provider-level filesystems may require external cleanup; this is not a
  storage quota guarantee.
- The owner publisher checks RUNNING, source SHA, manifest SHA, `model3d`,
  default-OFF checkbox and whether both public callbacks are queued. Gradio's
  public config does not reveal actual callback concurrency settings, so
  real-SDK CI checks the backend event objects, the 32-item queue, and the
  opt-in button's disabled state; exact source bytes are then pinned to the
  deployed immutable Hub revision. Healthy source checks do not constitute
  independent archaeology or model quality.
- **Remaining infrastructure risk:** the public API is intentionally
  callable without login. Queue bounds are not identity-aware rate limiting.
  Any future high-traffic/paid/enterprise tier must add independently governed
  ingress quotas, budgets and load tests before claiming capacity readiness.

This app does **not** train neural/LLM weights, prove infinite identities, replay the
external Lean formalization, use actual archaeological measurements, or claim
ancient Inka mathematical decipherment or broader production/scientific qualification.

Research sources: [Axiom Math HJO](https://github.com/AxiomMath/HJO) and
[Open Khipu Repository](https://github.com/khipulab/open-khipu-repository).
