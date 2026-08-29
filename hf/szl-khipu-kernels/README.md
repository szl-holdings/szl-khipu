---
license: apache-2.0
library_name: kernels
tags:
  - kernels
  - governed-ai
  - khipu
  - lambda-gate
  - yarqa
  - numpy
---

# szl-khipu-kernels

Kernel-Hub card for the SZL KHIPU NumPy silhouettes.

**CPU numpy path LIVE. CUDA UNAVAILABLE** this session — that is honesty, not a missing bench.

```python
from kernels import get_kernel

k = get_kernel(
    "SZLHOLDINGS/szl-khipu-kernels",
    revision="main",
    trust_remote_code=True,
)
# CPU numpy path is LIVE.
# CUDA is UNAVAILABLE this session — that is honesty, not a missing bench.

print(k.CONJECTURE_1)
gate = k.lambda_gate([0.95] * 13)
print(gate["score"], gate["passed"], gate["proven_trust"])  # advisory; Conjecture 1 OPEN

import numpy as np
q = kv = np.random.default_rng(7).standard_normal((12, 4))
_out, _probs, leaked = k.yarqa_attn(q, kv, kv, n_canals=3)
print(leaked)  # bound ≤ 1e-9
```

CPU fallback when Kernel Hub is not in the environment (labeled; not a Hub load):

```python
from szl_khipu import YUYAY_FLOORS, evaluate_lambda, yarqa_attn, lambda_gate
```

GitHub source: [szl-holdings/szl-khipu](https://github.com/szl-holdings/szl-khipu).

| Path | Status |
|---|---|
| CPU NumPy | LIVE |
| CUDA / Triton cubin | UNAVAILABLE |
| Energy | UNAVAILABLE — never a fabricated joule |
| proven_trust | false |
| Conjecture 1 | OPEN |
| Not | FlashAttention, SageAttention, FlexAttention, vLLM |

Apache-2.0. Copyright 2026 SZL Holdings. Doctrine v11 LOCKED.
