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
  receipt_hash_binding: CHECKED_AT_EXACT_REVISION_2026_10_02
  jobs: UNKNOWN
  publication_eligible: false
  canonical_source: https://github.com/szl-holdings/szl-forge
  card_resync: 2026-09-25
---

> **Status: SOFTWARE / REFERENCE / TEST FIXTURE.** Not a production model.

# chakana

This repository contains a small NumPy reference artifact: evidence-class crossing silhouette: MEASURED/SIGNED/MODELED kept separate.
The broader organ remains roadmap work. The synthetic archive is present;
earlier statements that this repository had no weights are superseded.

## Intended-organ source and historical re-sync

Canonical source: [https://github.com/szl-holdings/szl-forge](https://github.com/szl-holdings/szl-forge) (kit directory [`chakana/README.md`](https://github.com/szl-holdings/szl-forge/blob/main/chakana/README.md)). The card text itself is mirrored from `szl-khipu/atelier/hf/chakana.md`. GitHub is canonical; Hugging Face is the mirror. Re-synced 2026-09-25.

## Weights on this Hub ID

- **OBSERVED** — `chakana.npz` (3,219 bytes) is on the Hub tree, together with `TRAINING_RECEIPT.json`, `LICENSE`, `provenance.json`, `status.json` and `bom/model-bom.cdx.json` (listed 2026-09-25 through the Hub file API; revision SHA not captured by this pass). It is a synthetic NumPy silhouette: a small two-layer MLP pack from a CPU/NumPy run, described by its own receipt as "synthetic silhouettes only — honest placeholders with real weights".
- **UNAVAILABLE** — production weights, any checkpoint of the intended organ, any loader or `config.json`. Intended base per the szl-forge kit: `Qwen/Qwen3-Embedding-0.6B` (no fine-tune of it is on this Hub ID, so `base_model` is deliberately not declared in the frontmatter).
- **UNAVAILABLE** — `TRAINING_RECEIPT.batch.json`, the "full 6-organ receipt" the receipt refers to, is not on this Hub ID.

What the szl-forge kit says: `chakana/README.md` and `chakana/HF_MODEL_CARD.md` describe the intended organ as bridge embeddings (sentence-transformers, `base_model: Qwen/Qwen3-Embedding-0.6B`, optional Matryoshka 256/512/1024), status ROADMAP, `Jobs UNKNOWN`, nDCG@10 UNKNOWN, `publication_eligible: false`, with a launcher that refuses to fire. Both files still say the Hub repository is a stub "(README + `.gitattributes` only). No weights." That sentence describes an earlier state: the synthetic archive below is now on the tree. It remains true that no encoder weights and no Qwen3-Embedding fine-tune are on this Hub ID.

**Disambiguation (from the kit).** a11oy CHAKANA wiring / tinkuy (`a11oy/organs/amaru/**/chakana_wiring.py`) is Andean-cross topology wiring, not this organ; MiniEmbed in `szl-kernels` is a different, smaller artifact.

## Intended use

Inspect synthetic artifacts and exercise software fixtures. The archive does
not include a packaged loader or `config.json` in this repository.
`from_pretrained` compatibility and hosted inference are unverified.

## Source and verification scope

The card-authoring source is `szl-khipu/atelier/hf/chakana.md`; its matching
`atelier-space/cards/chakana.md` is a document copy. The intended-organ kit
is separately maintained at
[`szl-forge/chakana/README.md`](https://github.com/szl-holdings/szl-forge/blob/7b236fafe163ac3e282edf699677e97fd5e1f331/chakana/README.md).
The kit's roadmap is not a published production checkpoint for this fixture.

The explicit Python consumer is `scripts/publish_reference_card.py`. It accepts
one reviewed model ID, an immutable GitHub source commit and expected Hub parent,
then publishes only `README.md` with conditional parent binding and immutable
byte readback. A paired source document alone does not establish publication.
No automatic model-card writer or inference deployment is enabled by this card.

## Artifact evidence

The 2026-10-02 UTC inspection downloaded `chakana.npz` and the unsigned
`TRAINING_RECEIPT.json` at exact model-type Hub revision
[`503cf50d56f786b4ea4e950c18c556e976b484d2`](https://huggingface.co/SZLHOLDINGS/chakana/tree/503cf50d56f786b4ea4e950c18c556e976b484d2).
The archive is 3,219 bytes and its computed SHA-256 is:

`3849772ee86fe09e8752e98250573564de66e814231b50c36e7d29b5b6c3dbd5`

The digest matches the receipt's stated digest. `numpy.load(..., allow_pickle=False)`
with NumPy 2.4.6 inspected the following finite numeric arrays.
The immutable observations are recorded in
[`docs/reference-fixture-verification-20261002.json`](../../docs/reference-fixture-verification-20261002.json).
This verifies byte consistency and array structure at that revision. It does not
replay training, authenticate the unsigned receipt or qualify a production model.

| Array | Shape | Data type |
| --- | --- | --- |
| `w1` | `[12, 16]` | `float64` |
| `b1` | `[16]` | `float64` |
| `w2` | `[16, 3]` | `float64` |
| `b2` | `[3]` | `float64` |
| `holdoutAcc` | `[]` | `float64` |
| `seed` | `[]` | `int64` |

## Reported training

The repository receipt reports seed `20260721`, `2000` steps,
synthetic accuracy `0.588333`, and loss `0.820603`.
These values were read from the receipt and were not independently rerun.
They do not establish field performance or authority to make operational decisions.

The unsigned receipt is dated 2026-09-01. It records no sample count,
split digest, evaluation protocol or GitHub source commit. Its `holdoutAcc`
field is not an independently qualified held-out evaluation.
`TRAINING_RECEIPT.batch.json`, referenced as a full six-organ receipt, is absent
from the inspected exact Hub tree. No independent training replay was performed.

## License-publication evidence

The Apache-2.0 declaration is retained. Existing `provenance.json` and `status.json`
describe a license-file publication from parent `46e3b791026ac17200f9ba2ee691de4f69955ad9`.
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
