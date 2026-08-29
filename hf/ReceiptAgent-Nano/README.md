---
license: apache-2.0
library_name: numpy
tags:
  - governed-ai
  - szl-holdings
  - doctrine-v11
  - nano
  - synthetic
---

# ReceiptAgent-Nano

ALLOW · DENY · ABSTAIN · ESCALATE. Escalation is a class, not a retry loop.

**Family.** nano · **Evidence.** SYNTHETIC · **Weights.** numpy · **Params.** 4-10-4

Hub: [SZLHOLDINGS/ReceiptAgent-Nano](https://huggingface.co/SZLHOLDINGS/ReceiptAgent-Nano)

## The cut

Anthropic refuses. NVIDIA rails. Unsloth trains. We add a fourth way: hand the decision to a human with a receipt. Loop-tax lives here.

A policy head that cannot silently succeed. Every output is one of four named gates.

### Silhouette → leave → SZL

| Leader | Take, then tweak |
|---|---|
| Anthropic | Constitutional refuse → typed DENY/ABSTAIN. |
| NVIDIA | NeMo Guardrails flow → four-way head. |
| Unsloth | Grown form is SZL-Forge-1.5B-ReceiptAgent. |

Nobody else ships this combination. That is the point of a one-of-one.

## Intended use

Fail-closed unit tests for the 4-way gate.

## Bench (this tree)

`TRAINING_RECEIPT.json` seed `20260721` · honesty **REPORTED** · kernel is truth

| Metric | Value |
|---|---|
| held-out agree vs rule_check | 0.905 |
| weights | `receipt_agent.npz` sha256 `8aca4d24c90d6159cbb2bb885c7a94822d715899437f58abe69fb5c9664a1381` |

Infers on `POST /api/infer {"kind":"receipt_agent"}`. Surrogate may disagree. Kernel wins. **Not 1.5B.**

## Limitations

- Synthetic 4-D features. Not a substitute for the 1.5B agent.
- Hub kernel labels are ALLOW/WARN/BLOCKED/ESCALATE — kernel is truth. This atelier MLP is a 4-class silhouette, not rule_check.

## Honesty

| Claim | Label |
|---|---|
| This card's numbers | SYNTHETIC |
| Energy / joules | UNAVAILABLE unless a signed meter says MEASURED |
| Λ uniqueness | Conjecture 1 OPEN — not a theorem |
| GGUF as the signed object | FALSE |

Doctrine v11 LOCKED · 749 declarations · 14 axioms · 163 sorries · locked-proven 8.

Apache-2.0. Copyright 2026 SZL Holdings · Stephen P. Lutar Jr. · ORCID [0009-0001-0110-4173](https://orcid.org/0009-0001-0110-4173).
