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

# chakana

This repository contains a small NumPy reference artifact: evidence-class crossing silhouette: MEASURED/SIGNED/MODELED kept separate.
The broader organ remains roadmap work. The synthetic archive is present;
earlier statements that this repository had no weights are superseded.

## Intended use

Inspect synthetic artifacts and exercise software fixtures. The archive does
not include a packaged loader or `config.json` in this repository.
`from_pretrained` compatibility and hosted inference are unverified.

## Artifact evidence

`chakana.npz` is present (3,219 bytes). SHA-256:

`3849772ee86fe09e8752e98250573564de66e814231b50c36e7d29b5b6c3dbd5`

The archive hash matches `TRAINING_RECEIPT.json`. Its arrays were inspected
with `numpy.load(..., allow_pickle=False)`; numeric values were finite.

| Array | Shape | Data type |
| --- | --- | --- |
| `w1` | `[12, 16]` | `float64` |
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
synthetic accuracy `0.588333`, and loss `0.820603`.
These values were read from the receipt and were not independently rerun.
They do not establish field performance or authority to make operational decisions.

## Evidence boundaries

- Artifact bytes and receipt hash: checked at the pinned repository revision.
- Training and evaluation: reported synthetic evidence only.
- Production deployment, runtime correctness, and energy: unverified.
- Proven trust: false in the published training receipt.
- Lambda uniqueness remains Conjecture 1 OPEN, not a theorem.

Apache-2.0. Copyright 2026 SZL Holdings · Stephen P. Lutar Jr. · ORCID [0009-0001-0110-4173](https://orcid.org/0009-0001-0110-4173).
