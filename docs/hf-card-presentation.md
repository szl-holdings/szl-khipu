# Hugging Face card presentation

This change aligns the six existing model cards and the Docker Space card with
the shared SZL presentation. Each opens with the actual artifact, its current
stage, an explorer/source/evidence route, and the limits needed before use.
The four Nano cards also retain the eight matching copies required by
`tests/test_hf_model_metadata.py`.

The invariant is exact preservation: original YAML frontmatter, licenses, and
the complete original body remain unchanged. The body is inside the
`SZL-CARD-TECHNICAL:v1` disclosure. The source revision before presentation is
`8d06c9333b636a86a27d88feb49097906833af30`.

## Reviewable source map

[`publishing/hf-card-presentation.v1.json`](../publishing/hf-card-presentation.v1.json)
records seven unique targets, eight auxiliary copies, original Git blobs,
frontmatter/body/file SHA256 values, final file SHA256 values, and the existing
publisher route. Its Hub and provider observations are dated immutable
observations. They are not current serving or qualification claims.

The original bytes can be recovered with `git show <source revision>:<path>`.
Compare their frontmatter directly with the new file, and compare the remaining
body with the bytes between the technical disclosure markers. Auxiliary Nano
copies must still match their canonical `hf/<name>/README.md` file exactly.

## Existing publication routes

| Target | Authoring source | Existing route |
|---|---|---|
| `models/SZLHOLDINGS/szl-khipu` | Root `README.md` | Immutable model software projection |
| Four Nano models | `hf/<name>/README.md` | Existing explicit Nano publication list |
| `models/SZLHOLDINGS/szl-khipu-kernels` | `hf/szl-khipu-kernels/README.md` | Existing card update; package parity is separate |
| `spaces/SZLHOLDINGS/szl-khipu` | `space/README.md` | Existing Docker Space projection |

All four routes already run through `scripts/publish_hf.py` and
`.github/workflows/publish-hf.yml`. This presentation change does not modify
their authority, credentials, managed file sets, runtime code, artifact bytes,
or tests. A normal protected-main publication still performs that workflow's
existing complete projection and requires its source/readback evidence.

The Nano and kernel-pack targets have additional existing card sources in
`szl-atelier`; TinyKhipu-Nano and ReceiptAgent-Nano also have Forge card sources.
The map records those paths rather than claiming a sole writer. The Atelier
four-feature Tiny/Receipt fixtures and the Khipu package fixtures have different
schemas; a matching title does not make their artifacts or evidence equivalent.

## Validation and publication boundary

Review the existing metadata parity, honesty documentation, reference-card
publication, immutable model software, and Space source-binding contracts.
The map is a source-review receipt, not a Hub publication receipt.

The shared holographic mark must be published by its canonical `.github`
source before downstream card publication is represented as complete. No
primary inference endpoint is claimed: these cards link to the existing
Command Lab explorer. Software presence, dated provider listings, historical
measurements, and synthetic fixtures do not promote a model or native kernel
release.

