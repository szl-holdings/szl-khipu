<!-- SPDX-License-Identifier: Apache-2.0
(c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173 -->

# Published khipu readings, re-run on the pinned records

Status: **MEASURED** on the pinned Open Khipu Repository (OKR) records. Everything
here is post hoc and exploratory. It is **not decipherment**: no cord is given a
meaning that someone else has not already published, and the tests that go
beyond published claims only measure how strong the published evidence is.

Six things are in this directory:

1. `santa_valley.py` re-derives the countable parts of the Santa Valley
   khipu-to-census match (Urton 2017; Medrano and Urton 2018; FitzPatrick 2024).
2. `puruchuco.py` checks one pair of sums reported for the Puruchuco accounting
   hierarchy (Urton and Brezine 2005, via the Khipu Field Guide).
3. `hidden_cord.py` hides one recorded feature of one cord at a time and measures
   how many bits the rest of the khipu gives back, against a shuffle control.
4. `syllabary_stress.py` stress-tests the dictionary-hit evidence for a published
   proposal that some cords spell Quechua words (Sivan 2026).
5. `knot_direction.py` tests whether a knot's direction follows its type.
6. `matching_khipus.py` searches all pinned khipus for pairs that carry the same
   run of numbers, and asks which other recorded features travel with them.

## What was and was not read

| Source | Read in this run |
| --- | --- |
| FitzPatrick 2024, Ethnohistory 71(4): 443-469, doi 10.1215/00141801-11266328, open preprint https://osf.io/sr8kw | About three fifths: sections 1 to 3.1, the tribute passage of 3.4, the start of 3.5 and footnotes 1-21. The rest of sections 3 and 4 were not read. |
| Medrano and Urton 2018, Ethnohistory 65(1): 1-23, doi 10.1215/00141801-4260638 | Not read. Its counts are taken as FitzPatrick reports them. |
| Urton 2017, *Inka History in Knots* | Not read. |
| Urton and Brezine 2005, Science 309: 1065-1067, doi 10.1126/science.1113426 | Not read. |
| Khipu Field Guide, Khosla and Medrano (https://khipufieldguide.com/) | About page only. The Puruchuco tier list and the figures 1439 and 1447 come from a web-search summary of its notebook. |
| Sivan 2026, ALBA Project (https://alba-project.org/khipu-reader/, doi 10.5281/zenodo.19184002, code https://github.com/Alba-Research/KhipuReader, MIT) | Project page, README and four source files at commit `7c2722b91fcad514653c96f40fa2dae125de92b8`. The preprint itself was not read. |
| Da Fieno Delucchi 2026, K-CAT (https://github.com/adafieno/khipu-computational-toolkit, MIT) | Project page only. |
| Contreras 2026, arXiv:2607.00185 | Abstract only. |

Sources that were not read are cited so a reader can check them, not because
this run verified them.

## 1. Santa Valley khipus (UR087-UR092) and the 1670 Corongo census

Sealed report: `santa_valley_v1.json`, report sha256
`0c8b38acad3936b27d9622626255ddb40395eb002b01bde8ac77efbba686d687`.

| Claim | Status | Measured |
| --- | --- | --- |
| `khipus_in_corpus` | **REPLICATED** | All six are in the corpus: KH0323-KH0328, Museo Temple Radicati. |
| `pendant_cords_804` | **REPLICATED** | 824 level-1 pendants; 804 once the 20 one-cord clusters are left out. The source's own exclusion rule was not located. |
| `six_cord_groups_133` | **REPLICATED** | 48, 9, 34, 17, 15, 10 by the colour-band rule below. |
| `identifier_recto_63_verso_70` | **PARTIAL** | Measured 63 recto, 69 verso, 1 unspecified. Two groups differ (see below). |
| `kh0326_59_leading_verso` | **REPLICATED** | The first 59 pendants of KH0326 are verso. |
| `first_cord_total_near_367` | **PARTIAL** | The 120 knotted first cords sum to 360 (98.1% of 367); 10 first cords have no knots and 3 cannot be read. |
| `table_3_split_arithmetic` | **REPLICATED** | All twenty rows of FitzPatrick's Table 3 recomputed from the published inputs. |
| `six_cords_outside_groups` | **REPLICATED** | Six cords fall outside the groups, all on KH0326. |
| `tribute_paid_by_moiety` | **PARTIAL** | Published: verso likely 381 or 382 pesos, recto 86. Measured with the published side of each group: recto 87, verso 273. |

**Grouping rule.** The published work reads the pendants as groups of six cords
marked by colour. The colour-band rule here is: inside each OKR cord cluster, a
same-colour run of six or more gives leading groups of six and sets the rest
aside; shorter runs join into one mixed group of six; a lone cord between full
bands is set aside; a one-cord cluster is not a group member. It uses colour and
clustering only, never knot values or attachment direction. It was written after
seeing these khipus and the published counts. It reproduces all six per-khipu
group counts with no ambiguous case and sets aside six cords, all on KH0326,
which is the number the source gives.

**Where the pinned records differ from the published counts.** Group 15 of
KH0326 opens with a recto cord in OKR; the published sequence has verso there
(checked against the preprint text). Group 2 of KH0328 opens with a cord whose
attachment OKR records as unspecified. This is a question for the OKR
maintainers and the authors, not a finding against either.

**First-cord total.** The published claim is that first-cord values "closely
match" the 367 pesos the census gives as the total tribute. From the pinned
records the knotted first cords sum to 360. Three cautions: the source's own
sum was not found; thirteen first cords carry no knots or cannot be read; and the
sum depends on the grouping (counting off sixes by position instead gives
749, because the groups on KH0326 fall out of step).

**Tribute by moiety.** The source gives recto 86 pesos and verso "likely 381 or
382" (an estimate that allows for broken cords, after Urton 2017). Using the
published side of every group, the pinned records give recto 87 and verso 273.
Recto agrees. Verso does not, and all thirteen first cords without a readable
value are verso. The two published figures sum to 467 or 468, not 367; the text
read here does not say how those fit together.

**The amount owed.** The source puts 132 tributaries at 2 pesos 7 reales 3
quartillos at about 363 pesos. With 8 reales to the peso and 4 quartillos to the
real the same rate comes to 391 pesos 7 reales. The source's conversion was not
found in the text read here.

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
`bec9e899caed4f7940927ce0528733f08a4f4196dc6b7c74b0d3ee46a61f102c`.

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
| colour | knot_dir | -0.1304 | 0.1387 | 0.0794 | ABOVE_SHUFFLE_NULL_NO_NET_SAVING |
| colour | neighbours | 0.7293 | 1.0832 |  | ABOVE_SHUFFLE_NULL_NET_SAVING |
| colour | position | -0.0618 | 0.4021 |  | ABOVE_SHUFFLE_NULL_NO_NET_SAVING |
| colour | spin | -0.1734 | 0.0111 | 0.0051 | ABOVE_SHUFFLE_NULL_NO_NET_SAVING |
| colour | value_class | -0.0716 | 0.2549 | 0.1505 | ABOVE_SHUFFLE_NULL_NO_NET_SAVING |
| attach | colour | 0.0195 | 0.0349 | 0.0068 | ABOVE_SHUFFLE_NULL_NET_SAVING |
| attach | fibre | -0.0004 | 0.0001 | -0.0001 (no) | NOT_ABOVE_SHUFFLE_NULL |
| attach | knot_dir | 0.0054 | 0.0113 | 0.0013 (no) | ABOVE_SHUFFLE_NULL_NET_SAVING |
| attach | neighbours | 0.1117 | 0.1216 |  | ABOVE_SHUFFLE_NULL_NET_SAVING |
| attach | position | -0.0208 | -0.0002 |  | NOT_ABOVE_SHUFFLE_NULL |
| attach | spin | 0.0001 | 0.0007 | 0.0005 | ABOVE_SHUFFLE_NULL_NET_SAVING |
| attach | value_class | 0.0046 | 0.0135 | 0.0005 (no) | ABOVE_SHUFFLE_NULL_NET_SAVING |
| value_class | attach | -0.0048 | 0.0278 | 0.0016 (no) | ABOVE_SHUFFLE_NULL_NO_NET_SAVING |
| value_class | colour | 0.0855 | 0.2007 | 0.0993 | ABOVE_SHUFFLE_NULL_NET_SAVING |
| value_class | fibre | -0.0159 | 0.0088 | 0.0020 | ABOVE_SHUFFLE_NULL_NO_NET_SAVING |
| value_class | neighbours | 0.1348 | 0.2791 |  | ABOVE_SHUFFLE_NULL_NET_SAVING |
| value_class | position | 0.0017 | 0.1528 |  | ABOVE_SHUFFLE_NULL_NET_SAVING |
| value_class | spin | -0.0080 | 0.0183 | 0.0038 | ABOVE_SHUFFLE_NULL_NO_NET_SAVING |
| knot_dir | attach | -0.0118 | 0.0065 | 0.0013 (no) | ABOVE_SHUFFLE_NULL_NO_NET_SAVING |
| knot_dir | colour | -0.0052 | 0.0477 | 0.0293 | ABOVE_SHUFFLE_NULL_NO_NET_SAVING |
| knot_dir | fibre | -0.0140 | 0.0003 | 0.0004 (no) | NOT_ABOVE_SHUFFLE_NULL |
| knot_dir | neighbours | 0.0066 | 0.0714 |  | ABOVE_SHUFFLE_NULL_NET_SAVING |
| knot_dir | position | -0.0382 | 0.0310 |  | ABOVE_SHUFFLE_NULL_NO_NET_SAVING |
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
- **Knot direction is the least explained cord feature here.** About 0.59 bits
  per cord remain after the khipu is known, and neighbours, position, colour and
  attachment each recover little of it (0.07 bits at most). An earlier version
  of this page guessed that it depends on something the records leave out.
  That was wrong: section 5 shows it largely follows knot type, which OKR
  does record.
- **Attachment direction follows its neighbours** and, weakly, colour. Its links
  to value and knot direction vanish inside clusters, so they follow sections.

A link can come from how a khipu was made, how it survived, or how it was
catalogued. This test cannot tell those apart, and "unrecorded" is a category of
its own in the context features. No neural model was evaluated. The
khipu-scholar adapters answer questions about the same OKR records they were
trained on; they are not evidence about meaning and were not used here.

Two independent projects report results in the same direction on other data or
by other methods; neither was re-run here. K-CAT (Da Fieno Delucchi 2026), on
the Khipu Field Guide database, reports that primary colour predicts a cord's
order of magnitude. Contreras (2026), on OKR, reports twist direction as the
main discriminator of imperial-style khipus and one cluster dominated by
nineteenth-century museum collections, which fits spin being a khipu-level
feature and the cataloguing caution above.

## 4. Stress test of a published syllabary proposal

Sealed report: `syllabary_stress_v1.json`, report sha256
`c8728e9ca086c6dbb26edc7eb6860b8f7cf2c4cefa99b97ff46f5ddf84e9522e`.

Sivan (2026, ALBA Project) proposes that cords with two or more long or
figure-eight knots spell Quechua words, one syllable per knot. It is the most
specific public claim that khipu cords can be read as words, it is published
with its mapping, scoring rule, dictionaries and code under open licences, and
it asks for independent checks. The proposal, mapping and scoring rule are
Sivan's. `syllabary_stress.py` re-implements the scoring described in that
project's control scripts and applies it to the pinned corpus. None of that
project's code is run or copied, and its dictionaries are read from a
digest-checked copy and not redistributed.

| Claim | Status | Measured |
| --- | --- | --- |
| `string_cords_1992_of_37206` | **PARTIAL** | 2728 of 37082 knotted cords (7.4%) have two or more long or figure-eight knots; published 1,992 of 37,206 (5.4%). |
| `mapping_beats_random_mappings` | **REPLICATED** | None of 2000 random mappings reached the proposal's 1696 hits (best 1548). |

Hits out of 2256 knot sequences. "Published lookup" is the proposal's rule
(suffixed forms and prefixes of four or more letters also count); "exact"
counts only whole dictionary entries.

| Dictionary | Rule | Two-knot readings accepted | Proposal's hits | Random mappings, mean | Knots scrambled within cord, mean | Knots dealt at random within khipu, mean | Best refit, real cords | Best refits, scrambled cords |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kaikki_2074 | exact | 63.9% | 1168 | 632 | 1197 | 1213 | 1480 | 1414-1468 |
| kaikki_2074 | published_lookup | 82.2% | 1696 | 873 | 1697 | 1701 | 1899 | 1875-1895 |
| kaikki_aulex_14991 | exact | 74.0% | 1424 | 731 | 1416 | 1394 | 1605 | 1517-1577 |
| kaikki_aulex_14991 | published_lookup | 91.7% | 1896 | 1053 | 1891 | 1876 | 1977 | 1961-1982 |

What the numbers support:

- **The published random-mapping result reproduces.** The proposed syllables
  beat every one of 2000 mappings drawn at random from a 42-syllable
  inventory.
- **The scoring rule accepts most readings before any cord is looked at.** Of
  all possible two-knot readings over the proposed syllables, 82% count as
  hits under the published lookup with the smaller dictionary and 92% with
  the larger. Two thirds of the sequences are two knots long.
- **Scrambled cords score the same as real ones.** With the published lookup
  and the smaller dictionary the proposal scores 1696 on the real cords,
  1697 on average when the knots of each cord are put in random order, and
  1701 when each khipu's knots are dealt back to its cords at random. In no
  setting does knot order within a cord make a detectable difference. With
  the larger dictionary, real cords score 1 to 2% above randomly dealt ones
  (p = 0.03, not corrected for the eight comparisons).
- **A mapping fitted to scrambled cords out-scores the proposal.** In every
  setting all 20 refits on scrambled cords reach more hits than the proposal
  reaches on the real cords.
- **Refitting on real cords is only slightly better than on scrambled ones**:
  1899 against 1875-1895 with the published lookup and the smaller
  dictionary, and no better with the larger one.
- **The smaller dictionary was extended from the cords.** The proposal's own
  build script adds forms "observed in the OKR STRING cord corpus" to the
  Wiktionary-derived list (14 net new), which favours the mapping in every row.

So dictionary hits, as scored, do not separate real cords from scrambled
ones, and they cannot by themselves show that these cords spell words.
It does not show that the proposal is wrong. Not tested here: the thematic coherence
of readings by document type, the astronomical dating of UR006, the proposed
calendar in opening cords, generalisation to the Khipu Field Guide database,
and the UR112 ranking against 154,440 alternative mappings. A hit means a
string is in a word list; it does not mean the cord says that word.

## 5. Knot direction follows knot type

`knot_direction.py` reads every knot with a recorded S or Z direction from
`okr_knots_v1.json.gz`, a per-knot file copied from the pinned database by
`build_features.py --knots`, and uses the same leave-one-out count models and
shuffle control as section 3. It covers 407 khipus with at least
20 directed knots, 96,856 knots in all.

- Knowing the khipu cuts the uncertainty about a knot's direction from
  0.9161 to 0.3187 bits per knot.
- Knowing the knot's type (single, long, figure-eight) as well saves another
  0.1892 bits per knot, 59% of what was left. Shuffling
  directions among a khipu's knots never comes close (best shuffle -0.0046).
- The khipu's commonest direction is right for 91.1% of knots. The
  commonest direction of the knot's own type in its khipu is right for
  96.5%; adding the turn count of long knots gives 96.6%.
  270 khipus use both directions.

So knot direction largely follows knot type, khipu by khipu: each type has a
habitual direction, and about 3.5% of knots go against it. Whether those
exceptions carry information, or are slips in tying or recording, is open.
Report digest `51458ff334e4081aecf06b6cd1feb96c3c62b10c22fbf3435836151d02ac76fd`.

## 6. Khipus that carry the same numbers

Urton (2005) and Urton and Brezine (2005) described "matching khipus" at
Puruchuco: pairs whose number sequences are identical or nearly so, read as
duplicate accounts. The Khipu Field Guide (Khosla) records twelve duplicate
pairs that Manuel Medrano found by hand; the Guide's own algorithmic search
did not find them, and it removed the duplicates from its database. All twelve
are single merged records in the pinned OKR data, but OKR still carries both
entries of some other pairs.

`matching_khipus.py` searches all the pinned records against each other. It reads the level-1 pendants of each of the
619 khipus in order, weights each value by its rarity
(-log2 of its share of all pendant values), and seeds candidate pairs by a
shared run of three values worth at least 20 bits (read forwards
or backwards) or by sharing rare values. It aligns each candidate with a
Smith-Waterman local alignment (equal values earn their rarity, values one
apart earn half, an unreadable cord earns nothing, a different value costs
4 and a skipped cord 3) and keeps a pair only if it scores at least
40 bits with 8 equal nonzero values and beats every one of
100 shuffles of one khipu's cord order. Of 11,572 seeded candidates,
7,833 were aligned after a cheap upper bound, 26 were too large to align,
23 passed the score and 19 beat all their shuffles.

| Pair from the literature | Status | Note |
| --- | --- | --- |
| `UR064~UR068` | **REPLICATED** | Found; strongest Puruchuco pair. |
| `UR066~UR067` | **REPLICATED** | Found. |
| `UR063~UR073` | **REPLICATED** | Found, but only through the shared-rare-value seed: no informative run of three equal values. |

| Pair | Read | Bits | Best shuffle | Equal nonzero values | One object? | Museum and number | Mentioned before |
| --- | --- | --- | --- | --- | --- | --- | --- |
| UR1175 ~ UR233 | fwd | 505.7 | 33.7 | 73 | no | Berlin VA42518 / Berlin VA 63038 b | none found |
| AS038/HP036 ~ UR122 | fwd | 345.0 | 66.6 | 28 | no | Lima MNAAHP3550 / Göteborg 1938.45.0228 | Field Guide: listed as similar |
| UR266 ~ UR275 | fwd | 304.2 | 48.9 | 44 | no | Incahuasi project 13829 / Incahuasi project 13836-2014 | none found |
| UR255 ~ UR267A | fwd | 279.3 | 92.4 | 46 | no | Incahuasi project 9228-13 / Incahuasi project 13092 | OKR notes: match |
| UR064 ~ UR068 | fwd | 263.8 | 31.9 | 41 | no | Puruchuco #3 Tex 641 Rt 639 / Puruchuco 2 | Urton and Brezine 2005 |
| UR1175 ~ UR232 | fwd | 255.3 | 28.7 | 50 | no | Berlin VA42518 / Berlin VA63038(B) | none found |
| AS125 ~ UR247 | fwd | 191.6 | 94.7 | 14 | yes | Berlin VA42670 / Berlin VA 42610 | Field Guide: duplicate |
| UR1107 ~ UR237 | rev | 185.1 | 39.5 | 23 | yes | Berlin VA24370(B) / Berlin VA 66834 | Field Guide: duplicate |
| UR053B ~ UR053C | fwd | 134.8 | 44.7 | 25 | no | Lima, BCR ATE 3517 / Lima, BCR ATE 3517 | none found |
| UR256 ~ UR267B | fwd | 134.6 | 47.4 | 19 | no | Incahuasi project 9228-13 / Incahuasi project 13092 | OKR notes: match |
| UR066 ~ UR067 | fwd | 123.7 | 28.0 | 16 | no | Puruchuco 4a / museum not recorded, s/n | Urton and Brezine 2005; OKR notes |
| UR063 ~ UR073 | fwd | 108.8 | 39.7 | 25 | no | Puruchuco s/n / Puruchuco Tex 0637 Rt 0635/28 | Urton and Brezine 2005 |
| UR009 ~ UR021 | rev | 93.2 | 33.4 | 20 | no | Leymebamba CMA 850/LC1-479 / Leymebamba INC-498 | none found |
| UR1118 ~ UR218 | fwd | 90.7 | 37.4 | 8 | no | Berlin VA42601 / Berlin VA 42559 | none found |
| UR1114 ~ UR1123 | fwd | 86.8 | 30.2 | 10 | no | Berlin VA16148 / Berlin VA47085 | none found |
| UR137 ~ QU02 | fwd | 53.3 | 22.1 | 8 | no | Lowe, Miami 57.172.002 / Dallas B388/T41299.24 | none found |
| UR055 ~ UR277 | fwd | 49.6 | 41.7 | 9 | no | Museo Oro 4117-789-1014 203/INC-88 / Incahuasi project 13834-2014 | none found |
| AS026B ~ AS066 | fwd | 45.1 | 34.9 | 10 | no | Penn Museum SA4030 / Núñez del Prado, Cuzco 2a | none found |
| JC009 ~ JC013 | fwd | 41.7 | 23.1 | 9 | no | Incahuasi project PAI-007-2016 / Incahuasi project PAI-008-2016 | none found |

"One object?" is yes when the main cords are within 5% in length and matched
cords differ by 3 cm or less at the median. "Mentioned before" lists what the
OKR notes, the Khipu Field Guide (pages read on 2026-11-24) and the
matching-khipu literature say. "None found" is not a claim that nobody has
noticed.

What the pairs show:

- **Two pairs are one khipu entered twice, and the Field Guide already lists
  both.** Its KH0121 page gives UR237 as an alias of UR1107. Its database-build
  page credits Karen Thompson with spotting from photographs that UR247
  (KH0483) is a duplicate, though its table names a different partner (KH0198)
  from the one found here (AS125). Neither pair is among Manuel Medrano's
  twelve, and both are still two records in OKR. Matched cords agree to
  1.5 and 2.25 cm at the median. The length test flagged these two and
  no others. They show how two recordings of one object differ:
  2 of 29 and 1 of 15 aligned numbers differ (50 against 500, 100
  against 10, 3130 against 31111), and the two recordings of UR1107 share no
  colour name (0 of 21): colour codes cannot be compared across recorders
  without a key.
- **UR1175 carries the numbers of UR233 and then UR232, in that order.**
  UR1175 is the Aschers' AS175 (Pachacamac, Berlin VA42518, 224 pendants).
  Its pendants 0-103 match UR233 (505.7 bits, 73 equal values) and pendants
  127-222 match UR232 (255.3 bits). UR232 and UR233 (Huacho, Berlin VA63038)
  are recorded in the pinned OKR database as spliced together (UR232's primary
  cord note: "Beginning end spliced with UR 233"); the Field Guide gives
  UR232's museum number as VA63038(A). Unlike the known duplicates, matched
  cords differ in length by
  24.0 and 14.0 cm at the median, the main cords are 210 cm against 66 and
  81 cm, and long knots go the other way on 43 of 46 and
  27 of 27 matched cords. The same two projects agreed on every long knot of
  UR1107/UR237, so recording habit does not explain it. Colours are renamed
  one to one (48 of 73 cords follow the commonest pairing, above the
  shuffle that holds numbers fixed); with two recorders that may be their
  vocabularies rather than the dyes. I found nothing linking UR1175 to
  UR232/UR233. The records favour two objects, one carrying the other's
  numbers, but only the museum can settle it.
- **A khipu in Lima and one in Göteborg share a run of large numbers.**
  AS038/HP036 (MNAAHP3550, "Costa Sur") and UR122 (1938.45.0228, "Nazca")
  align over 51 cords with 28 equal values (345.0 bits; best shuffle 66.6).
  The Field Guide's similarity listing already puts the two next to each other;
  I found no statement that they share numbers. They have separate museum
  histories. The Göteborg museum's own record says 1938.45.0228 was deposited
  there by Erland Nordenskiöld (older number 24.6.117), bought from his estate
  in December 1938, found at Nasca, and documented by Gary Urton in June 2005;
  OKR's notes put the Lima khipu in the Museo Histórico collection by 1929. If
  the museum numbers in OKR are right, these are two khipus that have been on
  different continents since at least 1929, not one khipu catalogued twice.
  Many UR122 cords are broken:
  where one side has no readable number, that cord is shorter than its partner
  predicts 11 of 11 times, and all 4 numbers that look cut short (4130
  against 4000 on a 7 cm stub, 932 against 900, 1074 against 1070, 3848
  against 3840) are on the shorter UR122 cord. Four events give p =
  0.0625 on a fair coin: suggestive, not significant.
- **What travels with the numbers** (17 pairs of two objects): colour
  agreement beats a free shuffle in 6 pairs and survives holding the number fixed
  in 2; a one-to-one colour renaming beats the free shuffle in 7 and survives
  within values in 4. Long-knot direction agrees above the free shuffle
  in 6 pairs but never once the numbers are held fixed: knot type follows
  the digit and direction follows type (section 5), so the numbers already
  carry it, and few cords can move in that test. Attachment, spin, fibre and
  termination never beat the shuffle; at khipu level attachment is the same
  in 5 pairs and opposite in 5. Across these pairs the numbers come with the
  colour pattern, often under new names, and with little else that OKR
  records.
- **Broken cords explain unreadable values, not most differing ones.** Across
  these pairs an unreadable cord is shorter than its partner predicts
  65 of 68 times, but a number that looks cut short sits on the
  shorter cord only 7 of 16 times (p = 0.7728).

The thresholds were set after looking at the data, a kept pair is a candidate
until someone checks the objects, and the records cannot rule out one record
typed from another. Report digest `e0769a8c53eb084e75b7fb4c021d9fea8a6ef624119771f77735be4b05295129`.

## Other published readings, not tested here

| Reading | Khipus | In the pinned corpus | Status |
| --- | --- | --- | --- |
| White pendants as boundaries of sum-cord clusters (Medrano and Khosla 2024, Latin American Antiquity) | corpus-wide | yes | NOT_TESTED: article not read |
| Calendar reading of the Chachapoyas khipu UR006 (Urton 2001, Latin American Antiquity 12(2)) | UR006 = KH0242 | yes | NOT_TESTED: article not read |
| First names in cord colour on the Santa khipus (Medrano and Urton 2018) | UR087-UR092 | yes | NOT_TESTABLE here: needs the 1670 name list (Zevallos Quinones 1991), which this project does not hold |
| Collata narrative khipus (Hyland 2017, Current Anthropology 58(3)) | Collata | no | NOT_TESTABLE: not in OKR |

The last three citations are from the literature and were not opened in this run.

## What would move this forward

1. Ask the OKR maintainers and the authors about KH0326 group 15, KH0328
   group 2 and how the published tribute figures fit the 367 total.
2. Send the scrambled-cord result to the syllabary's author. The proposal lists
   what would count against it; this is a fourth test, and the thematic and
   dating evidence can be put through the same scrambling.
3. Obtain the 1670 name list. A name-by-group test is the only one here that
   could confirm or refute a reading at the level of individual groups.
4. Fit a masked-cord sequence model under the hidden-cord harness (same
   scoring, same shuffles) and see whether it beats these count tables. That
   needs a GPU and is ROADMAP.
5. Ask the Ethnologisches Museum Berlin to compare VA42518 (UR1175) with
   VA63038 (UR232 and UR233): cord lengths, long-knot direction, colours. For
   the Lima and Göteborg pair, the Göteborg record is read (see section 6);
   what remains is the MNAAHP, Lima, record for MNAAHP3550 and photographs of
   both khipus side by side.
6. Collect every pair the Field Guide lists as a duplicate and use the
   differences between the two recordings as an error model for sections 3,
   5 and 6.

## Files

| File | What it is |
| --- | --- |
| `santa_valley.py`, `santa_valley_v1.json` | Santa Valley replication and its sealed report. |
| `puruchuco.py`, `puruchuco_v1.json` | Puruchuco reported-sum check and its sealed report. |
| `build_features.py`, `okr_features_v1.json.gz` | Spin, fibre and knot direction per cord, copied from the pinned database (46,822 bytes, sha256 `1cd7c4cd822e0783969ca69a2dfae484b8c81b48ca57989fb535d53367e1d3c9`). Data are MIT (OKR); see `../okr_corpus/LICENSE-OKR.txt`. |
| `hidden_cord.py`, `hidden_cord_v1.json` | Hidden-cord information test and its sealed report. |
| `syllabary_stress.py`, `syllabary_stress_v1.json` | Syllabary stress test and its sealed report. The two dictionaries it reads are not in this repository. |
| `okr_knots_v1.json.gz` | Type, turns and direction of every knot on every corpus cord, copied from the pinned database by `build_features.py --knots` (65,041 bytes, sha256 `1ad88f0252fadcf489e09c1237c0a74bb92c2712d5cec97f3cffd9153cbe6c5e`). Data are MIT (OKR). |
| `knot_direction.py`, `knot_direction_v1.json` | Knot direction against knot type, and its sealed report. |
| `matching_khipus.py`, `matching_khipus_v1.json` | Matching-khipu search, copy comparison and broken-cord check, and its sealed report. |
| `../../tests/test_okr_santa_valley.py`, `test_okr_puruchuco.py`, `test_okr_features.py`, `test_okr_hidden_cord.py`, `test_okr_syllabary_stress.py`, `test_okr_knot_direction.py`, `test_okr_matching_khipus.py`, `test_okr_readings_docs.py` | Unit tests; the last one fails if this page and the sealed reports disagree. |

Digests here are integrity checks, not signatures.

## Reproduce

```
python3 -I research/okr_readings/santa_valley.py --check
python3 -I research/okr_readings/puruchuco.py --check
python3 -I research/okr_readings/hidden_cord.py --check        # about a minute on one core
python3 -I research/okr_readings/knot_direction.py --check
python3 -I research/okr_readings/matching_khipus.py --check    # about a minute
# with the pinned OKR database (see ../okr_corpus/README.md for the download and its digest):
python3 -I research/okr_readings/build_features.py --db PATH/khipu.db --check
python3 -I research/okr_readings/build_features.py --db PATH/khipu.db --knots --check
# with the two dictionaries from the proposal's repository at the commit above
# (reproducibility/data/quechua_kaikki_2074.txt and
#  src/khipu_translator/data/quechua_strict_clean.txt) in one directory:
python3 -I research/okr_readings/syllabary_stress.py --dict-dir PATH --check   # about a minute
python3 -m unittest discover -s tests -p "test_okr_*.py" -v
```
