# SZL KHIPU — Hub card

GitHub is canonical: [szl-holdings/szl-khipu](https://github.com/szl-holdings/szl-khipu).
This file is the short Hub-facing summary. Full spec lives in [README.md](README.md).

**proven_trust is false. Conjecture 1 OPEN. energy UNAVAILABLE. CUDA UNAVAILABLE. CPU NumPy LIVE.**

```python
from szl_khipu import YUYAY_FLOORS, lambda_gate, yarqa_attn

gate = lambda_gate(list(YUYAY_FLOORS))
print(gate["score"], gate["passed"], gate["advisory"], gate["proven_trust"])
# advisory; Conjecture 1 OPEN; proven_trust false; energy UNAVAILABLE
```

| Field | Value |
|---|---|
| License | Apache-2.0 |
| Runtime | NumPy >= 1.26 · Python >= 3.11 |
| Λ | advisory weighted geometric mean, 13 Yuyay axes |
| Energy | UNAVAILABLE — never a fabricated joule |
| CUDA | UNAVAILABLE |
| Tiny trainers | TinyKhipu NAVIGATE/ABSTAIN, ReceiptAgent 4-way, moons 2→8→2 |
| Anatomy | five-organ fail-closed kernel · not a 3D rehost · energy UNAVAILABLE |
| Not | Qwen, 1.5B, FlashAttention, SageAttention, FlexAttention, vLLM |

Doctrine v11 LOCKED · 749/14/163 · locked-proven 8. Copyright 2026 SZL Holdings.
