---
license: apache-2.0
library_name: numpy
tags: [governed-ai, khipu, szl-holdings, receipts, lambda-gate]
---

# szl-khipu
<!-- szl:header v1 -->
<!-- badges: add this repo's CI / release / status badges here -->
[![org: szl-holdings](https://img.shields.io/badge/org-szl--holdings-black)](https://github.com/szl-holdings)
[![doctrine](https://img.shields.io/badge/doctrine-control%20before%20action%20%C2%B7%20evidence%20after-blue)](https://a-11-oy.com)

**Control before action. Evidence after.**

Part of the [szl-holdings](https://github.com/szl-holdings) estate ·
Product: [a-11-oy.com](https://a-11-oy.com) ·
Proof: [a11oy.net](https://a11oy.net)
<!-- /szl:header -->

**Knot the run. Hash the proof. Fail closed.**

Governed-AI khipu: an advisory Λ-gate, original YARQA canal attention, a TinyKhipu NAVIGATE/ABSTAIN silhouette, and hash-chained receipts. CPU numpy is LIVE. CUDA is UNAVAILABLE. energy UNAVAILABLE. `proven_trust` is always false.

Canonical GitHub source: [szl-holdings/szl-khipu](https://github.com/szl-holdings/szl-khipu)  
Hub card: [SZLHOLDINGS/szl-khipu](https://huggingface.co/SZLHOLDINGS/szl-khipu)  
Kernels: [SZLHOLDINGS/szl-khipu-kernels](https://huggingface.co/kernels/SZLHOLDINGS/szl-khipu-kernels)

## What it is

- A Python package (`szl_khipu`) that knots a run, hashes a receipt, and fail-closes on a zero axis or a broken chain.
- Λ: weighted geometric mean over 13 Yuyay axes, advisory, never proven trust.
- YARQA: contiguous canals; attend only inside the compartment; leak is the bound.
- TinyKhipu-Nano: NAVIGATE / ABSTAIN silhouette. A few thousand floats. Hard ID filter.
- ReceiptAgent-Nano: 4-way gate (HARD_DENY / DENY_DEFAULT / LAMBDA_VETO / ALLOW). **The kernel is truth.** The agent does not override it.
- Receipts: sha256 of weights, seed, steps, loss. Honesty **REPORTED**. Joules **null**.
- Organ integrity: five-organ fail-closed kernel of [szl-holdings/anatomy](https://github.com/szl-holdings/anatomy). HEART/YUYAY, YAWAR, YACHAY, OTel, Khipu skeleton. Not a Three.js rehost. The 3D atlas is SLSA L1 static viz.

## What it is NOT

- **Not Qwen.** Not a Qwen fine-tune, not a Qwen rehost, not a Qwen eval.
- **Not 1.5B.** Nothing in this tree trains or publishes SZL-Khipu-1.5B, KHIPU-R2, or ReceiptAgent 1.5B. Those Hub cards stay RESEARCH and are not produced here.
- **Not a FlashAttention rehost.** Not Dao `.cu`, not hopper/, not cute/, not Sage `csrc`, not vLLM paged `.cu`, not `flex_attention.py`.
- **Λ uniqueness is OPEN.** Conjecture 1 is not a theorem. Unconditional uniqueness under kernel A1–A5 is machine-checked FALSE.
- **Energy UNAVAILABLE.** Never a fabricated joule. MEASURED-NVML or honest null.
- Not trained weights at 1–2B. Not GGUF. Not a CUDA speedup. Not proven trust.

## Install

```bash
pip install -e .
pip install -e ".[gradio]"   # optional — Gradio 4 space
pip install -e ".[torch]"    # optional — torch path; CUDA still UNAVAILABLE here
```

Requires Python ≥ 3.11. Runtime dep: `numpy>=1.26`. Apache-2.0.

## Python frontend + backend

Stdlib HTTP. Same process serves the holographic UI and runs the kernels. No Gradio required.

```bash
szl-khipu serve --host 0.0.0.0 --port 7860
# GET  /healthz  /version  /api/lambda  /api/greenlight  /api/anatomy
# POST /api/lambda  /api/anatomy  /api/greenlight  /api/yarqa  /api/tiledigest
```

Gold = OPEN. Proof teal = LIVE. Never green-as-proven. Energy UNAVAILABLE. Conjecture 1 stays OPEN.

Static JS silhouette (not the NumPy kernel): [docs/index.html](docs/index.html) · [szl-holdings/khipu-pages](https://github.com/szl-holdings/khipu-pages) · [htmlpreview](https://htmlpreview.github.io/?https://github.com/szl-holdings/khipu-pages/blob/main/index.html).

## Quickstart

### Lambda (advisory)

```python
from szl_khipu import evaluate_lambda, YUYAY_FLOORS

ev = evaluate_lambda(list(YUYAY_FLOORS))
print(ev.value, ev.blocked, ev.reason)
# advisory pass — uniqueness remains Conjecture 1 OPEN

zeroed = list(YUYAY_FLOORS)
zeroed[0] = 0.0
print(evaluate_lambda(zeroed).blocked)  # True — fail closed
```

CLI:

```bash
szl-khipu demo-lambda
szl-khipu demo-lambda --zero 0
```

### YARQA (canal leak)

```python
import numpy as np
from szl_khipu import yarqa_attn

q = k = v = np.random.default_rng(7).standard_normal((12, 4))
out = yarqa_attn(q, k, v, n_canals=3)
print(out.leaked)  # bound: leaked ≤ 1e-9
```

```bash
szl-khipu demo-yarqa --n-canals 3
```

### Organ integrity (five organs)

Fail-closed substrate. Any DOWN organ or a WILLAY veto blocks the body. Λ stays Conjecture 1 OPEN. Energy UNAVAILABLE. Locked-proven stays 8. Not a Three.js rehost.

```python
from szl_khipu import evaluate_anatomy

ev = evaluate_anatomy(seed=11)
print(ev.live_count, ev.blocked, ev.energy)  # 5 False UNAVAILABLE

print(evaluate_anatomy(zero_heart=True).blocked)        # True
print(evaluate_anatomy(fabricate_joule=True).energy_j)  # None — never a fabricated joule
```

```bash
szl-khipu demo-anatomy
szl-khipu demo-anatomy --tamper-chain
szl-khipu demo-anatomy --fabricate-joule
```

Canonical anatomy repo: [szl-holdings/anatomy](https://github.com/szl-holdings/anatomy) · 3D atlas: [SZLHOLDINGS/anatomy](https://huggingface.co/spaces/SZLHOLDINGS/anatomy)

### Train TinyKhipu

```bash
szl-khipu train --seed 20260721 --steps 280 --out artifacts
# writes artifacts/tiny_khipu.npz + artifacts/training_receipt.json
szl-khipu verify artifacts/training_receipt.json
```

```python
from szl_khipu import train_tiny_khipu

result = train_tiny_khipu(seed=20260721, steps=280)
print(result.plan_valid, result.abstain, result.hallucinated)
```

Export all three silhouettes (TinyKhipu, ReceiptAgent, moons) and a combined receipt:

```bash
python scripts/train_and_export.py
# artifacts/*.npz + artifacts/TRAINING_RECEIPT.json
# honesty REPORTED · energy_j null · proven_trust false · whatNot listed
```

## Kernels vs field leaders (honest deltas)

| SZL cut | Field leader | Honest delta |
|---|---|---|
| TileReceipt (`szl-receipt-attn`) | FlashAttention (Dao et al., NeurIPS 2022) | Numeric silhouette of tiled fused attention. SHA receipt of the tiles. **No speedup claim.** Not a rehost of Dao `.cu` / hopper / cute. |
| BlockWitness (`szl-block-kv`) | PagedAttention / vLLM (Kwon et al., SOSP 2023) | Paged-KV gather with a digest of the block table. **No tokens/s.** Not a vLLM rehost. |
| ScoreMod Fiber (`szl-maskmod`) | FlexAttention (PyTorch, arXiv:2412.05496) | Original score_mod + block-mask path that receipts the mask digest. **No CUDA benches.** A swapped mask cannot stay silent. |
| YARQA-ATTN | SageAttention (Zhang et al., ICLR 2025) | **Not quantized attention.** Contiguous canals (Quechua *yarqa*), attend inside the compartment, receipt the partition. GPU cubins **UNAVAILABLE**. CPU numpy path **LIVE**. |
| Governed RMSNorm | RMSNorm (Zhang & Sennrich, 2019) / LayerNorm | Matches a reference and optionally chains a digest of the rounded output. **No speedup.** Digest is integrity, not authorship. |
| Λ-gate | UN HDI 2010 WGM / OECD composite indicators | WGM over [0,1] axes, fail-closed on any zero or non-finite axis, A1–A4 runtime checks. Uniqueness is **Conjecture 1 — OPEN**. Advisory, never proven trust. |
| govsign + provctl | in-toto / SLSA / Sigstore / DSSE | Governance predicate (Λ, energy, decision) as an envelope. `proven_trust` locked **false**. UNSIGNED is a first-class fallback, never a fake signature. SLSA L1 honest, L2 roadmap. |

This repo silhouettes Λ, YARQA, TinyKhipu, ReceiptAgent, and receipts in **numpy**. It does not replace those field leaders and does not inherit their benches.

## Locked-8

Lean locked-proven formulas = **exactly 8**. Lab numerics CHECKED ≠ Lean PROVEN. The F-number mapping onto any larger registry is UNKNOWN — never fabricated.

| ID | Name | Caveat |
|---|---|---|
| F1 | Replay-Hash Determinism | |
| F4 | Khipu DAG acyclicity | edges dst < src |
| F7 | Chaski FIFO | drain(enqueueAll([], msgs)) = msgs |
| F11 | Ayni Reciprocity Conservation | Σ in = Σ out |
| F12 | Kuramoto boundedness | additive fragment ONLY — not full nonlinear sync |
| F18 | RS(10,6) recovery | recoverable iff ≥ 6 of 10 shards |
| F19 | Bekenstein additive scaffolding | monotone fragment ONLY — not S ≤ 2πkRE/ℏc |
| F22 | Khipu emit monotonicity | sequence numbers strictly increase |

## Conjecture 1

> Any two aggregators satisfying A1–A4 agree on every input. **OPEN (sorry).** Unconditional uniqueness under kernel A1–A5 is machine-checked FALSE.

Λ is advisory. Trust ceiling 0.97. `proven_trust` is false in this artifact and every receipt it emits.

Axioms carried at runtime (checks, not a uniqueness proof):

| ID | Name |
|---|---|
| A1 | IsMonotone |
| A2 | IsHomogeneous  Λ(c·x)=c·Λ(x) |
| A3 | IsEgyptianExact  Λ(c,…,c)=c |
| A4 | IsBounded  Λ(x)≤max(x) |
| A5 | IsPermutationInvariant |

## Honesty

| Claim | Label |
|---|---|
| CPU numpy path | LIVE |
| CUDA / GPU cubins | UNAVAILABLE |
| Energy / joules | UNAVAILABLE (never fabricated) |
| Λ uniqueness | Conjecture 1 OPEN |
| proven_trust | false |
| TinyKhipu / ReceiptAgent / moons trained here | REPORTED silhouette, not 1.5B |
| SZL-Khipu-1.5B / ReceiptAgent 1.5B | RESEARCH, **not trained in this tree** |
| Weights at Hub 1–2B | not applicable |

Doctrine **v11 LOCKED** · 749 declarations · 14 axioms · 163 tracked sorries · locked-proven **8**.

## Hub siblings

| Artifact | What |
|---|---|
| [hf/TinyKhipu-Nano](hf/TinyKhipu-Nano/README.md) | NAVIGATE/ABSTAIN silhouette |
| [hf/ReceiptAgent-Nano](hf/ReceiptAgent-Nano/README.md) | 4-way gate; kernel is truth |
| [hf/szl-khipu-kernels](hf/szl-khipu-kernels/README.md) | Kernel Hub card; `get_kernel` |
| [space/](space/README.md) | Hub docker hologram — stdlib HTTP, no Gradio |
| [spaces/](spaces/README.md) | Gradio 5 (GitHub only; Hub Space is docker) |

## License

Apache-2.0. Copyright 2026 SZL Holdings.

Stephen P. Lutar Jr. / SZL Holdings · ORCID [0009-0001-0110-4173](https://orcid.org/0009-0001-0110-4173)

---

## Work with SZL Holdings

szl-khipu participates in the SZL governed-AI estate; the flagship control plane **governed agent change management** in production: signal → investigation → policy eval → human approval → bounded patch → signed closure receipt.

- **Design partners (6-month, paid):** governed-action receipts in your environment → [stephenlutar2@gmail.com](mailto:stephenlutar2@gmail.com)
- **Verify our claims offline:** [github.com/szl-holdings/szl-gov](https://github.com/szl-holdings/szl-gov) — signed estate receipt + public verifier
- **Pricing + SKUs:** see `docs/pricing` (Control / Assurance / Sovereign)
