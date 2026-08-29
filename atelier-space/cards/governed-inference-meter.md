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

# governed-inference-meter

NVML energy as a receipt, not a dashboard widget. Tokens per joule is an eval axis.

**Family.** kernel · **Evidence.** KERNEL · **Weights.** kernel

Hub: [SZLHOLDINGS/governed-inference-meter](https://huggingface.co/SZLHOLDINGS/governed-inference-meter)

## The cut

NVIDIA built NVML. We bound it. A run without joules is an incomplete receipt. Leaders brag FLOPs. We ask what it cost the wall.

Energy-attested inference as the default, including the honest case where energy is unavailable.

### Silhouette → leave → SZL

| Leader | Take, then tweak |
|---|---|
| Anthropic | Honesty about cost. |
| NVIDIA | Direct take: NVML. Cut: signed tokens-per-joule. |
| Unsloth | Train cheap, then measure the decode. |

Nobody else ships this combination. That is the point of a one-of-one.

## Intended use

Wrap decode. Write joules into the receipt or write UNAVAILABLE.

## Limitations

- Energy may be unavailable. The card must say so — see energy-attested-runs.

## Honesty

| Claim | Label |
|---|---|
| This card's numbers | KERNEL |
| Energy / joules | UNAVAILABLE unless a signed meter says MEASURED |
| Λ uniqueness | Conjecture 1 OPEN — not a theorem |
| GGUF as the signed object | FALSE |

Doctrine v11 LOCKED · 749 declarations · 14 axioms · 163 sorries · locked-proven 8.

Apache-2.0. Copyright 2026 SZL Holdings · Stephen P. Lutar Jr. · ORCID [0009-0001-0110-4173](https://orcid.org/0009-0001-0110-4173).
