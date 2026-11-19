<!-- SPDX-License-Identifier: Apache-2.0
(c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173 -->

# OKR structure SFT v3 / eval v2 (canonical reading)

`build_structure_sft.py` rebuilds the SZL OKR-structure training set and its held-out
evaluation set from the digest-pinned public corpus
`research/okr_corpus/okr_corpus_v1.json.gz`. It uses only the standard library and
the `szl_khipu` package. The JSONL files are not committed; the sealed manifest
`structure_v3_manifest.json` records their sha256, and `--check` rebuilds them and
compares.

```bash
python -I research/okr_structure_sft/build_structure_sft.py --check
python -I research/okr_structure_sft/build_structure_sft.py --out /tmp/structure_v3
```

## Why it was rebuilt

The previous sets (`khipu-structure-sft-v2`, `khipu-structure-eval-v1` on the Hub,
private) had two labelling defects:

- Long knots counted `knot_value_type × NUM_TURNS`, which squares a units long knot
  (see `research/okr_value_rule`). `S100, S100, S10, S10, L2` was labelled 224; its
  canonical value is 222.
- Knotless pendants with a broken or cut end were written as 0. Their knots may be
  lost, so their value is unknown.

## Rules (all values from `szl_khipu.okr_khipu.cord_value`)

- Cord value: sum of each knot's recorded decimal contribution; UNKNOWN, never 0, when a
  knot value is missing or a knotless cord is broken or cut.
- Split: a khipu is held out when `int(sha256(str(KHIPU_ID)), 16) % 10 == 0`, the
  previous sets' rule. 61 of the 611 khipus with pendant cords are held out.
- Pendant cords are CORD_LEVEL 1 cords in `(ordinal, id)` order; "cord n" is the n-th.
- `okr-cipher-qa`: the first pendants with a known value and at least one knot, up to 3
  per training khipu and 5 per held-out khipu. Knots are written as type plus recorded
  value (`S100`, `L2`, `E1`).
- `okr-pendant-sum-qa`: all pendant values in order and their sum, only when every value
  is known and there are at most 60 pendants.
- `okr-structure-qa`: a summary; knot and colour counts are over pendant cords, and
  unknown pendant values are reported as unknown.
- `okr-cord-sequence` (training only): every pendant as
  `c<n>[len=…,col=…,val=…,k=…]`, with `?` for unknown values.

## Counts (MEASURED, sealed in the manifest)

| Set | Rows | Khipus | cipher | pendant-sum | summary | sequence |
|---|---:|---:|---:|---:|---:|---:|
| `khipu_structure_sft_v3.jsonl` | 2,857 | 550 | 1,566 | 191 | 550 | 550 |
| `khipu_structure_eval_v2.jsonl` | 366 | 61 | 282 | 23 | 61 | 0 |

The held-out cipher rows cover the same 61 khipus as before. Cords with an unknown
value are skipped, so some rows move on to the next cord. The pendant-sum tier is much
smaller than before because most khipus have at least one pendant with an unknown value.

## Limits

- The previous builder is not in version control; prompts and summaries were rewritten
  from its published rows. The primary cord structure code is dropped because the
  pinned corpus does not carry it.
- Exploratory training data. Not decipherment. Digests are integrity checks, not
  signatures.
