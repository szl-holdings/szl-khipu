---
license: apache-2.0
library_name: kernels
tags:
  - governed-ai
  - szl-holdings
  - doctrine-v11
  - governance
  - kernel
---

# szl-provctl

Supply-chain controller. SLSA + in-toto. Who built it, from what, on which runner.

**Family.** governance · **Evidence.** KERNEL · **Weights.** kernel

Hub: [SZLHOLDINGS/szl-provctl](https://huggingface.co/SZLHOLDINGS/szl-provctl)

## The cut

Model cards skip the builder. We treat the builder as part of the model.

A weight that is invalid without its provenance predicate.

### Silhouette → leave → SZL

| Leader | Take, then tweak |
|---|---|
| Anthropic | No public SLSA for Claude weights. |
| NVIDIA | NGC signed images — take, then apply to LoRAs. |
| Unsloth | After the job, attach SLSA. Unsloth does not. |

Nobody else ships this combination. That is the point of a one-of-one.

## Intended use

CI predicate for every publish.

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
