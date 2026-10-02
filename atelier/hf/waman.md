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
  synthetic_silhouette: waman.npz
  weights_on_hub: OBSERVED_SYNTHETIC_SILHOUETTE_ONLY
  production_weights: UNAVAILABLE
  base_model_finetune_on_hub: UNAVAILABLE
  training_receipt: TRAINING_RECEIPT.json
  receipt_hash_binding: CHECKED_AT_EXACT_REVISION_2026_10_02
  jobs: UNKNOWN
  publication_eligible: false
  canonical_source: https://github.com/szl-holdings/szl-forge
  card_resync: 2026-09-25
---

> **Status: SOFTWARE / REFERENCE / TEST FIXTURE.** Not a production model.

# waman

This repository contains a small NumPy reference artifact: C-UAS detector silhouette: box-and-receipt or fail-closed.
The broader organ remains roadmap work. The synthetic archive is present;
earlier statements that this repository had no weights are superseded.

## Intended-organ source and historical re-sync

Canonical source: [https://github.com/szl-holdings/szl-forge](https://github.com/szl-holdings/szl-forge) (kit directory [`waman/README.md`](https://github.com/szl-holdings/szl-forge/blob/main/waman/README.md)). The card text itself is mirrored from `szl-khipu/atelier/hf/waman.md`. GitHub is canonical; Hugging Face is the mirror. Re-synced 2026-09-25.

## Weights on this Hub ID

- **OBSERVED** — `waman.npz` (4,189 bytes) is on the Hub tree, together with `TRAINING_RECEIPT.json`, `LICENSE`, `provenance.json`, `status.json` and `bom/model-bom.cdx.json` (listed 2026-09-25 through the Hub file API; revision SHA not captured by this pass). It is a synthetic NumPy silhouette: a small two-layer MLP pack from a CPU/NumPy run, described by its own receipt as "synthetic silhouettes only — honest placeholders with real weights".
- **UNAVAILABLE** — production weights, any checkpoint of the intended organ, any loader or `config.json`. Intended base per the szl-forge kit: RF-DETR Nano through Large architecture (no such checkpoint is on this Hub ID; nothing to declare as `base_model`).
- **UNAVAILABLE** — `TRAINING_RECEIPT.batch.json`, the "full 6-organ receipt" the receipt refers to, is not on this Hub ID.

What the szl-forge kit says: `waman/README.md` describes the intended organ as a hawk detector on an RF-DETR Nano-through-Large architecture (never XL/2XL), with **no trainer in that directory**. Its `skip_receipt.json` records `status: SKIP-NO-ADMITTED-FRAMES`, `weights: UNAVAILABLE`, `jobs: UNKNOWN`, `evals: UNKNOWN`, `publication_eligible: false`, effector SIMULATED, and the claim boundary that `killinchu-osint-corpus` is not training-eligible.

**Alias.** [`SZLHOLDINGS/KILLINCHU-EYE`](https://huggingface.co/SZLHOLDINGS/KILLINCHU-EYE) is an alias of this organ (`szl-forge/waman/ALIASES.md`: same lane, not a second detector kit). That repository holds its own synthetic silhouette (`killinchu_eye.npz`) and receipt; neither repository holds detector weights.

## Intended use

Inspect synthetic artifacts and exercise software fixtures. The archive does
not include a packaged loader or `config.json` in this repository.
`from_pretrained` compatibility and hosted inference are unverified.

## Source and verification scope

The card-authoring source is `szl-khipu/atelier/hf/waman.md`; its matching
`atelier-space/cards/waman.md` is a document copy. The intended-organ kit
is separately maintained at
[`szl-forge/waman/README.md`](https://github.com/szl-holdings/szl-forge/blob/7b236fafe163ac3e282edf699677e97fd5e1f331/waman/README.md).
The kit's roadmap is not a published production checkpoint for this fixture.

The explicit Python consumer is `scripts/publish_reference_card.py`. It accepts
one reviewed model ID, an immutable GitHub source commit and expected Hub parent,
then publishes only `README.md` with conditional parent binding and immutable
byte readback. A paired source document alone does not establish publication.
No automatic model-card writer or inference deployment is enabled by this card.

## Artifact evidence

The 2026-10-02 UTC inspection downloaded `waman.npz` and the unsigned
`TRAINING_RECEIPT.json` at exact model-type Hub revision
[`a48b979a765c4f60b497204db2a418dbf0c957ff`](https://huggingface.co/SZLHOLDINGS/waman/tree/a48b979a765c4f60b497204db2a418dbf0c957ff).
The archive is 4,189 bytes and its computed SHA-256 is:

`9b31cf28e1877fb15eb9ef5ecafb4054612dc8418d1707b3f1f164b7296ef325`

The digest matches the receipt's stated digest. `numpy.load(..., allow_pickle=False)`
with NumPy 2.4.6 inspected the following finite numeric arrays.
The immutable observations are recorded in
[`docs/reference-fixture-verification-20261002.json`](../../docs/reference-fixture-verification-20261002.json).
This verifies byte consistency and array structure at that revision. It does not
replay training, authenticate the unsigned receipt or qualify a production model.

| Array | Shape | Data type |
| --- | --- | --- |
| `w1` | `[20, 16]` | `float64` |
| `b1` | `[16]` | `float64` |
| `w2` | `[16, 3]` | `float64` |
| `b2` | `[3]` | `float64` |
| `holdoutAcc` | `[]` | `float64` |
| `seed` | `[]` | `int64` |

## Reported training

The repository receipt reports seed `20260721`, `2000` steps,
synthetic accuracy `0.671667`, and loss `0.694394`.
These values were read from the receipt and were not independently rerun.
They do not establish field performance or authority to make operational decisions.

The unsigned receipt is dated 2026-09-01. It records no sample count,
split digest, evaluation protocol or GitHub source commit. Its `holdoutAcc`
field is not an independently qualified held-out evaluation.
`TRAINING_RECEIPT.batch.json`, referenced as a full six-organ receipt, is absent
from the inspected exact Hub tree. No independent training replay was performed.

## License-publication evidence

The Apache-2.0 declaration is retained. Existing `provenance.json` and `status.json`
describe a license-file publication from parent `3f57b4baeb346a874921291e0c2e3fd9379155c1`.
Their PUBLISHED state concerns `LICENSE`, `provenance.json` and `status.json`,
not synthetic-archive qualification, intended-organ training or a production release.
Those records leave copyright ownership and relicensing authority UNKNOWN;
artifact lineage, consent, privacy, training suitability, deployment and served
revision remain BLOCKED. Their `production_ready` value is false.

## Evidence boundaries

- Archive digest and array structure: inspected at the exact revision above.
- Training and evaluation: reported synthetic results only; no independent replay.
- Intended organ: roadmap work; jobs UNKNOWN and publication eligibility false.
- Production weights and base-model fine-tune: UNAVAILABLE in the inspected scope.
- Runtime, CUDA, operational deployment and energy: unverified.
- Proven trust: false in the unsigned training receipt.
- Lambda uniqueness remains Conjecture 1 OPEN, not a theorem.

Apache-2.0. Copyright 2026 SZL Holdings · Stephen P. Lutar Jr. · ORCID [0009-0001-0110-4173](https://orcid.org/0009-0001-0110-4173).
