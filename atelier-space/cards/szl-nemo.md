---
license: apache-2.0
library_name: other
tags:
  - governed-ai
  - szl-holdings
  - doctrine-v11
  - governance
  - hub
---

# szl-nemo

Tfidf → LogisticRegression over doctrine rules R1–R5. Not NVIDIA NeMo. Not Nemotron. Name collision, card-corrected.

**Family.** governance · **Evidence.** HUB · **Weights.** none · **Params.** Tfidf+LR

Hub: [SZLHOLDINGS/szl-nemo](https://huggingface.co/SZLHOLDINGS/szl-nemo)

## The cut

We took the idea of recipe-conformance from NVIDIA NeMo and built a tiny sklearn surrogate that triages answers against five doctrine rules. Then we stripped the misleading nemotron tags. Honesty over SEO.

A 10-millisecond 'does this answer violate doctrine?' that CI can run on every card.

### Silhouette → leave → SZL

| Leader | Take, then tweak |
|---|---|
| Anthropic | Constitutional classifier, tiny. |
| NVIDIA | Silhouette of NeMo recipe-conformance. Cut: sklearn, disclosed, not a Nemotron. |
| Unsloth | No. |

Nobody else ships this combination. That is the point of a one-of-one.

## Intended use

CI doctrine triage. Retrain from forge.py.

## Limitations

- model.joblib not on Hub at snapshot.
- Not Nemotron. Not generative.

## Honesty

| Claim | Label |
|---|---|
| This card's numbers | HUB |
| Energy / joules | UNAVAILABLE unless a signed meter says MEASURED |
| Λ uniqueness | Conjecture 1 OPEN — not a theorem |
| GGUF as the signed object | FALSE |

Doctrine v11 LOCKED · 749 declarations · 14 axioms · 163 sorries · locked-proven 8.

Apache-2.0. Copyright 2026 SZL Holdings · Stephen P. Lutar Jr. · ORCID [0009-0001-0110-4173](https://orcid.org/0009-0001-0110-4173).
