<!-- SPDX-License-Identifier: Apache-2.0
(c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173 -->

# OKR khipu sum relations — exact decimal sums under a permutation null

Status: **MEASURED** on the pinned Open Khipu Repository (OKR) records with a
within-khipu permutation null. This is a count of exact arithmetic coincidences
in a transcription, compared with chance. It is **not** decipherment, it says
nothing about narrative khipus, and no result here is a proof of intent.

What it asks: in real Inka-style khipus, how often does one cord's knotted value
equal the exact sum of other cords' values, in the structural positions Marcia
and Robert Ascher described in *Code of the Quipu* (1981) — and is that more
often than the same values would produce if they were shuffled within the
khipu?

Short answer from this run: **top-cord sums (R2) are far above chance and
robust to every check below.** In-group sum cords (R4) are far above chance
corpus-wide, but almost all of that comes from the Incahuasi archive.
Subsidiary sums (R1) are above chance corpus-wide only because of one khipu.
Sums of a different whole group (R3) are **not** above chance.

## Files

| File | What it is |
| --- | --- |
| `build_corpus.py` | Deterministic builder (stdlib only). Refuses any `khipu.db` whose SHA-256 is not the pinned one. `--check` re-derives and compares bytes. |
| `okr_corpus_v1.json.gz` | Compact corpus (892,079 bytes), sha256 `6ef204b641826b37c320509952ed4181e93865af20f1cdfefd7516a49cf8ad0d`. Data are MIT (OKR). |
| `okr_corpus_v1.manifest.json` | Source commit, input digests, corpus digests, counts, decoding rules, licence line. |
| `okr_relations_v1.json` | Precomputed corpus statistics and per-khipu relation lists (370,512 bytes), sha256 `a9f38398359e88819514333c083bdfd9b5880fb2b428847c872630c8b317a038`; records the corpus digest it was computed from. |
| `LICENSE-OKR.txt` | The OKR MIT licence, verbatim from the pinned commit. |
| `../../szl_khipu/okr_khipu.py` | Runtime engine (stdlib only): decoding, relation search, null model, 3D scene, khipu card. |
| `../../tests/test_okr_khipu.py` | Unit tests (`python -m unittest discover -s tests -p test_okr_khipu.py`). |

Digests here are integrity checks, not signatures.

## Source and pins

- Repository: https://github.com/khipulab/open-khipu-repository at commit
  `4039ca51f4de661d80d0160596309c983a62a9c7`.
- `data/khipu.db` sha256 `607913034a0f478c5c792025d0c3cab8a9a8f05223ed6bc9c2990122a8c1c4db`.
- `data/okr-kh-numbers.csv` sha256 `d0453883762b2511f72bf48672a7c018084d67d59fe12a4a11bc3ab6b9708e5e`
  (used only for the "Other Names" and "Country" columns).
- Cite the OKR as: Open Khipu Repository, DOI https://doi.org/10.5281/zenodo.18025748.

## Reproduce

```
# download the two pinned inputs (same commit) into one directory, then:
python3 -I research/okr_corpus/build_corpus.py --db PATH/khipu.db \
    --out research/okr_corpus/okr_corpus_v1.json.gz --relations --trials 1000
# verify the shipped files byte for byte (about 45 s on one CPU core):
python3 -I research/okr_corpus/build_corpus.py --db PATH/khipu.db \
    --out research/okr_corpus/okr_corpus_v1.json.gz --relations --check
# unit tests; the rebuild test runs only when SZL_OKR_DB points at the pinned db:
SZL_OKR_DB=PATH/khipu.db python3 -m unittest discover -s tests -p test_okr_khipu.py -v
```

The builder opens the database read-only (`mode=ro`), treats every text field as
untrusted data (control characters removed, whitespace collapsed, surrounding
quotes stripped, capped at 200 characters), writes JSON with sorted keys and
fixed separators, and gzips with `mtime=0`. Two runs give identical bytes. If a
different zlib build changes only the gzip stream, `--check` says so explicitly
and still fails.

## How the OKR tables were read

These readings come from inspecting the pinned database; the manifest repeats them.

- **Parents.** `cord.PENDANT_FROM` is the parent: a `primary_cord.PCORD_ID` for
  pendants and top cords, a `cord.CORD_ID` for subsidiaries. `cord.ATTACHED_TO`
  is 0 or NULL on every row and is not used. 38,717 cords hang from a primary
  cord of their own khipu, 15,379 from another cord, and 307 have no resolvable
  parent (`PENDANT_FROM` 0, unknown, or a primary cord recorded under a
  different khipu).
- **Levels and roles.** `CORD_LEVEL` 1 = hangs from the primary cord, 2, 3, ... =
  subsidiary depth. **Negative levels are the top-cord side:** every level −1
  cord sits in a `cord_cluster` whose `GROUPING_CLASS` is `T` (top cords), and
  −2/−3 cords are subsidiaries of those top cords. Some transcriptions instead
  record top cords at level 1 inside a `T` or `TPA` cluster; both are treated as
  top cords. Clusters classed `M` (marker), `K` (knot) or `X` (extension) are
  markers and are not searched. Resulting roles: 38,120 pendants, 252 top
  cords, 15,379 subsidiaries, 636 markers, 16 orphans (|level| ≥ 2 with no
  resolvable parent).
- **Order and groups.** `CORD_ORDINAL` orders the cords along a primary cord,
  with top cords interleaved among the pendants (checked on AS-, UR- and
  HP-series transcriptions). A *pendant group* is a maximal run of consecutive
  pendants on one primary cord that share a `CLUSTER_ID`.
- **Knot values.** `knot.knot_value_type` is the knot's own decimal contribution
  (a single knot in the tens position is 10, a long knot of 4 turns in the units
  position is 4, a figure-eight knot is 1). It is never NULL in this database
  but is 0 on 211 knots whose value could not be read.
  `knot_cluster.TOTAL_VALUE` is 0 or NULL on every row and `END_POS` is never
  greater than `START_POS`, so neither is used. Knot position is
  `knot_cluster.START_POS` (cm from the attachment).
- **Colour.** The longest `ascher_cord_color` range of each cord gives its colour
  label; RGB comes from `ascher_color_dc` for that label's first colour code.
  Cords with no colour row get no RGB, and renderers draw them neutral grey.
  No colour is invented or blended.

### Decoding rules (value of a cord)

1. Value = sum of `knot_value_type` over the cord's knots.
2. Any knot with a missing or non-positive value makes the **whole cord
   UNKNOWN** (`None`). Unknown is never treated as 0.
3. A cord with no knots is 0 with status `knotless`.
4. A knotless cord whose end is broken (`B`) or cut (`C`) is **UNKNOWN**
   (`broken_knotless`), because its knots may have been lost.
5. A broken cord that still has knots keeps its recorded sum. Relations that
   touch such a cord carry `involves_broken_cord: true`.

Counts: 36,944 cords known, 12,144 knotless, 5,315 unknown (5,177
broken-knotless, 138 with an unreadable knot). 526 knot rows point at no cord
row and are excluded. 85 knots have a recorded contribution that is not a single
digit times a power of ten (for example long knots of 11–16 turns, single knots
recorded as 2500). They are kept as recorded and counted in the manifest.

## Relation types (fixed before the corpus-wide run)

All four rules were written after looking at the structure of a few khipus
(KH0079, KH0359, KH0358, KH0389, KH0217) and before any relation was counted.
A first corpus-wide observed count and a null run on three khipus were used
only to check runtime. After that the only thing inspected was whether top-cord
ordinals interleave with pendants (they do), and no rule was changed. R3 was
not re-tuned after it came out at chance.

Every relation needs the target and all summands to have known values, at
least **two nonzero summands** (otherwise it is an equality, not a sum; this
also excludes 0 = 0 + 0), and a positive target.

| Type | Rule | Bounded search space |
| --- | --- | --- |
| **R1** subsidiary sum | A cord's value = the sum of **all** its direct subsidiaries (≥ 2 subsidiaries). | One test per eligible parent (1,984 in the corpus). |
| **R2** top-cord sum | A top cord's value = the sum of 1–3 **consecutive whole pendant groups** that touch the top cord's position: the group(s) immediately before or after it, or the group it sits inside. Total ≥ 2 pendants; in a multi-group union every group must be nonzero. | At most 9 unions per top cord (1,812 in the corpus). |
| **R3** group-sum cord | A pendant's value = the sum of all pendants of a **different** whole group (group size ≥ 2, target ≥ 10). | Every eligible group × every known pendant (699,754 pairs in the corpus, excluding own-group pairs). |
| **R4** in-group sum cord | The **first or last** pendant of a group with ≥ 3 pendants = the sum of the other pendants of that group. | Two tests per eligible group (6,196 in the corpus). |

R4 was added to the other three to cover sum cords placed at the start or end
of their own group, a placement discussed in the khipu literature since the
Aschers. It was specified at the same time as R1–R3. Counts are numbers of
matching (target, summand set) pairs, so one R3 target that equals several
groups is counted once per group.

## Chance control

- **Null.** For each khipu, known cord values are shuffled among cords of the
  same stratum: (root role pendant/top/marker/orphan, subsidiary or not,
  depth). Structure, cord positions and the missingness pattern stay fixed;
  unknown cords stay unknown. The identical relation search is rerun on every
  permutation.
- **Robustness null** (`role_depth_magnitude`): additionally shuffle only among
  values with the same number of decimal digits, so each cord keeps its order
  of magnitude. This is stricter where magnitudes cluster locally.
- **Per-khipu p** = (1 + #{null count ≥ observed}) / (trials + 1).
  Deterministic: `random.Random` seeded from sha256(`szl.okr_null/v1:{seed}:{khipu id}`),
  seed 1981, 1000 trials. The smallest attainable p is 1/1001 ≈ 0.000999.
- **Pooled corpus test.** For each trial t the per-khipu null counts are summed
  across all 619 khipus. The observed corpus total is compared with those 1000
  sums.
- **Drop the top khipu.** The pooled test is repeated without the single khipu
  that contributes most observed relations of that type. This check was added
  after the first full run showed the relations were concentrated. It can only
  weaken a claim, never strengthen one.
- **Multiple testing.** The four pooled tests are the primary result (Bonferroni
  threshold 0.05 / 4 = 0.0125). Per-khipu p-values are uncorrected and
  descriptive. Benjamini–Hochberg at q = 0.05 across the khipus that could be
  tested is reported too, but with 1000 permutations the p floor (0.000999)
  limits it.

## Results (MEASURED, pinned OKR records, 1000 permutations, seed 1981)

From `okr_relations_v1.json`, produced by the `--relations --trials 1000`
command above. Primary null: `role_depth`.

| Type | Observed | Null mean (sd) | Obs / null | z | Pooled p | Magnitude-null obs/null, p | Khipus with ≥1 / tested | Without top khipu: obs vs null, p |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |
| R1 subsidiary sum | 59 | 35.78 (5.69) | 1.65× | 4.08 | ≤ 0.001 | 1.55×, ≤ 0.001 | 30 / 228 | KH0349 dropped (16): 43 vs 34.89, **p = 0.097** |
| R2 top-cord sum | 54 | 4.96 (1.94) | 10.89× | 25.29 | ≤ 0.001 | 8.27×, ≤ 0.001 | 14 / 35 | KH0079 dropped (11): 43 vs 4.53, p ≤ 0.001 |
| R3 different-group sum | 714 | 639.70 (52.13) | 1.12× | 1.43 | **0.083** | 1.05×, **0.281** | 101 / 537 | KH0082 dropped (122): 592 vs 510.55, p = 0.041 |
| R4 in-group sum cord | 106 | 28.84 (5.28) | 3.68× | 14.60 | ≤ 0.001 | 3.76×, ≤ 0.001 | 40 / 502 | KH0503 dropped (15): 91 vs 28.68, p ≤ 0.001 |

"≤ 0.001" means p = 0.000999, the floor for 1000 permutations: no permuted
corpus reached the observed total. 156 of the 612 khipus that have cords show
at least one relation of any type; 78 show at least one R1, R2 or R4.

Per-khipu results (uncorrected, role_depth null): khipus with p ≤ 0.01 are
R1 6, R2 8, R3 9, R4 18. Benjamini–Hochberg at q = 0.05 retains 8 khipus for R2
(KH0079/AS066, KH0055/AS044, KH0109/UR1096, KH0217/AS199, KH0358/UR118,
KH0405/UR166, KH0359/UR119, KH0424/UR186) and none for R1, R3 or R4.

**Post-hoc check (not pre-specified; labelled as such).** 73 of the 106 R4
relations come from the 52 khipus whose provenance is Incahuasi. Excluding those
52 khipus (567 remain, same seeds, role_depth null, 1000 trials):
R1 57 vs 33.71 (p ≤ 0.001), R2 54 vs 4.96 (p ≤ 0.001), R3 694 vs 612.29
(p = 0.056), **R4 33 vs 27.25 (p = 0.157)**. Command:

```
python3 -c "from szl_khipu import okr_khipu as ok; c=ok.load_corpus(); s=ok.corpus_statistics({'khipus':[k for k in c['khipus'] if k['provenance']!='Incahuasi']}, trials=1000, strata='role_depth'); print({t:(r['observed'],r['null_mean'],r['pooled_p']) for t,r in s['by_strata']['role_depth'].items()})"
```

### What the measurements support

- **Top-cord sums (R2): strong and robust.** In 14 khipus top cords equal the
  exact sum of the adjacent pendant group(s) 54 times, against about 5 expected
  by chance. This survives the magnitude-preserving null, dropping the
  top-contributing khipu, and excluding Incahuasi. Example, KH0217 (AS199):
  top cord 513 = 55 + 46 + 214 + 57 + 44 + 97, the group beside it. This
  matches the hierarchical summation the Aschers documented, observed here in
  the pinned OKR records at p ≤ 0.001 under a within-khipu permutation null.
- **In-group sum cords (R4): strong corpus-wide, concentrated.** The excess is
  real for the corpus as recorded, but it comes almost entirely from the
  Incahuasi khipus (for example KH0503/UR267A: 106 = 15 + 91, 206 = 15 + 191,
  ...). Outside Incahuasi, R4 is not distinguishable from chance in this test.
- **Subsidiary sums (R1): weak.** The corpus-wide excess is carried by one khipu,
  KH0349 (UR113, Nazca), with 16 small-valued sums (e.g. 8 = 2 + 1 + 1 + 4).
  Without it, p = 0.097.
- **Sums of a different whole group (R3): not above chance** at the pre-set
  threshold (p = 0.083; 0.281 under the magnitude null). Individual khipus such
  as KH0079 (AS066, 61 vs 15.66) and KH0225 (AS207A, 49 vs 8.85) do show an
  excess, but corpus-wide the large search space is dominated by coincidences
  among small, repeated values.

The careful phrasing for the app is: *exact top-cord sums occur about 11× as
often as under a within-khipu permutation null in the pinned OKR records
(p ≤ 0.001, 1000 permutations).* That is evidence that the recorded numbers are
arranged additively. It is not a reading of what the numbers counted.

## Limitations

- **Transcription, not artifact.** Values are what recorders entered. Recording
  errors, misread knots, and different conventions between recorders (Ascher,
  Urton, Pereyra and others, entered by different people over decades) are all
  inside these numbers. An off-by-one entry deletes a true relation; nothing here
  can repair that.
- **Damage.** 9,392 cords are recorded as broken. Broken knotless cords are
  UNKNOWN; broken cords with knots keep their recorded (possibly truncated)
  sum. 12 R1, 13 R2, 129 R3 and 36 R4 relations involve a broken cord.
- **Ambiguous structure.** 307 cords have no resolvable parent. Pendant groups
  come from OKR `CLUSTER_ID`s, which may not match how an analyst would group
  by spacing or colour. Ordinals tie on a few khipus; ties break by cord id.
- **Null model.** The permutation null keeps the multiset of values and the
  structure but not local magnitude patterns. The magnitude-stratified null
  addresses part of this, and the conclusions above hold under both. Each null
  answers "more than these same values would produce if placed at random within
  this khipu", not "more than any conceivable process".
- **Concentration and dependence.** Khipus from one archive (Incahuasi) or one
  recorder are not independent samples; the post-hoc split shows how much one
  archive moves R4. OKR assigns one KH number per khipu, and no further
  de-duplication was done.
- **Multiple testing.** Four pooled tests are primary. Per-khipu p-values are
  uncorrected; with about 600 khipus, several p ≤ 0.01 values per type are
  expected by chance alone.
- **Other relations.** The four rules cover only part of what the Aschers
  described (no cross-khipu sums, no colour-defined groups, no non-adjacent
  groupings). A relation type that is absent here may still exist under a
  different definition. Testing such a definition would need its own
  pre-specification and correction.

## Runtime (measured on this container, one process, Python 3.13)

| Call | Median-size khipu (KH0122, 42 cords) | Largest khipu (KH0082, 1,831 cords) |
| --- | ---: | ---: |
| `find_relations` | 0.2 ms | 5.4 ms |
| `scene` | 0.8 ms | 47 ms (drawn cords capped at 1,500) |
| `null_model(trials=200)` | 4 ms | 129 ms |
| `khipu_card(report=...)` | 0.3 ms | 6.6 ms |

`load_corpus` (cold, with digest check and per-cord re-decoding) takes 0.64 s,
and `list_khipus` 0.06 s. The full corpus statistics (619 khipus × 1000
trials × 2 nulls) take about 45 s and are shipped precomputed.

## Licence and provenance

The khipu data are from the Open Khipu Repository and remain under its MIT
licence:

> MIT License — Copyright (c) 2022 Open Khipu Repository Team. Permission is
> hereby granted, free of charge, ... The above copyright notice and this
> permission notice shall be included in all copies or substantial portions of
> the Software. (Full text: `LICENSE-OKR.txt`.)

The builder, engine, tests and this document are Apache-2.0, SZL Holdings. The
derived corpus is a re-encoding of OKR fields (no notes, no images). Please cite
the OKR DOI https://doi.org/10.5281/zenodo.18025748 when using it.

## Credit

The numbers here exist because of decades of recording work. The OKR lists its
data contributors as: Alcides Alvarez, Bat-ami Artzi, Marcia Ascher, Robert
Ascher, Alicia Boswell, Carrie Brezine, Saoirse Byrne, Andres Chirinos, Jon
Clindaniel, Mackinley FitzPatrick, Ivan Ghezzi, Di Hu, Sabine Hyland, Ashok
Khosla, Manuel Medrano, Hugo Pereyra, Kylie Quave, Alejo Rojas, William
Scannell, Julia Strauss, Karen Thompson, Gary Urton and Rosa María Varillas.
At the pinned commit the OKR Advisory Board is Carrie Brezine, Mackinley
FitzPatrick, Iván Ghezzi, Sabine Hyland, Manuel Medrano and Jeffrey
Splitstoser. The repository is administered by the Open Khipu Research
Laboratory and maintained by the OKR Team. The relation types follow Marcia
Ascher and Robert Ascher, *Code of the Quipu: A Study in Media, Mathematics,
and Culture* (University of Michigan Press, 1981). Any error in reading the
tables is ours, not theirs.

## Ethics

Following the OKR's own statement: these are **Inka-style khipus** from
archaeological contexts across the Andes and from museum collections worldwide.
They are part of the material heritage of Andean peoples and are not solely
Peruvian; several Andean countries consider khipus part of their heritage. The
OKR prefers neutral KH numbers to identifiers built from scholars' initials, so
this module uses the KH number as the primary identifier and shows investigator
numbers (AS…, UR…) only as secondary labels. The khipus were collected and
recorded within the power structures the OKR names in its README. This module
re-reads published numbers. It does not decipher narrative khipus, does not
assign meanings to the counts, and should not be presented as speaking for the
communities whose heritage these objects are.
