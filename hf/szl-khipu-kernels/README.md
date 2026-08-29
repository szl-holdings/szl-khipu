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

Kernel-Hub card for the SZL KHIPU NumPy silhouettes. **This is a kernel suite, not a checkpoint.** Do not treat Chaski FIFO as a Hub model card.

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
```

Package fallback (labeled; not a Hub load):

```python
from szl_khipu import (
    evaluate_lambda, yarqa_attn, evaluate_greenlight, evaluate_anatomy,
    run_chaski, run_ayni, run_shard, run_bay, run_prefix, run_route,
)

gate = evaluate_lambda([0.95] * 13)
print(gate["value"], gate["blocked"], gate["proven_trust"])  # advisory; Conjecture 1 OPEN

import numpy as np
q = kv = np.random.default_rng(7).standard_normal((12, 4))
_out, _probs, leaked = yarqa_attn(q, kv, kv, n_canals=3)
print(leaked)  # bound ≤ 1e-9

print(run_prefix(11, hijack=0)["hold"])  # 1
print(run_prefix(11, hijack=1)["hold"])  # 0 · poison after digest
print(run_route(11, tamper=0)["hold"])   # 1
print(run_route(11, tamper=1)["hold"])   # 0 · expert swap
```

HTTP hologram (same process as the kernels):

```
GET  /api/bench
POST /api/infer   {"kind":"tiny_khipu","query":"resolve F18 handle"}
POST /api/prefix  {"hijack":1}
POST /api/route   {"tamper":1}
```

GitHub source: [szl-holdings/szl-khipu](https://github.com/szl-holdings/szl-khipu).

## Live original cuts (not rehosts)

| Kernel | Field leader we cut from | Bound | Status |
|---|---|---|---|
| TileReceipt | FlashAttention | residual vs naive | LIVE |
| ScoreMod | FlexAttention | future mass = 0 | LIVE |
| BlockWitness | vLLM PagedAttention | table digest | LIVE |
| YARQA | SageAttention | canal leak = 0 | LIVE |
| PrefixWitness | SGLang RadixAttention | poison after digest → BLOCKED | LIVE |
| RouteWitness | Mixtral / Switch MoE | expert swap → BLOCKED | LIVE |
| GreenLight / Ari | signed assent (dual of Willay) | sorry cannot paint | LIVE |
| Kay Pacha / Anatomy | five-organ substrate | zero HEART fail-closes | LIVE |
| Chaski FIFO | F7 silhouette | reorder/drop → BLOCKED | LIVE · **not a Hub checkpoint** |
| Ayni | residual bus | skip leak → BLOCKED | LIVE |
| ShardWitness | RS(10,6) GF(257) | need 6 of 10 | LIVE · CHECKED ≠ Lean PROVEN |
| Evidence Bay | four rails | Space is not proof | LIVE |
| GovEnvelope | DSSE envelope | STRUCTURAL-ONLY · never a fake key | LIVE |
| Invariants | locked-8 | energy UNAVAILABLE · uniqueness OPEN | LIVE |
| Λ gate | WGM | Conjecture 1 OPEN | ADVISORY |

## Honesty

| Path | Status |
|---|---|
| CPU NumPy | LIVE |
| CUDA / Triton cubin | UNAVAILABLE |
| Energy | UNAVAILABLE — never a fabricated joule |
| proven_trust | false |
| Conjecture 1 | OPEN |
| 1.5B / Qwen / Mixtral / SGLang weights | not scraped, not rehosted, not trained here |
| Not | FlashAttention, SageAttention, FlexAttention, vLLM, Mixtral, SGLang |

Apache-2.0. Copyright 2026 SZL Holdings. Doctrine v11 LOCKED.
