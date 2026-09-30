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

> **Status: SOFTWARE / REFERENCE / TEST FIXTURE.** Not a production model.

This Hub repository contains a bare NumPy archive. The loading and forward-pass
implementation lives in the canonical `szl_khipu` package; no packaged Hub
loader or `config.json` is shipped alongside these weights. Treat this as a
software fixture until its complete inference contract is independently verified.

# TinyKhipu-Nano

Token embeddings and handles in. NAVIGATE or ABSTAIN out. Abstain is the default class, not a post-hoc filter.

**Family.** nano · **Evidence.** SYNTHETIC · **Weights.** numpy · **Architecture.** 24-token, 12-dimensional embedding with two-class and handle-scoring heads · **Not 1.5B.**

Hub: [SZLHOLDINGS/TinyKhipu-Nano](https://huggingface.co/SZLHOLDINGS/TinyKhipu-Nano)

## Reference fixture

A synthetic token-and-handle reference fixture for the NAVIGATE/ABSTAIN schema.
It mean-pools token embeddings and scores handle notes. This card makes no
ecosystem-wide novelty claim and establishes no predecessor relationship or
quality proxy for a 1.5B checkpoint.

## Intended use

Unit-test the NAVIGATE|ABSTAIN schema before GPU spend.

## Reported synthetic fixture evidence

`TRAINING_RECEIPT.json` seed `20260721` · steps 280 · honesty **REPORTED**

| Metric | Value |
|---|---|
| plan_valid | 1.00 |
| abstain | 1.00 |
| hallucinated | 0 |
| weights | `tiny_khipu.npz` receipt-reported sha256 `cc8d0385b2c75079669df809d7e4823f1ad8d9d535aec511446347490b11dff9` |

The related demo documents an application-specific `POST /api/infer` route.
This archive repository establishes no hosted endpoint, served revision, or
deployment guarantee. The route is illustrative application context.

## Limitations

- The shared unsigned receipt reports `plan_valid=1.0`, `abstain=1.0`, and
  `hallucinated=0.0` on its synthetic fixture. Named sample count, split identity,
  and generalization are not independently established by that receipt.
- These reported values are not a reliability guarantee or a sibling model evaluation.

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

The previous card reports `tiny_khipu.npz` (3,568 bytes). Receipt-reported SHA-256 (not rehashed in this review):

`cc8d0385b2c75079669df809d7e4823f1ad8d9d535aec511446347490b11dff9`

The previous card reported that the archive matched the unsigned training
receipt and that `numpy.load(..., allow_pickle=False)` found finite numeric
arrays. The table below preserves that historical report. The September 30,
2026 card review read pinned text and the receipt; it did not download, rehash,
or inspect the archive, and did not replay training.

| Array | Shape | Data type |
| --- | --- | --- |
| `E` | `[24, 12]` | `float64` |
| `W` | `[2, 12]` | `float64` |
| `b` | `[2]` | `float64` |
| `Wc` | `[12]` | `float64` |

An independently checked archive/receipt match could establish local artifact
consistency; an unsigned digest would still not authenticate authorship or
measurement. These preserved receipt and array reports establish no new
training replay, independent evaluation, deployment, or production readiness.

Reviewed Hub text: [immutable snapshot `d890010f874ecafd3f2f1ef4066d84b810ba775e`](https://huggingface.co/SZLHOLDINGS/TinyKhipu-Nano/blob/d890010f874ecafd3f2f1ef4066d84b810ba775e/README.md).
Reviewed publisher source: [`hf/TinyKhipu-Nano/README.md` at `e53e3d24b22e356eb986c373aee27b3b3e7947ec`](https://github.com/szl-holdings/szl-khipu/blob/e53e3d24b22e356eb986c373aee27b3b3e7947ec/hf/TinyKhipu-Nano/README.md).
The shared unsigned [`TRAINING_RECEIPT.json`](https://huggingface.co/SZLHOLDINGS/TinyKhipu-Nano/blob/d890010f874ecafd3f2f1ef4066d84b810ba775e/TRAINING_RECEIPT.json), timestamped
`2026-08-29T17:11:32.518042+00:00`, enumerates four artifacts. Only its
`artifacts["tiny_khipu.npz"]` entry describes this archive; the other
entries do not establish that sibling artifacts are present in this repository.
The receipt does not bind its training run to the reviewed source commit.
