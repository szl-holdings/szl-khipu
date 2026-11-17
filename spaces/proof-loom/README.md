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

## Conjecture Crucible — finite mathematical counterexamples

The second optional research tool tests user-proposed Rogers–Ramanujan *partition-product* identities. Enter a modulus (2–12), sorted nonzero residues (1–4 classes) and a finite limit (1–256), then explicitly click the checker. It compares two independent exact reference methods (classical q-series and gap partitions) with the proposed product. There is no automatic evaluation at page load or GPU use.

The live `/falsify` API returns a human-readable result and an unsigned, domain-separated SHA-256 JSON receipt. An incorrect hypothesis yields the first finite counterexample with actual and proposed integer counts; where small enough, exact partition examples are included. **A hypothesis matching all 257 coefficients through n=256 is not proved for all n.** This interface does not test the HJO general torus-knot identities, Lean proof replay, or historical Inca khipus.

The publisher verifies the seven-file exact SOURCE.json and the presence of queued `/falsify` and `/hjo_profile` endpoints on the RUNNING Space. The finite checker shares the same `concurrency_limit=1`, `concurrency_id=proof-loom-cpu` CPU lane as the existing 3D and training controls.

## HJO Cylindric Lab — bounded finite definition study

The third optional research instrument uses **exact definitions** from Axiom Math's HJO Lean challenge at commit `6a58dfa6ab98bd35d841cb2cf8fd9081f62fad03`, with byte-verified `Challenge/Basic.lean` (SHA-256 `dc96a4b2f1bdeda0027968924ba480f8fc0e29e34eb56fb6cfbdbce2e235b48e`). The challenge contains five intentional `sorry` placeholders in theorem statements. They are not proofs, and this Space does not execute Lean.

After a researcher clicks `Run exact finite cylindric enumeration`, pure Python calculates the balanced outgoing profile and coefficients of the *bounded cylindric partition generating-function definition only*. Two independent enumerators must agree or the action reports HOLD. The implemented checks require `2<=a<=4`, `a<b<=9`, and `gcd(a,b)=1`, with entry cap `N=0..3` and volume degree `D=0..8`. Incompatible parameters HOLD without evaluation.

The exact HJO rank-N polynomial is NOT computed, the corresponding HJO finite identity has NOT been checked, and no new infinite theorem is proved. This UI does not interpret actual Andean khipus. Source details, checks, examples and limits: [research/hjo_profile](https://github.com/szl-holdings/szl-khipu/tree/main/research/hjo_profile).
