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
requests without opt-in return DISABLED without training. A negative-control
option deliberately corrupts a count and must return HOLD.

This app does **not** train neural/LLM weights, prove infinite identities, replay the
external Lean formalization, use actual archaeological measurements, or claim
ancient Inka mathematical decipherment or broader production/scientific qualification.

Research sources: [Axiom Math HJO](https://github.com/AxiomMath/HJO) and
[Open Khipu Repository](https://github.com/khipulab/open-khipu-repository).
