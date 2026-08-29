---
license: apache-2.0
library_name: kernels
tags:
  - governed-ai
  - szl-holdings
  - doctrine-v11
  - kernel
  - kernel
---

# szl-receipt-attn

Softmax gated by λ. Tokens outside authority do not get weight. They get zero.

**Family.** kernel · **Evidence.** KERNEL · **Weights.** kernel

Hub: [SZLHOLDINGS/szl-receipt-attn](https://huggingface.co/SZLHOLDINGS/szl-receipt-attn)

## The cut

Guardrails after generation are late. Masking before softmax is the thing nobody ships because it hurts scores. We want the hurt.

A model that cannot attend to what it is not allowed to see.

### Silhouette → leave → SZL

| Leader | Take, then tweak |
|---|---|
| Anthropic | Constitution applied at the attention head. |
| NVIDIA | Fused kernel, NVIDIA-shaped, SZL-cut. |
| Unsloth | No. |

Nobody else ships this combination. That is the point of a one-of-one.

## Intended use

Fuse into governed decode.

## Limitations

- Kernel, not weights.

## Honesty

| Claim | Label |
|---|---|
| This card's numbers | KERNEL |
| Energy / joules | UNAVAILABLE unless a signed meter says MEASURED |
| Λ uniqueness | Conjecture 1 OPEN — not a theorem |
| GGUF as the signed object | FALSE |

Doctrine v11 LOCKED · 749 declarations · 14 axioms · 163 sorries · locked-proven 8.

Apache-2.0. Copyright 2026 SZL Holdings · Stephen P. Lutar Jr. · ORCID [0009-0001-0110-4173](https://orcid.org/0009-0001-0110-4173).
