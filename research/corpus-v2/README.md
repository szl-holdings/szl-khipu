# SZL corpus-v2: open-asset ingestion layer

Purpose: give the SZL khipu research program a **receipts-native ingestion layer** for the field's newly published open assets, with the same discipline as corpus-v1 (hash-pinned, idempotent fetchers, license respect, fail-closed).

**Status (2026-11-19): EXECUTED.** `fetch_open_assets.py` ran on a clean environment; all four open assets fetched and SHA-256-pinned in `fetch_manifest.csv`. The Khipu-ML license was verified on fetch (MIT, Copyright (c) 2026 Maria Contreras). Nothing rights-flagged was fetched.

## OKR pin (unchanged)

The analysis in `research/okr_corpus` pins OKR `data/khipu.db` at upstream commit `4039ca51` (v2.1.0 lineage; 619 khipus / 54,403 cords / 110,677 knots; MIT, [khipulab/open-khipu-repository](https://github.com/khipulab/open-khipu-repository)). Corpus-v2 does not change that pin; it layers new open assets alongside it. Every corpus-v2 manifest row cites its upstream source and license basis. OKR credits stay upstream's.

## Ingested (open assets, training admissibility noted)

| Asset | Source | License (MEASURED) | Contents | Training use |
|---|---|---|---|---|
| KDB recovery record v1.0 | Zenodo DOI [10.5281/zenodo.21514490](https://doi.org/10.5281/zenodo.21514490) | Open deposit | Per-file SHA-256 manifest of the recovered Harvard KDB DataTables, idempotent recovery tool, validation reports — **not** the recovered sheets | Admissible (provenance/reference layer) |
| Contreras 2607.00185 | [arXiv](https://arxiv.org/abs/2607.00185) | arXiv non-exclusive license | Clustering, provenance classification, Santa Valley Match validation | Admissible (open scholarship corpus) |
| Contreras 2610.38580 | [arXiv](https://arxiv.org/abs/2610.38580) | arXiv non-exclusive license | KFG re-analysis: cataloger confound, null models, Ascher sum-relation | Admissible (open scholarship corpus) |
| Khipu-ML code | [GitHub](https://github.com/mcontrerasmalpar-pixel/khipu-ml) | **MIT verified on fetch** (Copyright (c) 2026 Maria Contreras) | Open code + data | Admissible |

## Catalogued, NOT trained on (license-encumbered)

| Asset | Source | License (MEASURED) | Handling |
|---|---|---|---|
| Khipu-Biblio Cross-Reference (KBCR) | [Melbourne Figshare](https://figshare.unimelb.edu.au/articles/dataset/Khipu-Biblio_Cross-Reference_KBCR_Resource/25661322), published 2026-03-13 | **CC BY-NC-SA 4.0** | Catalogue entry only. Non-commercial + share-alike terms make it inadmissible for the training corpus; used solely as a bibliographic reference. Attribution preserved; no sublicense implied. |
| Recovered KDB sheets (14 alternate assessments, AB001=KH0701, Urton type tables) | pending OKR board response to [khipulab#1](https://github.com/khipulab/open-khipu-repository/issues/1) | rights not settled | NOT fetched, NOT mirrored, NOT trained on — see `NOT_REDISTRIBUTABLE.md` |

## Method

`fetch_open_assets.py` is stdlib-only, idempotent, records per-file SHA-256 in `fetch_manifest.csv`, and fails closed on hash mismatch. Re-runs skip files that already match. License text is verified on fetch, not assumed.
