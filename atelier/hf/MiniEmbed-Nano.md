---
license: apache-2.0
library_name: numpy
tags:
  - governed-ai
  - szl-holdings
  - doctrine-v11
  - nano
  - measured
---

# MiniEmbed-Nano

A 64×12 embedding whose rows are a function of SHA-256. The vector is the receipt of the token.

**Family.** nano · **Evidence.** MEASURED · **Weights.** numpy · **Params.** 64 × 12

Hub: [SZLHOLDINGS/MiniEmbed-Nano](https://huggingface.co/SZLHOLDINGS/MiniEmbed-Nano)

## The cut

Nobody ships an embedding where retrieval is provenance. MiniEmbed is not BGE, not NV-Embed. Mean-pool of L2 rows, seed 20260721, CPU NumPy.

An embedding you can re-derive bit-exact from the seed. No SGD theater. Cosine is a claim about the table, not a vibe.

### Silhouette → leave → SZL

| Leader | Take, then tweak |
|---|---|
| Anthropic | Honest about what it is not — not a foundation embed. |
| NVIDIA | Tiny table instead of NV-Embed / NeMo retrieval stacks. |
| Unsloth | No LoRA. Construction is `build(seed)` — Unsloth is the wrong tool and we say so. |

Nobody else ships this combination. That is the point of a one-of-one.

## Intended use

Silhouette of receipted retrieval. Teaching and tests.

## Limitations

- Not a neural embed.
- Not comparable to BGE-base 768-d.
- Hit@2 is on five doctrine pairs — SAMPLE.

## Honesty

| Claim | Label |
|---|---|
| This card's numbers | MEASURED |
| Energy / joules | UNAVAILABLE unless a signed meter says MEASURED |
| Λ uniqueness | Conjecture 1 OPEN — not a theorem |
| GGUF as the signed object | FALSE |

Doctrine v11 LOCKED · 749 declarations · 14 axioms · 163 sorries · locked-proven 8.

Apache-2.0. Copyright 2026 SZL Holdings · Stephen P. Lutar Jr. · ORCID [0009-0001-0110-4173](https://orcid.org/0009-0001-0110-4173).
