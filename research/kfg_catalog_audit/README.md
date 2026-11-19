# Khipu Field Guide / OKR reproducibility audit

Three separate checks; none labels historical meaning or trains a model.

| Check | Result |
|---|---|
| [Catalog snapshots](catalog_snapshot_audit.json) | All 593 exact KH labels in the 2024 Field Guide release, and all 677 in the sampled live index, appear in the pinned 702-label OKR register. Of 34 other live display labels, 18 have a candidate name or fragment-parent mapping and 16 do not. That is an unresolved reconciliation queue, not evidence of 16 missing artifacts. |
| [Exact single-group relation overlap](xcat/README.md) | On 557 records sharing database ID and catalog label, 39 strictly mapped Field Guide positives agree with SZL on the target, complete summand cord set and value. Eight additional SZL single-group positives do not occur in that mapped positive export. Missing entries are not negatives. |
| [Grouped split replay](grouped/README.md) | The two catalog-documented alias pairs already share the training split. Two similar but not established-duplicate pairs straddle the split. Grouping them for sensitivity moves two artifacts to train (eval rows 366 → 354). No archive was rewritten and no model was trained or evaluated on the new split. |

## Catalog identity and interpretation

The [OKR register](https://github.com/khipulab/open-khipu-repository/blob/4039ca51f4de661d80d0160596309c983a62a9c7/data/okr-kh-numbers.csv) flags KH0140/KH0483 reciprocally, as does the [Field Guide's KH0140 record](https://www.khipufieldguide.com/catalog/KH0140.html). The [Field Guide's index note 8](https://khipufieldguide.com/sketchbook/index.html) documents KH0121/KH0473 as a duplicate identification, while the pinned 2024 snapshots preserve distinct accession labels. Group aliases conservatively for data splitting and retain original records and conflicts. A catalog label or a string match alone does not prove artifact identity.

Top-cord sums are a testable relation, not an assumption for every cord. The public [Medrano and Khosla paper and companion data](https://zenodo.org/records/10472429) are the external reference. Existing SZL totals include up to three adjacent groups; the overlap check explicitly restricts both methods to exact single-group positives. Both derive data partly from common sources. None of these comparisons verifies a historical meaning, corpus prevalence, detector sensitivity, or an independent replication.

## Replay the catalog comparison

Run from this directory with Python 3.10+ and lxml. The sampled index is live; its HTML can change. Compare its SHA-256 to the JSON before expecting byte-identical output. The two CSV URLs below are immutable source revisions.

```sh
curl --fail --location https://raw.githubusercontent.com/khipulab/open-khipu-repository/4039ca51f4de661d80d0160596309c983a62a9c7/data/okr-kh-numbers.csv --output okr.csv
curl --fail --location https://raw.githubusercontent.com/khipufieldguide/data-science-khipu-article/a89c5dc1b8e412e3d0203719f76d5902563ab736/data/khipu_summary.csv --output field-guide.csv
curl --fail --location https://khipufieldguide.com/sketchbook/index.html --output field-guide-index.html
python -m unittest -v test_catalog_snapshot_audit.py
python catalog_snapshot_audit.py okr.csv field-guide.csv --live-index field-guide-index.html > reproduced.json
```
