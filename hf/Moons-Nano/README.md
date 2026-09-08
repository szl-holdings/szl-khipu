---
license: apache-2.0
library_name: numpy
tags:
  - governed-ai
  - khipu
  - szl-holdings
  - moons
  - mlp
  - silhouette
  - software
  - reference
  - test-fixture
---

> **Status: SOFTWARE / REFERENCE / TEST FIXTURE.** Not a production model.

This Hub repository contains a bare NumPy archive. The loading and forward-pass
implementation lives in the canonical `szl_khipu` package; no packaged Hub
loader or `config.json` is shipped alongside these weights. Treat this as a
software fixture until its complete inference contract is independently verified.

# Moons-Nano

Two-moons **2→8→2** tanh-softmax SGD. A few hundred floats. **Not 1.5B. Not Qwen. Not a foundation model.**

Canonical source: [szl-holdings/szl-khipu](https://github.com/szl-holdings/szl-khipu)  
Sibling card: [SZLHOLDINGS/szl-khipu](https://huggingface.co/SZLHOLDINGS/szl-khipu)

```python
from szl_khipu.train import moons

weights, ev = moons.train(seed=20260721, steps=400)
print(ev["acc"], ev["loss"])
# REPORTED: acc 0.93 · loss ~0.13 on the training moons
moons.save_npz("moons.npz", weights)
```

## What it does

- Classic two-moons toy classification. Hidden width 8. Softmax over 2.
- Trained here on CPU NumPy. Honesty **REPORTED**. Energy **UNAVAILABLE**.

## Bench (this tree)

`TRAINING_RECEIPT.json` seed `20260721` · steps 400 · honesty **REPORTED**

| Metric | Value |
|---|---|
| acc | 0.93 |
| loss | ~0.13 |
| weights | `moons.npz` sha256 `dda50e3b293534de3f5aec01ebf9f8d6688e06069931618dfd35f01369904104` |

Infers on `POST /api/infer {"kind":"moons","x":0.2,"y":0.3}`. **Not 1.5B. Not a published benchmark.**

## What it is NOT

- **Not SZL-Khipu-1.5B.** Not QLoRA. Not a chat model.
- **Not sklearn moons as a product claim.** A live silhouette so the estate has a TRAINED tiny MLP that actually ran.
- **Not proven trust.** Λ uniqueness remains Conjecture 1 OPEN.
- Energy **UNAVAILABLE**. CUDA **UNAVAILABLE**. Never a fabricated joule.

## Honesty

| Claim | Label | What-NOT |
|---|---|---|
| Weights trained in this package | REPORTED | silhouette, Not 1.5B |
| acc 0.93 on the training moons | REPORTED | not a published benchmark |
| Λ | ADVISORY · Conjecture 1 OPEN | never a theorem |
| Energy | UNAVAILABLE | never a fabricated joule |
| CUDA | UNAVAILABLE | CPU numpy LIVE |

Doctrine v11 LOCKED · 749/14/163 · locked-proven 8. Apache-2.0. Copyright 2026 SZL Holdings · Stephen P. Lutar Jr. · ORCID [0009-0001-0110-4173](https://orcid.org/0009-0001-0110-4173).

## Artifact evidence

`moons.npz` is present (1,302 bytes). SHA-256:

`dda50e3b293534de3f5aec01ebf9f8d6688e06069931618dfd35f01369904104`

The archive hash matches `TRAINING_RECEIPT.json`. Its arrays were inspected
with `numpy.load(..., allow_pickle=False)`; numeric values were finite.

| Array | Shape | Data type |
| --- | --- | --- |
| `W1` | `[8, 2]` | `float64` |
| `b1` | `[8]` | `float64` |
| `W2` | `[2, 8]` | `float64` |
| `b2` | `[2]` | `float64` |

A matching unsigned receipt establishes local artifact consistency. Training
metrics remain reported synthetic results; this check does not independently
reproduce training or establish deployment, general intelligence, or production readiness.
