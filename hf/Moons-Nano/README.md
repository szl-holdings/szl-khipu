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
---

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
