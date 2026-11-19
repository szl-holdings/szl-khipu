<!-- SPDX-License-Identifier: Apache-2.0
(c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173 -->

# Published khipu readings, re-run on the pinned records

Status: **MEASURED** on the pinned Open Khipu Repository (OKR) records. Everything
here is post hoc and exploratory. It is **not decipherment**: no cord is given a
meaning that someone else has not already published, and the one test that goes
beyond published claims only counts how strongly recorded features are linked.

Three things are in this directory:

1. `santa_valley.py` re-derives the countable parts of the Santa Valley
   khipu-to-census match (Urton 2017; Medrano and Urton 2018; FitzPatrick 2024).
2. `puruchuco.py` checks one pair of sums reported for the Puruchuco accounting
   hierarchy (Urton and Brezine 2005, via the Khipu Field Guide).
3. `hidden_cord.py` hides one recorded feature of one cord at a time and measures
   how many bits the rest of the khipu gives back, against a shuffle control.

## What was and was not read

| Source | Read in this run |
| --- | --- |
| FitzPatrick 2024, Ethnohistory 71(4): 443-469, doi 10.1215/00141801-11266328, open preprint https://osf.io/sr8kw | First half and footnotes 9-12. Section 4 and footnotes 3, 5, 7 and 8 were not read. |
| Medrano and Urton 2018, Ethnohistory 65(1): 1-23, doi 10.1215/00141801-4260638 | Not read. Its counts are taken as FitzPatrick reports them. |
| Urton 2017, *Inka History in Knots* | Not read. |
| Urton and Brezine 2005, Science 309: 1065-1067, doi 10.1126/science.1113426 | Not read. |
| Khipu Field Guide, notebook "Replicating Puruchuco" (https://khipufieldguide.com/) | Not read. Tier list and the figures 1439 and 1447 come from a web-search summary. |
| Contreras 2026, arXiv:2607.00185 | Abstract-level only. It reports the recto/verso structure of the Santa khipus and leaves the tribute total as future work. |

Sources that were not read are cited so a reader can check them, not because
this run verified them.

## 1. Santa Valley khipus (UR087-UR092) and the 1670 Corongo census

Sealed report: `santa_valley_v1.json`, report sha256
`cc7bdd98929acdee13f1d0101e5a4b369a9ae6418bf943e034544acc816a116f`.

| Claim | Status | Measured |
| --- | --- | --- |
| `khipus_in_corpus` | **REPLICATED** | All six are in the corpus: KH0323-KH0328, Museo Temple Radicati. |
| `pendant_cords_804` | **REPLICATED** | 824 level-1 pendants; 804 once the 20 one-cord clusters are left out. The source's own exclusion rule was not located. |
| `six_cord_groups_133` | **REPLICATED** | 48, 9, 34, 17, 15, 10 by the colour-band rule below. |
| `identifier_recto_63_verso_70` | **PARTIAL** | Measured 63 recto, 69 verso, 1 unspecified. Two groups differ (see below). |
| `kh0326_59_leading_verso` | **REPLICATED** | The first 59 pendants of KH0326 are verso. |
| `first_cord_total_near_367` | **PARTIAL** | The 120 knotted first cords sum to 360 (98.1% of 367); 10 first cords have no knots and 3 cannot be read. |
| `table_3_split_arithmetic` | **REPLICATED** | All twenty rows of FitzPatrick's Table 3 recomputed from the published inputs. |
| `tribute_paid_by_moiety` | **NOT_TESTED** | Section 4 of the source was not read. Measured first-cord sums by side: verso 267, recto 91, unspecified 2. |

**Grouping rule.** The published work reads the pendants as groups of six cords
marked by colour. The colour-band rule here is: inside each OKR cord cluster, a
same-colour run of six or more gives leading groups of six and sets the rest
aside; shorter runs join into one mixed group of six; a lone cord between full
bands is set aside; a one-cord cluster is not a group member. It uses colour and
clustering only, never knot values or attachment direction. It was written after
seeing these khipus and the published counts. It reproduces all six per-khipu
group counts with no ambiguous case and sets aside six cords, all on KH0326
(four of them are the last four of the ten brown cords the source describes).

**Where the pinned records differ from the published counts.** Group 15 of
KH0326 opens with a recto cord in OKR; the published sequence has verso there.
Group 2 of KH0328 opens with a cord whose attachment OKR records as unspecified.
The published KH0326 sequence is this project's transcription from the preprint
and could not be re-checked in this run. This is a question for the OKR
maintainers and the authors, not a finding against either.

**First-cord total.** The published claim is that first-cord values "closely
match" the 367 pesos the census gives as the total tribute. From the pinned
records the knotted first cords sum to 360. Three cautions: the source's own
sum was not read; thirteen first cords carry no knots or cannot be read; and the
sum depends on the grouping (counting off sixes by position instead gives
749, because the groups on KH0326 fall out of step).

**The census's own arithmetic.** 132 tributaries at 2 pesos 7 reales 3 quartillos
come to 391 pesos 7 reales, not 367. That is our arithmetic (8 reales to the
peso, 4 quartillos to the real); the source's footnote on it was not read.

**Which pachacas are verso.** With the published group counts (70 verso, 63
recto), FitzPatrick's split (Namus, Cuyuchin, Guauyan as verso) has error
3 and Medrano and Urton's has 5, as published. With the counts measured
from the pinned records (69 verso, 63 recto) FitzPatrick's split is still the
single best of the twenty (error 2) and Medrano and Urton's drops to rank
3 (error 6).

**How surprising is a best-possible split?** Not very, on its own. The smallest
error the counts allow is 3, because 130 named tributaries cannot equal 133
groups. If six pachaca sizes are drawn at random (uniform compositions of 130),
61.8% of draws have some three-pachaca split that reaches that floor
(20000 draws, seed 1670). This is our illustrative control, not something
in the sources. The split arithmetic alone therefore does not carry the
argument; the case rests on the other evidence the authors give.

## 2. Puruchuco

Sealed report: `puruchuco_v1.json`, report sha256
`28f2ccfa7a866870da1c853f1d24b082038a0ac4ec4053a91cd8db2a46299518`.

| Claim | Status | Measured |
| --- | --- | --- |
| `ur063_total_1439` | **REPLICATED** | UR063 pendant total is 1439 (6 cords unreadable). |
| `ur068_cords_34_53_total_1447` | **REPLICATED** | UR068 cords 34-53 sum to 1447. |
| `hierarchy_sums_move_upward` | **NOT_TESTED** | The paper's cord-by-cord correspondences were not read. |
| `cm009` | **NOT_TESTABLE** | CM009 is not in the pinned corpus. |

Our control: no other khipu among the 618 in the corpus has a pendant total
within 8 of the UR068 span. Inside UR068 the match is not sensitive to where a
twenty-cord window starts (15 of 54 windows are within 8 of 1439), because
one cord (1236) carries most of the sum.

## 3. Hidden-cord information test

Sealed report: `hidden_cord_v1.json`, report sha256
`a265e1c6c61fbfc1241732d42df7aeb507f02c155ad2901514966ca85042d06d`.

Unit: level-1 pendant cords on a primary cord. Six recorded features: colour,
attachment (recto/verso), spin (S/Z), knot direction (S, Z or mixed over the
cord's knots), fibre, and value class (0, 1-9, 10-99, 100-999, 1000+). Spin,
fibre and knot direction come from `okr_features_v1.json.gz`, which
`build_features.py` copies out of the pinned database.

For each feature, each cord with that feature recorded is hidden in turn and
predicted from count tables fitted on the other cords of the same khipu
(khipus with fewer than 12 recorded cords are left out). The baseline is the
khipu's own frequencies. A context is then added: the two neighbouring cords,
the cord's position in its cluster, or another feature of the same cord.
"Gain" is bits saved per cord over the baseline, net of the cost of splitting
the counts. "Excess" is the gain minus the mean gain over 100 shuffles of the
hidden feature inside each khipu. "Excess inside clusters" repeats that with
values shuffled only inside their own cord cluster; "(no)" marks links that do
not beat every such shuffle.

Baselines, bits per cord:

| Feature | Khipus | Cords | Knowing only the corpus | Knowing the khipu |
| --- | --- | --- | --- | --- |
| colour | 477 | 36405 | 5.1199 | 2.6055 |
| attach | 329 | 25422 | 1.0061 | 0.2743 |
| value_class | 474 | 34203 | 2.0798 | 1.2767 |
| knot_dir | 355 | 21450 | 1.3572 | 0.5948 |
| spin | 389 | 30470 | 0.4176 | 0.0240 |
| fibre | 248 | 21113 | 0.5267 | 0.0355 |

Contexts:

| Hidden feature | Context | Gain | Excess | Excess inside clusters | Verdict |
| --- | --- | --- | --- | --- | --- |
| colour | attach | -0.1653 | 0.0364 | 0.0080 | ABOVE_SHUFFLE_NULL_NO_NET_SAVING |
| colour | fibre | -0.1707 | 0.0128 | 0.0043 | ABOVE_SHUFFLE_NULL_NO_NET_SAVING |
| colour | knot_dir | -0.1304 | 0.1388 | 0.0794 | ABOVE_SHUFFLE_NULL_NO_NET_SAVING |
| colour | neighbours | 0.7292 | 1.0831 |  | ABOVE_SHUFFLE_NULL_NET_SAVING |
| colour | position | -0.0618 | 0.4022 |  | ABOVE_SHUFFLE_NULL_NO_NET_SAVING |
| colour | spin | -0.1734 | 0.0111 | 0.0051 | ABOVE_SHUFFLE_NULL_NO_NET_SAVING |
| colour | value_class | -0.0716 | 0.2549 | 0.1505 | ABOVE_SHUFFLE_NULL_NO_NET_SAVING |
| attach | colour | 0.0195 | 0.0349 | 0.0068 | ABOVE_SHUFFLE_NULL_NET_SAVING |
| attach | fibre | -0.0004 | 0.0001 | -0.0001 (no) | NOT_ABOVE_SHUFFLE_NULL |
| attach | knot_dir | 0.0054 | 0.0113 | 0.0013 (no) | ABOVE_SHUFFLE_NULL_NET_SAVING |
| attach | neighbours | 0.1117 | 0.1216 |  | ABOVE_SHUFFLE_NULL_NET_SAVING |
| attach | position | -0.0208 | -0.0002 |  | NOT_ABOVE_SHUFFLE_NULL |
| attach | spin | 0.0001 | 0.0007 | 0.0005 | ABOVE_SHUFFLE_NULL_NET_SAVING |
| attach | value_class | 0.0046 | 0.0135 | 0.0005 (no) | ABOVE_SHUFFLE_NULL_NET_SAVING |
| value_class | attach | -0.0048 | 0.0278 | 0.0015 (no) | ABOVE_SHUFFLE_NULL_NO_NET_SAVING |
| value_class | colour | 0.0855 | 0.2008 | 0.0989 | ABOVE_SHUFFLE_NULL_NET_SAVING |
| value_class | fibre | -0.0159 | 0.0088 | 0.0019 | ABOVE_SHUFFLE_NULL_NO_NET_SAVING |
| value_class | neighbours | 0.1344 | 0.2788 |  | ABOVE_SHUFFLE_NULL_NET_SAVING |
| value_class | position | 0.0016 | 0.1526 |  | ABOVE_SHUFFLE_NULL_NET_SAVING |
| value_class | spin | -0.0080 | 0.0182 | 0.0037 | ABOVE_SHUFFLE_NULL_NO_NET_SAVING |
| knot_dir | attach | -0.0118 | 0.0065 | 0.0013 (no) | ABOVE_SHUFFLE_NULL_NO_NET_SAVING |
| knot_dir | colour | -0.0052 | 0.0477 | 0.0293 | ABOVE_SHUFFLE_NULL_NO_NET_SAVING |
| knot_dir | fibre | -0.0140 | 0.0003 | 0.0004 (no) | NOT_ABOVE_SHUFFLE_NULL |
| knot_dir | neighbours | 0.0066 | 0.0715 |  | ABOVE_SHUFFLE_NULL_NET_SAVING |
| knot_dir | position | -0.0383 | 0.0309 |  | ABOVE_SHUFFLE_NULL_NO_NET_SAVING |
| knot_dir | spin | -0.0151 | -0.0004 | -0.0005 (no) | NOT_ABOVE_SHUFFLE_NULL |
| spin | attach | 0.0018 | 0.0013 | 0.0009 | ABOVE_SHUFFLE_NULL_NET_SAVING |
| spin | colour | 0.0061 | 0.0067 | 0.0036 | ABOVE_SHUFFLE_NULL_NET_SAVING |
| spin | fibre | 0.0027 | 0.0023 | 0.0006 | ABOVE_SHUFFLE_NULL_NET_SAVING |
| spin | knot_dir | 0.0001 | 0.0002 | -0.0003 (no) | NOT_ABOVE_SHUFFLE_NULL |
| spin | neighbours | 0.0051 | 0.0056 |  | ABOVE_SHUFFLE_NULL_NET_SAVING |
| spin | position | -0.0024 | -0.0009 |  | NOT_ABOVE_SHUFFLE_NULL |
| spin | value_class | 0.0008 | 0.0011 | 0.0006 (no) | ABOVE_SHUFFLE_NULL_NET_SAVING |
| fibre | attach | 0.0009 | 0.0005 | 0.0000 (no) | NOT_ABOVE_SHUFFLE_NULL |
| fibre | colour | 0.0173 | 0.0189 | 0.0066 | ABOVE_SHUFFLE_NULL_NET_SAVING |
| fibre | knot_dir | 0.0033 | 0.0031 | 0.0021 | ABOVE_SHUFFLE_NULL_NET_SAVING |
| fibre | neighbours | 0.0210 | 0.0215 |  | ABOVE_SHUFFLE_NULL_NET_SAVING |
| fibre | position | -0.0017 | 0.0006 |  | NOT_ABOVE_SHUFFLE_NULL |
| fibre | spin | 0.0041 | 0.0038 | 0.0011 | ABOVE_SHUFFLE_NULL_NET_SAVING |
| fibre | value_class | 0.0047 | 0.0049 | 0.0036 | ABOVE_SHUFFLE_NULL_NET_SAVING |

What the numbers support, and nothing more:

- **Most of what can be predicted about a cord is which khipu it is on.** Spin
  and fibre are almost entirely khipu-level as recorded: under 0.04 bits per
  cord remain once the khipu is known. A cord-by-cord code in spin or fibre
  has very little recorded variation to live in.
- **Colour is ordered along the cord.** Neighbours save 0.73 bits per cord on
  colour. Colour banding has been described since the Aschers; this puts a
  number and a control on it.
- **Colour and value magnitude are linked inside khipus**, and about half of
  that link remains when values are shuffled only inside their own cluster.
- **Knot direction is the least explained feature.** About 0.59 bits per cord
  remain after the khipu is known, and neighbours, position, colour and
  attachment each recover little of it (0.07 bits at most). Either it is habit
  and noise, or it follows something OKR does not record.
- **Attachment direction follows its neighbours** and, weakly, colour. Its links
  to value and knot direction vanish inside clusters, so they follow sections.

A link can come from how a khipu was made, how it survived, or how it was
catalogued. This test cannot tell those apart, and "unrecorded" is a category of
its own in the context features. No neural model was evaluated. The
khipu-scholar adapters answer questions about the same OKR records they were
trained on; they are not evidence about meaning and were not used here.

## Other published readings, not tested here

| Reading | Khipus | In the pinned corpus | Status |
| --- | --- | --- | --- |
| White pendants as boundaries of sum-cord clusters (Medrano and Khosla 2024, Latin American Antiquity) | corpus-wide | yes | NOT_TESTED: article not read |
| Calendar reading of the Chachapoyas khipu UR006 (Urton 2001, Latin American Antiquity 12(2)) | UR006 = KH0242 | yes | NOT_TESTED: article not read |
| First names in cord colour on the Santa khipus (Medrano and Urton 2018) | UR087-UR092 | yes | NOT_TESTABLE here: needs the 1670 name list (Zevallos Quinones 1991), which this project does not hold |
| Collata narrative khipus (Hyland 2017, Current Anthropology 58(3)) | Collata | no | NOT_TESTABLE: not in OKR |

The last three citations are from the literature and were not opened in this run.

## What would move this forward

1. Read FitzPatrick's section 4 and footnotes and compare its tribute figures
   with the measured sums by side.
2. Ask the OKR maintainers and the authors about KH0326 group 15 and KH0328
   group 2.
3. Obtain the 1670 name list. A name-by-group test is the only one here that
   could confirm or refute a reading at the level of individual groups.
4. Fit a masked-cord sequence model under this same harness (same hidden-cord
   scoring, same shuffles) and see whether it beats these count tables. That
   needs a GPU and is ROADMAP.

## Files

| File | What it is |
| --- | --- |
| `santa_valley.py`, `santa_valley_v1.json` | Santa Valley replication and its sealed report. |
| `puruchuco.py`, `puruchuco_v1.json` | Puruchuco reported-sum check and its sealed report. |
| `build_features.py`, `okr_features_v1.json.gz` | Spin, fibre and knot direction per cord, copied from the pinned database (46,822 bytes, sha256 `1cd7c4cd822e0783969ca69a2dfae484b8c81b48ca57989fb535d53367e1d3c9`). Data are MIT (OKR); see `../okr_corpus/LICENSE-OKR.txt`. |
| `hidden_cord.py`, `hidden_cord_v1.json` | Hidden-cord information test and its sealed report. |
| `../../tests/test_okr_santa_valley.py`, `test_okr_puruchuco.py`, `test_okr_features.py`, `test_okr_hidden_cord.py`, `test_okr_readings_docs.py` | Unit tests; the last one fails if this page and the sealed reports disagree. |

Digests here are integrity checks, not signatures.

## Reproduce

```
python3 -I research/okr_readings/santa_valley.py --check
python3 -I research/okr_readings/puruchuco.py --check
python3 -I research/okr_readings/hidden_cord.py --check        # about a minute on one core
# with the pinned OKR database (see ../okr_corpus/README.md for the download and its digest):
python3 -I research/okr_readings/build_features.py --db PATH/khipu.db --check
python3 -m unittest discover -s tests -p "test_okr_*.py" -v
```
