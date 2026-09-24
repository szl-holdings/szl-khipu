---
license: apache-2.0
library_name: numpy
tags:
  - governed-ai
  - szl-holdings
  - doctrine-v11
  - nano
  - synthetic
  - software
  - reference
  - test-fixture
---

> **Status: SOFTWARE / REFERENCE / TEST FIXTURE.** Not a production model.

This Hub repository contains a bare NumPy archive. The loading and forward-pass
implementation lives in the canonical `szl_khipu` package; no packaged Hub
loader or `config.json` is shipped alongside these weights. Treat this as a
software fixture until its complete inference contract is independently verified.

# TinyKhipu-Nano

Token embeddings and handles in. NAVIGATE or ABSTAIN out. Abstain is the default class, not a post-hoc filter.

**Family.** nano · **Evidence.** SYNTHETIC · **Weights.** numpy · **Architecture.** 24-token, 12-dimensional embedding with two-class and handle-scoring heads · **Not 1.5B.**

Hub: [SZLHOLDINGS/TinyKhipu-Nano](https://huggingface.co/SZLHOLDINGS/TinyKhipu-Nano)

## The cut

Leaders train models to answer. We train a silhouette to shut up when overlap is thin or the lure is adversarial. This nano is the token-and-handle reference model of that cut. Not 1.5B.

A synthetic navigator that mean-pools token embeddings, scores handle notes, and returns NAVIGATE or ABSTAIN.

### Silhouette → leave → SZL

| Leader | Take, then tweak |
|---|---|
| Anthropic | Refusal as a typed output, not a polite paragraph. |
| NVIDIA | Guardrail inside the head, not a sidecar. |
| Unsloth | The 1.5B QLoRA is the grown form of this MLP. |

Nobody else ships this combination. That is the point of a one-of-one.

## Intended use

Unit-test the NAVIGATE|ABSTAIN schema before GPU spend.

## Bench (this tree)

`TRAINING_RECEIPT.json` seed `20260721` · steps 280 · honesty **REPORTED**

| Metric | Value |
|---|---|
| plan_valid | 1.00 |
| abstain | 1.00 |
| hallucinated | 0 |
| weights | `tiny_khipu.npz` sha256 `cc8d0385b2c75079669df809d7e4823f1ad8d9d535aec511446347490b11dff9` |

Infers on `POST /api/infer {"kind":"tiny_khipu"}`. Hard ID filter. **Not Qwen. Not 1.5B.**

## Limitations

- Synthetic features. Perfect holdout is a design fact, not a field claim.
- The 1.5B abstain rate is 2/6 — this nano does not wash that.

## Honesty

| Claim | Label |
|---|---|
| This card's numbers | SYNTHETIC |
| Energy / joules | UNAVAILABLE unless a signed meter says MEASURED |
| Λ uniqueness | Conjecture 1 OPEN — not a theorem |
| GGUF as the signed object | FALSE |

Doctrine v11 LOCKED · 749 declarations · 14 axioms · 163 sorries · locked-proven 8.

Apache-2.0. Copyright 2026 SZL Holdings · Stephen P. Lutar Jr. · ORCID [0009-0001-0110-4173](https://orcid.org/0009-0001-0110-4173).

## Artifact evidence

`tiny_khipu.npz` is present (3,568 bytes). SHA-256:

`cc8d0385b2c75079669df809d7e4823f1ad8d9d535aec511446347490b11dff9`

The archive hash matches `TRAINING_RECEIPT.json`. Its arrays were inspected
with `numpy.load(..., allow_pickle=False)`; numeric values were finite.

| Array | Shape | Data type |
| --- | --- | --- |
| `E` | `[24, 12]` | `float64` |
| `W` | `[2, 12]` | `float64` |
| `b` | `[2]` | `float64` |
| `Wc` | `[12]` | `float64` |

A matching unsigned receipt establishes local artifact consistency. Training
metrics remain reported synthetic results; this check does not independently
reproduce training or establish deployment, general intelligence, or production readiness.
