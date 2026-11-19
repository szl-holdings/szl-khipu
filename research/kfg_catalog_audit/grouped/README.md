# Khipu grouped split sensitivity — archived baseline replay

## Scope and pinned provenance

Source: `szl-holdings/szl-khipu` commit `9d62dec25f6ff6fd69a73bc74a7b714f8dcb2187`.
Builder: `research/okr_structure_sft/build_structure_sft.py` (actual source imported, not reimplemented).
Corpus: `research/okr_corpus/okr_corpus_v1.json.gz`, upstream OKR commit `4039ca51f4de661d80d0160596309c983a62a9c7`.
The replay verifies clean tracked source and exact revision, uses the corpus loader's pinned digest, and first reproduces the committed baseline manifest exactly. It never rewrites the source, archived corpus, JSONL training artifacts or manifest. It generates only this separate sensitivity evidence. No training or model inference occurs.

Alias-pair documentary provenance: [Khipu Field Guide sketchbook footnote 8](https://khipufieldguide.com/sketchbook/index.html) identifies KH0473 as a duplicate of KH0121; OKR/KFG document KH0140/KH0483. This replay does not independently verify the physical objects. Historical distinct accession labels are not erased. Pair links for KH0192/KH0470 and KH0303/KH0304 are treated only as a similarity sensitivity, **not duplicate assertions**.

## Method

Union the specified pair edges into components. The representative is the component's minimum **numeric internal corpus ID**, then use the original SHA-256 modulo-10 split rule on that representative. Singleton assignment is unchanged. This is a declared deterministic sensitivity policy, not a uniquely correct split. It does not delete/deduplicate records or optimize benchmark results.

Rebuild rows through the original builder, temporarily substituting only its split predicate in memory and restoring it afterwards. Its training-only sequence row and 3-versus-5 cipher limits remain in force; therefore row movement is not a simple shuffle. Content identities omit only the `split` attribute.

## Results

| Scenario | Train khipus | Train rows | Eval khipus | Eval rows |
|---|---:|---:|---:|---:|
| Pinned original | 550 | 2,857 | 61 | 366 |
| Two documented alias groups | 550 | 2,857 | 61 | 366 |
| Alias groups plus two similarity groups | 552 | 2,867 | 59 | 354 |

Both alias groups already lie entirely in training; regrouping changes zero assignments and zero bytes of rebuilt JSONL. The two similarity pairs straddle the original split. Grouping them moves KH0303 and KH0470 from evaluation to training. Each had six eval rows and generates five train rows. Eight existing content rows transfer; four extra eval cipher rows disappear; two train-only sequence rows are generated. No train-to-eval movement occurs.

Identity-level intersection remains zero before and after. That **does not** rule out object aliases or structurally similar examples across the partitions. Named cross-split alias edges remain 0/2; named cross-split similarity edges change from 2/2 to 0/2 only in the second sensitivity.

## Limits

This covers four named pairs only. It neither proves complete decontamination nor declares the new split held-out: already trained models retain their exposure. It does not establish model quality, mathematical novelty, decipherment, or improved accuracy. No public release or new dataset version is made. Original records remain intact.

## Reproduce

```
python -B -m unittest -v test_grouped_split_sensitivity.py
python -B grouped_split_sensitivity.py source
```

Seven tests cover singleton preservation, component ordering/transitivity, missing/duplicate identities, content identity and the real pinned-corpus replay. `evidence.json` includes exact source/corpus/archive/output digests, per-pair split checks, moved identifiers and tier counts.
