---
license: apache-2.0
library_name: numpy
tags:
  - governed-ai
  - szl-holdings
  - doctrine-v11
  - nano
  - synthetic
  - software
  - reference
  - test-fixture
---

<!-- SZL-CARD-PRESENTATION:v1 -->
<p><a href="https://huggingface.co/spaces/SZLHOLDINGS/szl-command-lab"><img src="https://raw.githubusercontent.com/szl-holdings/.github/main/profile/assets/szl/logos/szl_mark_holographic.svg" alt="SZL Holdings" width="112" /></a></p>

# ReceiptAgent-Nano

A small synthetic reference head for proposing ALLOW, WARN, BLOCKED, or ESCALATE from receipt features.

**Artifact:** Bare NumPy weight archive · **Stage:** Synthetic test fixture

[Explore in Command Lab](https://huggingface.co/spaces/SZLHOLDINGS/szl-command-lab) · [Build](https://github.com/szl-holdings/szl-khipu) · [Evidence](https://github.com/szl-holdings/szl-khipu/blob/8d06c9333b636a86a27d88feb49097906833af30/hf/ReceiptAgent-Nano/README.md)

## Before you use it

- The learned head is advisory; deterministic rule_check remains the authority for admission.
- Reported synthetic agreement is not an independently reproduced holdout result or a production guarantee.
- The package's 24-feature fixture is separate from the Atelier four-feature MLP and the 1.5B agent. Verify archive, loader, labels, and immutable revision together.

<details>
<summary>Technical details and evidence</summary>

<!-- SZL-CARD-TECHNICAL:v1:START -->

> **Status: SOFTWARE / REFERENCE / TEST FIXTURE.** Not a production model.

This Hub repository contains a bare NumPy archive. The loading and forward-pass
implementation lives in the canonical `szl_khipu` package; no packaged Hub
loader or `config.json` is shipped alongside these weights. Treat this as a
software fixture until its complete inference contract is independently verified.

# ReceiptAgent-Nano

Synthetic four-class policy surrogate. Escalation is a class in the reviewed
implementation; this fixture does not establish a runtime retry loop.

**Family.** nano · **Evidence.** SYNTHETIC · **Weights.** numpy · **Architecture.** 24-16-8-4 MLP

Hub: [SZLHOLDINGS/ReceiptAgent-Nano](https://huggingface.co/SZLHOLDINGS/ReceiptAgent-Nano)

## Reference fixture

A small synthetic four-class reference fixture for testing policy-output
schemas. Its learned predictions are advisory; they do not override the
deterministic rule checker. No comparative safety or ecosystem-wide novelty
claim is made.

## Intended use

Test advisory four-class output schemas alongside the separately authoritative rule checker.

## Reported synthetic fixture evidence

`TRAINING_RECEIPT.json` seed `20260721` · honesty **REPORTED** · kernel is truth

| Metric | Value |
|---|---|
| receipt-reported agreement vs rule_check | 0.905 |
| weights | `receipt_agent.npz` receipt-reported sha256 `8aca4d24c90d6159cbb2bb885c7a94822d715899437f58abe69fb5c9664a1381` |

The related demo documents an application-specific `POST /api/infer` route.
This archive repository establishes no hosted endpoint, served revision, or
deployment guarantee. The route is illustrative application context.

## Limitations

- Synthetic 24-dimensional features. Not a substitute for the 1.5B agent.
- The [reviewed implementation](https://github.com/szl-holdings/szl-khipu/blob/e53e3d24b22e356eb986c373aee27b3b3e7947ec/szl_khipu/train/receipt_agent.py)
  defines class indices `0=ALLOW`, `1=WARN`, `2=BLOCKED`, `3=ESCALATE`, and keeps
  the deterministic `rule_check` decision authoritative. The former package
  summary named a different label set; that set must not be substituted here.
- The shared receipt does not bind an exact training/source revision, class
  mapping, held-out sample count, or split digest to this archive. Current-source
  inspection is not a recovered historical training contract. Agreement `0.905`
  is a reported synthetic result, not independently auditable production accuracy.

## Honesty

| Claim | Label |
|---|---|
| This card's numbers | SYNTHETIC |
| Energy / joules | UNAVAILABLE unless a signed meter says MEASURED |
| Λ uniqueness | Conjecture 1 OPEN — not a theorem |
| GGUF as the signed object | FALSE |

Doctrine v11 LOCKED · 749 declarations · 14 axioms · 163 sorries · locked-proven 8.

Apache-2.0. Copyright 2026 SZL Holdings · Stephen P. Lutar Jr. · ORCID [0009-0001-0110-4173](https://orcid.org/0009-0001-0110-4173).

## Artifact evidence

The previous card reports `receipt_agent.npz` (6,014 bytes). Receipt-reported SHA-256 (not rehashed in this review):

`8aca4d24c90d6159cbb2bb885c7a94822d715899437f58abe69fb5c9664a1381`

The previous card reported that the archive matched the unsigned training
receipt and that `numpy.load(..., allow_pickle=False)` found finite numeric
arrays. The table below preserves that historical report. The September 30,
2026 card review read pinned text and the receipt; it did not download, rehash,
or inspect the archive, and did not replay training.

| Array | Shape | Data type |
| --- | --- | --- |
| `W1` | `[16, 24]` | `float64` |
| `b1` | `[16]` | `float64` |
| `W2` | `[8, 16]` | `float64` |
| `b2` | `[8]` | `float64` |
| `W3` | `[4, 8]` | `float64` |
| `b3` | `[4]` | `float64` |

An independently checked archive/receipt match could establish local artifact
consistency; an unsigned digest would still not authenticate authorship or
measurement. These preserved receipt and array reports establish no new
training replay, independent evaluation, deployment, or production readiness.

Reviewed Hub text: [immutable snapshot `463df555fee339b776b938846238327100f573ab`](https://huggingface.co/SZLHOLDINGS/ReceiptAgent-Nano/blob/463df555fee339b776b938846238327100f573ab/README.md).
Reviewed publisher source: [`hf/ReceiptAgent-Nano/README.md` at `e53e3d24b22e356eb986c373aee27b3b3e7947ec`](https://github.com/szl-holdings/szl-khipu/blob/e53e3d24b22e356eb986c373aee27b3b3e7947ec/hf/ReceiptAgent-Nano/README.md).
The shared unsigned [`TRAINING_RECEIPT.json`](https://huggingface.co/SZLHOLDINGS/ReceiptAgent-Nano/blob/463df555fee339b776b938846238327100f573ab/TRAINING_RECEIPT.json), timestamped
`2026-08-29T17:11:32.518042+00:00`, enumerates four artifacts. Only its
`artifacts["receipt_agent.npz"]` entry describes this archive; the other
entries do not establish that sibling artifacts are present in this repository.
The receipt does not bind its training run to the reviewed source commit.

<!-- SZL-CARD-TECHNICAL:v1:END -->

</details>
