<!-- SPDX-License-Identifier: Apache-2.0
(c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173 -->

# OKR knot-value rule audit

`audit_value_rule.py` checks which arithmetic reading of Open Khipu Repository
knots a cord-value label follows. It needs only the standard library and the
`szl_khipu` package.

| Rule | Cord value |
|---|---|
| `canonical` | Sum of `knot_value_type` over the cord's knots. OKR stores each knot's decimal contribution there: a three-turn long knot in the tens place is stored as value 30 with `NUM_TURNS` 3. `research/okr_corpus` uses this rule. |
| `turns_multiplied` | Long-type knots (L, LL, BL, SP) contribute `knot_value_type × NUM_TURNS`. For a units long knot the stored value already equals its turns, so this squares it: `S10, L8` reads 74 instead of 18. |

## Result on the pinned public corpus (MEASURED)

Input: `research/okr_corpus/okr_corpus_v1.json.gz`, sha256
`6ef204b641826b37c320509952ed4181e93865af20f1cdfefd7516a49cf8ad0d`, 619 khipus.
Sealed in `value_rule_audit_v1.json`; replay with `--check`.

Under `turns_multiplied`, 21,676 knots, 19,145 cords and 476 of the 619 khipus
take a different value. The exact sum relations found by
`szl_khipu.okr_khipu.find_relations` change as follows:

| Relation | `canonical` | `turns_multiplied` |
|---|---:|---:|
| R1 subsidiary sum | 59 | 12 |
| R2 top-cord sum | 54 | 3 |
| R3 group-sum cord | 714 | 564 |
| R4 in-group sum cord | 106 | 87 |

The `canonical` counts equal `statistics.observed` in the committed
`research/okr_corpus/okr_relations_v1.json`; a test checks this.

Reading (exploratory): the top-cord and subsidiary sums, the relations that let
a khipu's own arithmetic be checked, almost all disappear under
`turns_multiplied`. That supports reading `knot_value_type` as each knot's
contribution. R3 and R4 include many small-value coincidences (see the null
model in `research/okr_corpus`), so they are weak evidence either way.

## Why this exists

The SZL OKR-structure training and evaluation sets on the Hub
(`SZLHOLDINGS/khipu-structure-sft-v2`, `SZLHOLDINGS/khipu-structure-eval-v1`,
both private) label their "cord total value" questions with the
`turns_multiplied` rule. Those labels cannot be compared with OKR readings or
with `research/okr_corpus`, and an exact-match score against them measures
agreement with that rule, not with the canonical reading. Label mode shows which
rule each label follows; prediction mode rescores model outputs against both.
Results from the private files are not committed here.

```bash
python -I research/okr_value_rule/audit_value_rule.py --check
python -I research/okr_value_rule/audit_value_rule.py --labels eval.jsonl --preds preds.jsonl
```

`--preds` rows (`khipu`, `gold`, `pred`) must align one-to-one, in order, with
the arithmetic rows of `--labels`; a misaligned file is refused (exit 2).

## Limits

- `turns_multiplied` approximates a labelling rule; it does not model how any
  particular builder treated zero or missing values. Rows with an unknown knot
  value are counted as `unknown_value` and never scored.
- LL (double long) knots are treated like other long knots; OKR's notes say the
  Aschers give LL a value of 3.
- Exploratory and not preregistered. Not decipherment. Digests are integrity
  checks, not signatures.
