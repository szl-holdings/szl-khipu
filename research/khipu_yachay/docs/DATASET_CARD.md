# SZL Khipu Yachay Research v0 — dataset card

**Status:** local, research-only; no Hugging Face dataset publication verified. **DO NOT represent this as an archaeological training corpus.**

## Purpose and composition

This project contains three strictly separated collections:

1. **540 synthetic, first-party training questions** and **80 held-out-template synthetic evaluation questions**, in JSONL. They label *research intent* across five categories (`NUMERACY`, `RECORDS`, `RESEARCH_LIMITS`, `DATA_RIGHTS`, `METHODS`), not the semantic content of actual historical khipus. No external paper, image, transcript, Indigenous-language text, or museum object data were included in model training.
2. **702 published KH identifier pointers** (`KH0001`–`KH0702`) drawn from Open Khipu Repository v2.1.0's `data/okr-kh-numbers.csv`, pinned at Git blob `57a44cf0befc8baacc5d6bbcf11e09decf41cd14`. Each row is *identifier-only*; country, museum, knot values, narratives and unverified inferred meanings are deliberately `null` or absent. This is an index for research, not 702 decoded khipus. Cite DOI **10.5281/zenodo.18025748**. The source repository's LICENSE is MIT; attribution and traditional knowledge responsibilities remain separate.
3. **14 attributed source catalog entries** recording DOI/URL, authorship, review state, rights and whether bulk copying or training is admitted. Only small original descriptions and public bibliographic metadata are included. Entries with uncertain terms remain `METADATA_ONLY` / `LINK_ONLY` and `bulk_training_admitted=false`.

Historical source data and this project's synthetic examples **must never be silently mixed** into a common train/validation split. The full ~79.8 MB OKR Zenodo archive, KFG workbook collection, museum photographs and full articles are **not copied** into this release.

## Data provenance, ownership and rights

- OKR: `https://github.com/khipulab/open-khipu-repository/tree/v2.1.0` (`MIT`, copyright Open Khipu Repository Team; archived v2.1.0 DOI above). Attribution to contributing researchers and the full OKR license are required before redistributing substantial source bytes.
- Khipu Field Guide article companion: `https://github.com/khipufieldguide/data-science-khipu-article/tree/v2.1.0` (MIT software/data repository, *not automatically a license to reuse all museum imagery*). DOI **10.5281/zenodo.10472429**.
- Other listed scholarly articles: metadata references only, not article text.
- The use of Quechua *yachay* (“knowledge”) is linguistic inspiration and requires community consultation before asserting cultural endorsement. **No Quechua language-model competency is measured or claimed.**
- Indigenous data sovereignty: even openly distributed materials may carry community interests not exhausted by a repository license. Historical discovery must involve Andean researchers, institutions and communities and recognize contributors. See the OKR ethics statement.

## Split and leakage disclosure

A fixed generator with no downloaded source text produces 540 training prompts (9 template families per label × 12 development subjects) and 80 evaluation prompts (2 unseen template families per label × 8 distinct evaluation subjects). This *reduces literal template overlap*; it is not a sealed or independently authored holdout. Both splits were authored and tuned by the same developer, including a revised curriculum after the initial 37.5% evaluation. The reported final 95.0% is therefore **development-influenced** and must not be presented as a prospective untouched test score. An independent evaluation is required.

## Prohibited unsupported claims

No decipherment, cultural translation, new Inka formula, archaeological correctness, historical provenance classification, real-world Q&A accuracy, or rights clearance beyond recorded evidence is established by this dataset. Avoid demographic/geographic identity inference from museum holdings. Missing cord values never become zero; a sum match never proves source authenticity.

## Next admitted data wave

Revalidate licenses and original data rights; import exact versions of eligible OKR/KFG numeric fields as a **separate** dataset with explicit per-row missingness, object and recorder provenance, site/group-based partitioning, measurement uncertainty, independent evaluation, negative controls, consultation and withdrawal rights. Do not train on ambiguous archival values before that review. New metadata discoveries through `scripts/discover_metadata.py` are link/index-only until separately reviewed; no unbounded scraping or bypass of access restrictions is authorized.
