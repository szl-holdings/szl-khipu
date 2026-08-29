---
license: apache-2.0
library_name: numpy
tags:
  - governed-ai
  - khipu
  - szl-holdings
  - embedding
  - silhouette
---

# MiniEmbed-Nano

Tiny hash+table embed: **V=64, d=12**, L2-normalized rows. **Not a foundation embed. Not neural. Not MiniEmbed 3290×128.**

Canonical source: [szl-holdings/szl-khipu](https://github.com/szl-holdings/szl-khipu)  
Sibling card: [SZLHOLDINGS/szl-khipu](https://huggingface.co/SZLHOLDINGS/szl-khipu)  
The larger statistical MiniEmbed (3290 × 128) lives on [SZLHOLDINGS/szl-kernels](https://huggingface.co/SZLHOLDINGS/szl-kernels) — a different artifact. Do not mix them.

```python
from szl_khipu.train import mini_embed

emb = mini_embed.build(seed=20260721)
vec = emb.embed("knot the run")
print(emb.V, emb.D, vec.shape)
# 64 12 (12,)
emb.save_npz("mini_embed.npz")
```

## What it does

- SHA-256 token id modulo 64. Mean-pool then L2. Deterministic given seed.
- Built here on CPU NumPy. Honesty **REPORTED**. Energy **UNAVAILABLE**.
- No analogy score. No retrieval score. No SVD variance claim (that belongs to the 3290×128 table).

## Bench (this tree)

`TRAINING_RECEIPT.json` seed `20260721` · honesty **REPORTED**

| Metric | Value |
|---|---|
| V×d | 64 × 12 |
| method | hash+table L2 |
| weights | `mini_embed.npz` sha256 `ae31a3a7214d1f142d8ea3f4f86c35bdedd7c108bc5d04ea00c87e7b674e6e3b` |

Infers on `POST /api/infer {"kind":"mini_embed","token":"F18"}`. **Not neural. Not 3290×128.**

## What it is NOT

- **Not** the [SZLHOLDINGS/szl-kernels](https://huggingface.co/SZLHOLDINGS/szl-kernels) MiniEmbed (3290 × 128, SVD var 0.3146).
- **Not neural. Not word2vec. Not a foundation embed.**
- **Not 1.5B. Not Qwen.**
- **Not proven trust.** Λ uniqueness remains Conjecture 1 OPEN.
- Energy **UNAVAILABLE**. CUDA **UNAVAILABLE**. Never a fabricated joule.

## Honesty

| Claim | Label | What-NOT |
|---|---|---|
| Table built in this package | REPORTED | V=64 d=12, not 3290×128 |
| Neural / trained embed | FALSE | hash+table, not SGD |
| Analogy / retrieval score | UNAVAILABLE | not measured |
| Energy | UNAVAILABLE | never a fabricated joule |
| CUDA | UNAVAILABLE | CPU numpy LIVE |

Doctrine v11 LOCKED · 749/14/163 · locked-proven 8. Apache-2.0. Copyright 2026 SZL Holdings · Stephen P. Lutar Jr. · ORCID [0009-0001-0110-4173](https://orcid.org/0009-0001-0110-4173).
