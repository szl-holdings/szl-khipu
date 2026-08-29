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

# szl-maskmod

Authority as a mask. Out-of-scope tokens are zeroed, not down-weighted. Soft permission is a leak.

**Family.** kernel · **Evidence.** KERNEL · **Weights.** kernel

Hub: [SZLHOLDINGS/szl-maskmod](https://huggingface.co/SZLHOLDINGS/szl-maskmod)

## The cut

Every safety paper multiplies by 0.1. We multiply by 0. There is no 'a little bit unauthorized'.

Hard masks as the default, not an ablation.

### Silhouette → leave → SZL

| Leader | Take, then tweak |
|---|---|
| Anthropic | Hard refuse, compiled. |
| NVIDIA | Fused mask kernel. |
| Unsloth | No. |

Nobody else ships this combination. That is the point of a one-of-one.

## Intended use

Compose with receipt-attn.

## Limitations

- Kernel.

## Honesty

| Claim | Label |
|---|---|
| This card's numbers | KERNEL |
| Energy / joules | UNAVAILABLE unless a signed meter says MEASURED |
| Λ uniqueness | Conjecture 1 OPEN — not a theorem |
| GGUF as the signed object | FALSE |

Doctrine v11 LOCKED · 749 declarations · 14 axioms · 163 sorries · locked-proven 8.

Apache-2.0. Copyright 2026 SZL Holdings · Stephen P. Lutar Jr. · ORCID [0009-0001-0110-4173](https://orcid.org/0009-0001-0110-4173).
