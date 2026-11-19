# SZL corpus-v2: open-asset ingestion layer

Purpose: give the SZL khipu research program a **receipts-native ingestion layer** for the field's newly published open assets, with the same discipline as corpus-v1 (hash-pinned, idempotent fetchers, license respect, fail-closed).

## OKR pin (unchanged)

The analysis in `research/okr_corpus` pins OKR `data/khipu.db` at upstream commit `4039ca51` (v2.1.0 lineage; 619 khipus / 54,403 cords / 110,677 knots; MIT, [khipulab/open-khipu-repository](https://github.com/khipulab/open-khipu-repository)). Corpus-v2 does not change that pin; it layers new open assets alongside it. Every corpus-v2 manifest row cites its upstream source and license basis. OKR credits stay upstream's.

## What corpus-v2 ingests (OPEN assets only)

| Asset | Source | License basis | Contents |
|---|---|---|---|
| KDB recovery record v1.0 | Zenodo DOI [10.5281/zenodo.21514490](https://doi.org/10.5281/zenodo.21514490) | Open deposit (32.1 kB: manifest, tooling, validation) | Per-file SHA-256 manifest of the recovered Harvard KDB DataTables, idempotent recovery tool, validation reports — **not** the recovered sheets themselves |
| Contreras structural pattern mining | arXiv [2607.00185](https://arxiv.org/abs/2607.00185), [2610.38580](https://arxiv.org/abs/2610.38580) + [Khipu-ML](https://github.com/mcontrerasmalpar-pixel/khipu-ml) | arXiv non-exclusive license / repo MIT (verified on fetch) | Clustering, provenance classification, cataloger-confound analysis, KFG re-analysis, open code + data |
| Khipu-Biblio Cross-Reference (KBCR) | [Melbourne Figshare](https://figshare.unimelb.edu.au/articles/dataset/Khipu-Biblio_Cross-Reference_KBCR_Resource/25661322) | per-file (verify on fetch; abort if not open) | Bibliography cross-reference tables for corpus-v2 metadata |

## What corpus-v2 does NOT ingest (rights-flagged)

See `NOT_REDISTRIBUTABLE.md`. The recovered KDB content (14 alternate assessments, AB001/KH0701, Urton khipu-type tables) is pending the OKR Advisory Board's response to [khipulab#1](https://github.com/khipulab/open-khipu-repository/issues/1). The Zenodo recovery record is ingested (open); the recovered sheets are not, until rights are settled. No SZL training set will ever contain flagged material.

## Method

`fetch_open_assets.py` is stdlib-only, idempotent, records per-file SHA-256 in `fetch_manifest.csv`, and fails closed on hash mismatch. Re-runs skip files that already match.
