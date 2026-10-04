---
license: apache-2.0
library_name: numpy
tags:
  - governed-ai
  - khipu
  - szl-holdings
  - embedding
  - silhouette
  - software
  - reference
  - test-fixture
---

<!-- SZL-CARD-PRESENTATION:v1 -->
<p><a href="https://huggingface.co/spaces/SZLHOLDINGS/szl-command-lab"><img src="https://raw.githubusercontent.com/szl-holdings/.github/main/profile/assets/szl/logos/szl_mark_holographic.svg" alt="SZL Holdings" width="112" /></a></p>

# MiniEmbed-Nano

A deterministic 64 × 12 NumPy table for inspecting hash-based token vectors and simple pooling.

**Artifact:** NumPy embedding table · **Stage:** Software / reference / test fixture

[Explore in Command Lab](https://huggingface.co/spaces/SZLHOLDINGS/szl-command-lab) · [Build](https://github.com/szl-holdings/szl-khipu) · [Evidence](https://github.com/szl-holdings/szl-khipu/blob/8d06c9333b636a86a27d88feb49097906833af30/hf/MiniEmbed-Nano/README.md)

## Before you use it

- This is a small reference table, not a trained neural embedding model or the separate 3290 × 128 SVD MiniEmbed artifact.
- The example constructs a new table; it does not verify loading or reproducing the published archive.
- No retrieval or analogy score is established for this artifact. Bind its exact revision, array schema, and loader before comparison.

<details>
<summary>Technical details and evidence</summary>

<!-- SZL-CARD-TECHNICAL:v1:START -->

> **Status: SOFTWARE / REFERENCE / TEST FIXTURE.** Not a production model.

This Hub repository contains a bare NumPy archive. The loading and forward-pass
implementation lives in the canonical `szl_khipu` package; no packaged Hub
loader or `config.json` is shipped alongside these weights. Treat this as a
software fixture until its complete inference contract is independently verified.

# MiniEmbed-Nano

Tiny hash+table embed: **V=64, d=12**, L2-normalized rows. **Not a foundation embed. Not neural. Not MiniEmbed 3290×128.**

Canonical source: [szl-holdings/szl-khipu](https://github.com/szl-holdings/szl-khipu)  
Sibling card: [SZLHOLDINGS/szl-khipu](https://huggingface.co/SZLHOLDINGS/szl-khipu)  
The larger statistical MiniEmbed (3290 × 128) lives on [SZLHOLDINGS/szl-kernels](https://huggingface.co/SZLHOLDINGS/szl-kernels) — a different artifact. Do not mix them.

Construction example for the canonical package: this builds and saves a
new deterministic 64 × 12 table. It does not load or independently verify the
published `mini_embed.npz`.

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

## Reported synthetic fixture evidence

`TRAINING_RECEIPT.json` seed `20260721` · honesty **REPORTED**

| Metric | Value |
|---|---|
| V×d | 64 × 12 |
| method | hash+table L2 |
| weights | `mini_embed.npz` receipt-reported sha256 `ae31a3a7214d1f142d8ea3f4f86c35bdedd7c108bc5d04ea00c87e7b674e6e3b` |

The related demo documents an application-specific `POST /api/infer` route.
This archive repository establishes no hosted endpoint, served revision, or
deployment guarantee. The route is illustrative application context.

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

## Artifact evidence

The previous card reports `mini_embed.npz` (6,892 bytes). Receipt-reported SHA-256 (not rehashed in this review):

`ae31a3a7214d1f142d8ea3f4f86c35bdedd7c108bc5d04ea00c87e7b674e6e3b`

The previous card reported that the archive matched the unsigned training
receipt and that `numpy.load(..., allow_pickle=False)` found finite numeric
arrays. The table below preserves that historical report. The September 30,
2026 card review read pinned text and the receipt; it did not download, rehash,
or inspect the archive, and did not replay training.

| Array | Shape | Data type |
| --- | --- | --- |
| `table` | `[64, 12]` | `float64` |
| `V` | `[]` | `int64` |
| `D` | `[]` | `int64` |

The retained receipt labels these reported synthetic fixture results **REPORTED**.

An independently checked archive/receipt match could establish local artifact
consistency; an unsigned digest would still not authenticate authorship or
measurement. These preserved receipt and array reports establish no new
training replay, independent evaluation, deployment, or production readiness.

Reviewed Hub text: [immutable snapshot `01e82f36ff722528233f76daf899c18f8cb5aaa2`](https://huggingface.co/SZLHOLDINGS/MiniEmbed-Nano/blob/01e82f36ff722528233f76daf899c18f8cb5aaa2/README.md).
Reviewed publisher source: [`hf/MiniEmbed-Nano/README.md` at `e53e3d24b22e356eb986c373aee27b3b3e7947ec`](https://github.com/szl-holdings/szl-khipu/blob/e53e3d24b22e356eb986c373aee27b3b3e7947ec/hf/MiniEmbed-Nano/README.md).
The shared unsigned [`TRAINING_RECEIPT.json`](https://huggingface.co/SZLHOLDINGS/MiniEmbed-Nano/blob/01e82f36ff722528233f76daf899c18f8cb5aaa2/TRAINING_RECEIPT.json), timestamped
`2026-08-29T17:11:32.518042+00:00`, enumerates four artifacts. Only its
`artifacts["mini_embed.npz"]` entry describes this archive; the other
entries do not establish that sibling artifacts are present in this repository.
The receipt does not bind its training run to the reviewed source commit.

<!-- SZL-CARD-TECHNICAL:v1:END -->

</details>
