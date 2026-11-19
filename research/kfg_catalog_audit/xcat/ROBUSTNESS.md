# Artifact-level robustness of the strict cross-catalog match

The frozen comparison reports **39 matching relations in 11 artifacts**. In descending order, the object counts are 6, 5, 5, 5, 4, 4, 4, 2, 2, 1 and 1. The largest contributor, KH0055 (AS044), supplies 6/39 (15.4%). The four largest contribute 21/39 (53.8%).

Deleting any one of the 11 matching artifacts leaves **33–38 rows across 10 artifacts**; deleting any one of the full 557 shared identity records can leave up to 39 because removing a non-contributor changes no match counts. Deleting all four largest contributors still leaves 18 matches in seven artifacts. The JSON gives each exact omission result.

| Descriptive restriction on frozen exact matches | Rows | Artifacts |
|---|---:|---:|
| None | 39 | 11 |
| Nonblank provenance not labeled Unknown | 23 | 8 |
| Every recorded summand value strictly positive | 32 | 11 |
| Neither target nor summands have termination code B or C | 29 | 9 |
| All three restrictions together | 13 | 6 |

These are post-hoc sensitivities, not new detection runs. Provenance refers to the metadata field, not verified geography; the B/C filter follows the pinned SZL termination-code convention. Deletion is by complete artifact, not individual cord. The full 557 objects are an identity-concordance frame, not the eligible relation denominator. The 39 strictly mapped KFG positives and the 47 OKR single-group positives are positive lists, not ground-truth labels for all scored or unscored candidates. These finite-catalog counts do not justify confidence intervals, accuracy estimates, or a claim of independent replication.

Reproduce with the pinned inputs described in the cross-catalog README, plus its generated `result.json`:

```sh
python robustness.py > robustness_replay.json
cmp robustness.json robustness_replay.json
```
