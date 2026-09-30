---
license: apache-2.0
library_name: other
tags:
  - governed-ai
  - szl-holdings
  - doctrine-v11
  - roadmap
  - software
  - reference
  - test-fixture
szl:
  doctrine: v11-LOCKED
  artifact_class: SYNTHETIC_NUMPY_SILHOUETTE
  synthetic_silhouette: chakana.npz
  weights_on_hub: OBSERVED_SYNTHETIC_SILHOUETTE_ONLY
  production_weights: UNAVAILABLE
  base_model_finetune_on_hub: UNAVAILABLE
  training_receipt: TRAINING_RECEIPT.json
  receipt_hash_binding: STATED_BY_CARD_NOT_RECHECKED_2026_09_25
  jobs: UNKNOWN
  publication_eligible: false
---

> **Status: SOFTWARE / REFERENCE / TEST FIXTURE.** Not a production model.

# chakana

This repository contains a small NumPy reference artifact: evidence-class crossing silhouette: MEASURED/SIGNED/MODELED kept separate.
The broader organ remains roadmap work. The synthetic archive is present;
earlier statements that this repository had no weights are superseded.

## Source and review scope

The reviewed card-authoring baseline is
[`szl-khipu/atelier/hf/chakana.md`](https://github.com/szl-holdings/szl-khipu/blob/e53e3d24b22e356eb986c373aee27b3b3e7947ec/atelier/hf/chakana.md).
The existing 2026-09-30 source audit identifies the separate intended-organ
kit as
[`szl-forge/chakana/README.md`](https://github.com/szl-holdings/szl-forge/blob/5b3dfdf9beafe0d6d1e6043ca005ec4b17c45204/chakana/README.md).
The kit is not evidence of a published production checkpoint or base-model
fine-tune for this synthetic fixture. No `base_model` metadata is claimed here.

The 2026-09-30 documentation review read the card, unsigned training receipt,
license and license-publication records at model-type Hub revision
[`503cf50d56f786b4ea4e950c18c556e976b484d2`](https://huggingface.co/SZLHOLDINGS/chakana/tree/503cf50d56f786b4ea4e950c18c556e976b484d2).
The earlier 2026-09-25 re-sync reported an inventory observation without
capturing its revision SHA. This later small-file review does not retroactively
identify that observation's revision or recheck the archive bytes.

The automated Hugging Face model-card consumer for this authoring file remains
UNKNOWN. Matching `atelier-space/cards/chakana.md` is a document-parity
requirement; it does not establish a model publication route or served revision.

## Intended use

Inspect synthetic artifacts and exercise software fixtures. The archive does
not include a packaged loader or `config.json` in this repository.
`from_pretrained` compatibility and hosted inference are unverified.

## Artifact evidence

The earlier card and 2026-09-25 re-sync report `chakana.npz` at
3,219 bytes. The unsigned `TRAINING_RECEIPT.json` states this SHA-256:

`3849772ee86fe09e8752e98250573564de66e814231b50c36e7d29b5b6c3dbd5`

The earlier card reports that the archive matched that receipt and that
`numpy.load(..., allow_pickle=False)` found finite numeric arrays. The re-sync
did not repeat the digest or array checks. This 2026-09-30 documentation review
also did not download, rehash or load the archive. The table retains the
earlier card's reported array description; it is not a new validation result.

| Array | Shape | Data type |
| --- | --- | --- |
| `w1` | `[12, 16]` | `float64` |
| `b1` | `[16]` | `float64` |
| `w2` | `[16, 3]` | `float64` |
| `b2` | `[3]` | `float64` |
| `holdoutAcc` | `[]` | `float64` |
| `seed` | `[]` | `int64` |

Reading a receipt's stated digest does not independently verify the current
archive or the signer. No training replay, runtime test, deployment, general
intelligence or production-readiness claim follows from this review.

## Reported training

The repository receipt reports seed `20260721`, `2000` steps,
synthetic accuracy `0.588333`, and loss `0.820603`.
These values were read from the receipt and were not independently rerun.
They do not establish field performance or authority to make operational decisions.

The unsigned receipt is dated 2026-09-01. It does not record a sample count,
split digest, evaluation protocol or GitHub source commit. The historically
reported `holdoutAcc` field does not establish an independently verified
held-out evaluation. `TRAINING_RECEIPT.batch.json`, referenced as a full
six-organ receipt, was unavailable on the reviewed Hub ID.

## License-publication evidence

The Apache-2.0 declaration and standalone `LICENSE` are retained unchanged.
`provenance.json` and `status.json` describe an earlier license-file publication
from parent `46e3b791026ac17200f9ba2ee691de4f69955ad9`.
Their PUBLISHED state concerns `LICENSE`, `provenance.json` and `status.json`;
it does not qualify the synthetic archive, its training or a production release.

Those records leave copyright ownership and relicensing authority UNKNOWN.
Artifact lineage, consent, privacy review, training suitability, deployment and
served revision remain BLOCKED; `production_ready` is false. License-file
presence does not resolve those boundaries.

## Evidence boundaries

- Archive digest and array inspection: historical card reports, not rechecked
  by the 2026-09-25 re-sync or this 2026-09-30 documentation review.
- Training and evaluation: reported synthetic evidence only; no independent
  replay or qualified held-out result.
- Intended organ: roadmap work; jobs UNKNOWN, publication eligibility false.
  The present synthetic fixture is not the intended organ's checkpoint.
- Production weights and base-model fine-tune: UNAVAILABLE in the reviewed
  card's stated scope.
- Current runtime, CUDA, production deployment and energy: unverified.
- Proven trust: false in the published training receipt.
- Lambda uniqueness remains Conjecture 1 OPEN, not a theorem.

Apache-2.0. Copyright 2026 SZL Holdings · Stephen P. Lutar Jr. · ORCID [0009-0001-0110-4173](https://orcid.org/0009-0001-0110-4173).
