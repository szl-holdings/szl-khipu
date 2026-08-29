---
license: apache-2.0
library_name: numpy
tags:
  - governed-ai
  - khipu
  - szl-holdings
  - navigate
  - abstain
  - silhouette
---

# TinyKhipu-Nano

NAVIGATE / ABSTAIN silhouette. Cited IDs are hard-filtered to the offered set. A few thousand floats. **Not 1.5B. Not Qwen. Not GGUF.**

Canonical source: [szl-holdings/szl-khipu](https://github.com/szl-holdings/szl-khipu)  
Sibling card: [SZLHOLDINGS/szl-khipu](https://huggingface.co/SZLHOLDINGS/szl-khipu)

```python
from szl_khipu.train import tiny_khipu

weights, ev = tiny_khipu.train(seed=20260721, steps=280)
print(ev["plan_valid"], ev["abstain"], ev["hallucinated"])
# hallucinated == 0: the hard ID filter never cites off-list handles
tiny_khipu.save_npz("tiny_khipu.npz", weights)
```

## What it does

- Formula-token navigator over the locked-eight IDs plus NAVIGATE / ABSTAIN / honesty labels.
- **NAVIGATE** only when a locked formula token is in the query *and* in an offered handle.
- **ABSTAIN** otherwise. Abstain is the thing to beat, not a failure.
- Hallucinated citations are structurally impossible (filter, not a hope).

## What it is NOT

- **Not SZL-Khipu-1.5B.** That Hub card is RESEARCH (QLoRA proposal). Weights here are a CPU NumPy silhouette.
- **Not Qwen, not GGUF, not a chat model.**
- **Not proven trust.** Λ uniqueness remains Conjecture 1 OPEN.
- Energy **UNAVAILABLE**. CUDA **UNAVAILABLE**. Honesty **REPORTED**.

## Honesty

| Claim | Label | What-NOT |
|---|---|---|
| Weights trained in this package | REPORTED | silhouette, Not 1.5B |
| Hallucinated citations | 0 by construction | not a learned refusal |
| Λ | ADVISORY · Conjecture 1 OPEN | never a theorem |
| Energy | UNAVAILABLE | never a fabricated joule |
| CUDA | UNAVAILABLE | CPU numpy LIVE |

Doctrine v11 LOCKED · 749/14/163 · locked-proven 8. Apache-2.0. Copyright 2026 SZL Holdings · Stephen P. Lutar Jr. · ORCID [0009-0001-0110-4173](https://orcid.org/0009-0001-0110-4173).
