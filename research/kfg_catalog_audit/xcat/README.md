# Khipu cross-catalog positive overlap

Use Python 3.9+ with the standard library. From the directory containing `compare.py`:

```sh
KFG=https://raw.githubusercontent.com/khipufieldguide/data-science-khipu-article/a89c5dc1b8e412e3d0203719f76d5902563ab736/data
OKR=https://huggingface.co/spaces/SZLHOLDINGS/khipu-proof-loom/resolve/c947def2fe0eae460c304d5ce0b7eb8e2881d9a5
curl --fail --location "$KFG/KFG_DB.SQL" --output KFG_DB.SQL
curl --fail --location "$KFG/khipu_summary.csv" --output khipu_summary.csv
curl --fail --location "$KFG/ascher_sum_relations/sum_top_cords_relation.csv" --output sum_top_cords_relation.csv
curl --fail --location "$OKR/okr_corpus_v1.json.gz" --output corpus.json.gz
curl --fail --location "$OKR/okr_relations_v1.json" --output okr.json
python compare.py > reproduction.json
cmp result.json reproduction.json
```

All five input hashes are embedded in the script and result. Do not use Python's `-O` mode, which strips the script's integrity and schema assertions.
KFG release: [Data Science Khipu Article v2.1.0](https://github.com/khipufieldguide/data-science-khipu-article/tree/a89c5dc1b8e412e3d0203719f76d5902563ab736). OKR inputs: [Proof Loom publication manifest](https://huggingface.co/spaces/SZLHOLDINGS/khipu-proof-loom/blob/c947def2fe0eae460c304d5ce0b7eb8e2881d9a5/SOURCE.json).

We restrict artifacts to records sharing both the numerical database ID and the OKR name. On the KFG side, we filter the published relation rows for documented exactness and integer equality, positive target, at least two summands, and adjacent cluster positions; then recover the target and the complete summand cord IDs from the SQL tables. The artifact's target cluster must agree with the CSV's zero-based position on the relevant primary in the SQL sort. On the SZL side, we filter published exact R2 positives for one summand cluster. The join key is artifact ID, target cord ID, sorted complete summand cord ID list, and value.

Of 650 KFG and 619 OKR artifacts, 558 have the same numerical ID, and 557 agree on both keys. On those 557, all 39 strictly mappable KFG positive rows agree with the SZL rows, across 11 artifacts. SZL has 47 single-group positives on the shared records, eight of which do not occur in the strictly mapped KFG positive export. Seven additional SZL multigroup positives are out of scope. The KFG CSV has 86 total rows, 62 satisfy the strict positive predicate across the full KFG catalog, and 60 map positionally across that full catalog. There are three export flag/arithmetic discrepancies and two strict positive rows with unresolved pinned position mappings. Neither discrepancy nor absence in the export is treated as a negative or an error by either method.

This compares published detections and their cord identities. Shared source records mean it is not independent replication. The exported positives do not define a complete negative or eligible-candidate denominator: do not infer precision, sensitivity, corpus prevalence or narrative decipherment. The KFG web guide is updated separately; it is not pooled with the pinned release here.

Optional native SZL recomputation (review the pinned source before executing it):

```sh
curl --fail --location "$OKR/okr_khipu.py" --output okr_khipu.py
python verify_okr.py
```
