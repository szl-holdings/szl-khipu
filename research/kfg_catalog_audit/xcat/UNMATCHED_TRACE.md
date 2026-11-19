# Trace of the eight OKR-only positive rows

Run from the same directory as the inputs and baseline `result.json` described in the cross-catalog README:

```sh
python trace_unmatched.py > unmatched_replay.json
cmp unmatched_trace.json unmatched_replay.json
```

For each baseline unmatched row, the script finds the same target cord and complete group membership in the pinned KFG SQL cord tables, reconstructs values by summing the recorded knot decimals (no recorded knots contribute zero here), and reconciles the independently recorded relation CSV's target-cluster identity and positions. These are preselected SZL candidates checked in a second catalog's shared source records, not a rerun of KFG detection or an independent sample.

| OKR (KFG) | Value | Pinned source finding |
|---|---:|---|
| KH0217 (AS199) | 463 | SQL inputs match; no relation CSV row for this target cluster. |
| KH0068 (UR1057) | 2 | CSV points to a different 14-cord group totaling 3, despite an exact flag. SZL's seven-cord summand cluster is separated from the target by a non-pendant cluster in the SQL position order. |
| KH0277 (UR047) | 100 | CSV reports the other adjacent 10-cord group. Both groups independently contain ten cords of value 10 in the pinned SQL. |
| KH0323 (UR087) | 15 | CSV reports the opposite group as a 15 versus 16 near match. The SZL candidate sums to 15. |
| KH0358 (UR118) | 395 | CSV reports a single-cord 395 versus 495 near match. The target key does not anchor at the CSV position; the declared summand position selects a 495 cord in the SQL ordering. The separate six-cord SZL group sums to 395. |
| KH0358 (UR118) | 581 | Exact-valued CSV row, but target and summand positions do not anchor to their designated roles in the pinned SQL order. |
| KH0109 (UR1096) | 17 | Exact-valued CSV row, but target and summand positions do not anchor to their designated roles in the pinned SQL order. |
| KH0079 (AS066) | 200 | Same eight summands and equal arithmetic in SQL and export, but the CSV exact flag is false. |

All eight exact equalities can be reproduced on the same full cord IDs in the pinned KFG SQL. Seven have a relation CSV row for the same target cluster; one does not. The frozen 39 strict cross-catalog overlap count remains unchanged. These eight records are neither evidence of false negatives nor independent validation, and none supports decipherment.
