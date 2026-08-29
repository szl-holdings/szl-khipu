---
license: apache-2.0
library_name: numpy
tags:
  - governed-ai
  - khipu
  - szl-holdings
  - receipts
  - lambda-gate
  - 4-way-gate
  - silhouette
---

# ReceiptAgent-Nano

4-way gate silhouette. **The kernel is truth.**

ReceiptAgent-Nano proposes; it never executes and never overrides the kernel. The four class labels are **ALLOW / WARN / BLOCKED / ESCALATE**. `rule_check` is ground truth. The MLP is advisory. Policy deny-by-default is the same fail-closed spine (HARD_DENY / DENY_DEFAULT / LAMBDA_VETO / ALLOW). Λ is advisory (Conjecture 1 OPEN). `proven_trust` is false. Energy UNAVAILABLE. Not 1.5B. Not Qwen.

Canonical source: [szl-holdings/szl-khipu](https://github.com/szl-holdings/szl-khipu)  
Sibling card: [SZLHOLDINGS/szl-khipu](https://huggingface.co/SZLHOLDINGS/szl-khipu)

## 4-way gate

| Code | Who decides | Meaning |
|---|---|---|
| ALLOW | kernel `rule_check` | explicit allow and axes held |
| WARN | kernel `rule_check` | bound or yuyay floor missed |
| BLOCKED | kernel `rule_check` | hard deny, zero axis, or no allow |
| ESCALATE | kernel `rule_check` | chain/pin break — still not autonomous |

The kernel (`rule_check` / `deny_by_default`) is the ground truth. A trained silhouette that approximates the gate is **not** a substitute for the kernel, not proven trust, and not a uniqueness theorem. `decide()` always returns the kernel label.

```python
from szl_khipu.train import receipt_agent
from szl_khipu import deny_by_default

print(deny_by_default(allow=True, hard_deny=False, lambda_pass=True))
# ALLOW — kernel is truth; the agent does not override this

weights, ev = receipt_agent.train(seed=20260721)
# few-thousand-float silhouette, honesty REPORTED; kernel_wins = 1.0
```

## What it is NOT

- **Not SZL-Forge-1.5B-ReceiptAgent.** That Hub card is RESEARCH, proposal-only, never executes, GGUF not in a signed hash, **not trained here**.
- **Not szl-receiptagent-qwen35-0.8b-v2.** Not Qwen. Not 0.8B. Not 10.8M trainable adapters.
- **Not autonomy.** Not a tool-caller. Not a replacement for HARD_SECURITY.
- **Not joules, not CUDA. proven_trust stays false.**

## Honesty

| Claim | Label | What-NOT |
|---|---|---|
| Kernel 4-way gate | LIVE | kernel is truth; agent is not |
| Agent weights trained here | REPORTED | silhouette, not 1.5B |
| Λ | ADVISORY · Conjecture 1 OPEN | never a theorem, never proven trust |
| Energy | UNAVAILABLE | never a fabricated joule |
| CUDA | UNAVAILABLE | CPU numpy LIVE |
| 1.5B ReceiptAgent | RESEARCH elsewhere | not this artifact |

Doctrine v11 LOCKED · 749/14/163 · locked-proven 8. Apache-2.0. Copyright 2026 SZL Holdings · Stephen P. Lutar Jr. · ORCID [0009-0001-0110-4173](https://orcid.org/0009-0001-0110-4173).
