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

<!-- SZL-CARD-PRESENTATION:v1 -->
<p><a href="https://huggingface.co/spaces/SZLHOLDINGS/szl-command-lab"><img src="https://raw.githubusercontent.com/szl-holdings/.github/main/profile/assets/szl/logos/szl_mark_holographic.svg" alt="SZL Holdings" width="112" /></a></p>

# Moons-Nano

A 2→8→2 NumPy classifier for studying a small synthetic two-moons decision boundary.

**Artifact:** Bare NumPy weight archive · **Stage:** Software / reference / test fixture

[Explore in Command Lab](https://huggingface.co/spaces/SZLHOLDINGS/szl-command-lab) · [Build](https://github.com/szl-holdings/szl-khipu) · [Evidence](https://github.com/szl-holdings/szl-khipu/blob/8d06c9333b636a86a27d88feb49097906833af30/hf/Moons-Nano/README.md)

## Before you use it

- Training accuracy and loss are historical reported fixture results; they do not establish held-out performance or generalization.
- The example constructs a new fixture rather than loading the published archive. Match its array schema and loader before use.
- This toy fixture does not qualify a larger model. CUDA and energy measurement are UNAVAILABLE.

<details>
<summary>Technical details and evidence</summary>

<!-- SZL-CARD-TECHNICAL:v1:START -->

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

## Reported synthetic fixture evidence

`TRAINING_RECEIPT.json` seed `20260721` · steps 400 · honesty **REPORTED**

Accuracy `0.93` and loss `0.12973121797997034` are reported on the training
moons. They are not held-out generalization or a published benchmark. The
construction example above trains a new fixture; it does not load this archive.

| Metric | Value |
|---|---|
| training accuracy | 0.93 |
| training loss | 0.12973121797997034 |
| weights | `moons.npz` receipt-reported sha256 `dda50e3b293534de3f5aec01ebf9f8d6688e06069931618dfd35f01369904104` |

The related demo documents an application-specific `POST /api/infer` route.
This archive repository establishes no hosted endpoint, served revision, or
deployment guarantee. The route is illustrative application context.

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

The previous card reports `moons.npz` (1,302 bytes). Receipt-reported SHA-256 (not rehashed in this review):

`dda50e3b293534de3f5aec01ebf9f8d6688e06069931618dfd35f01369904104`

The previous card reported that the archive matched the unsigned training
receipt and that `numpy.load(..., allow_pickle=False)` found finite numeric
arrays. The table below preserves that historical report. The September 30,
2026 card review read pinned text and the receipt; it did not download, rehash,
or inspect the archive, and did not replay training.

| Array | Shape | Data type |
| --- | --- | --- |
| `W1` | `[8, 2]` | `float64` |
| `b1` | `[8]` | `float64` |
| `W2` | `[2, 8]` | `float64` |
| `b2` | `[2]` | `float64` |

The retained receipt labels these reported synthetic fixture results **REPORTED**.

An independently checked archive/receipt match could establish local artifact
consistency; an unsigned digest would still not authenticate authorship or
measurement. These preserved receipt and array reports establish no new
training replay, independent evaluation, deployment, or production readiness.

Reviewed Hub text: [immutable snapshot `77d002f9314dc0c86cd0f14e63fff60364929652`](https://huggingface.co/SZLHOLDINGS/Moons-Nano/blob/77d002f9314dc0c86cd0f14e63fff60364929652/README.md).
Reviewed publisher source: [`hf/Moons-Nano/README.md` at `e53e3d24b22e356eb986c373aee27b3b3e7947ec`](https://github.com/szl-holdings/szl-khipu/blob/e53e3d24b22e356eb986c373aee27b3b3e7947ec/hf/Moons-Nano/README.md).
The shared unsigned [`TRAINING_RECEIPT.json`](https://huggingface.co/SZLHOLDINGS/Moons-Nano/blob/77d002f9314dc0c86cd0f14e63fff60364929652/TRAINING_RECEIPT.json), timestamped
`2026-08-29T17:11:32.518042+00:00`, enumerates four artifacts. Only its
`artifacts["moons.npz"]` entry describes this archive; the other
entries do not establish that sibling artifacts are present in this repository.
The receipt does not bind its training run to the reviewed source commit.

<!-- SZL-CARD-TECHNICAL:v1:END -->

</details>
