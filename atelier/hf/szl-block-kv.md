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

# szl-block-kv

KV cache that refuses to store keys it is not authorized to remember. arXiv:2309.06180 plus a gate.

**Family.** kernel · **Evidence.** KERNEL · **Weights.** kernel

Hub: [SZLHOLDINGS/szl-block-kv](https://huggingface.co/SZLHOLDINGS/szl-block-kv)

## The cut

Blocked KV was invented for speed. We use the blocking to forget on purpose. Memory is a privilege.

A cache that cannot be subpoenaed for what it was never allowed to hold.

### Silhouette → leave → SZL

| Leader | Take, then tweak |
|---|---|
| Anthropic | No persistent unauthorized memory. |
| NVIDIA | PagedAttention / blocked KV — then we spend it on governance. |
| Unsloth | No. |

Nobody else ships this combination. That is the point of a one-of-one.

## Intended use

Governed decode memory.

## Limitations

- Kernel. Not a drop-in vLLM replacement.

## Honesty

| Claim | Label |
|---|---|
| This card's numbers | KERNEL |
| Energy / joules | UNAVAILABLE unless a signed meter says MEASURED |
| Λ uniqueness | Conjecture 1 OPEN — not a theorem |
| GGUF as the signed object | FALSE |

Doctrine v11 LOCKED · 749 declarations · 14 axioms · 163 sorries · locked-proven 8.

Apache-2.0. Copyright 2026 SZL Holdings · Stephen P. Lutar Jr. · ORCID [0009-0001-0110-4173](https://orcid.org/0009-0001-0110-4173).
