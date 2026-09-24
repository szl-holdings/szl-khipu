---
license: apache-2.0
library_name: other
tags:
  - governed-ai
  - szl-holdings
  - doctrine-v11
  - roadmap
  - roadmap
  - software
  - reference
  - test-fixture
---

> **Status: SOFTWARE / REFERENCE / TEST FIXTURE.** Not a production model.

# waman

This repository contains a small NumPy reference artifact: C-UAS detector silhouette: box-and-receipt or fail-closed.
The broader organ remains roadmap work. The synthetic archive is present;
earlier statements that this repository had no weights are superseded.

## Intended use

Inspect synthetic artifacts and exercise software fixtures. The archive does
not include a packaged loader or `config.json` in this repository.
`from_pretrained` compatibility and hosted inference are unverified.

## Artifact evidence

`waman.npz` is present (4,189 bytes). SHA-256:

`9b31cf28e1877fb15eb9ef5ecafb4054612dc8418d1707b3f1f164b7296ef325`

The archive hash matches `TRAINING_RECEIPT.json`. Its arrays were inspected
with `numpy.load(..., allow_pickle=False)`; numeric values were finite.

| Array | Shape | Data type |
| --- | --- | --- |
| `w1` | `[20, 16]` | `float64` |
| `b1` | `[16]` | `float64` |
| `w2` | `[16, 3]` | `float64` |
| `b2` | `[3]` | `float64` |
| `holdoutAcc` | `[]` | `float64` |
| `seed` | `[]` | `int64` |

A matching unsigned receipt establishes local artifact consistency. Training
metrics remain reported synthetic results; this check does not independently
reproduce training or establish deployment, general intelligence, or production readiness.

## Reported training

The repository receipt reports seed `20260721`, `2000` steps,
synthetic accuracy `0.671667`, and loss `0.694394`.
These values were read from the receipt and were not independently rerun.
They do not establish field performance or authority to make operational decisions.

## Evidence boundaries

- Artifact bytes and receipt hash: checked at the pinned repository revision.
- Training and evaluation: reported synthetic evidence only.
- Production deployment, runtime correctness, and energy: unverified.
- Proven trust: false in the published training receipt.
- Lambda uniqueness remains Conjecture 1 OPEN, not a theorem.

Apache-2.0. Copyright 2026 SZL Holdings · Stephen P. Lutar Jr. · ORCID [0009-0001-0110-4173](https://orcid.org/0009-0001-0110-4173).
