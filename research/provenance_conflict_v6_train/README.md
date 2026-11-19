<!-- SPDX-License-Identifier: Apache-2.0
(c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173 -->

# Provenance-native v6 conflict-handling training pack — STAGED

Status: **STAGED.** Nothing here has been trained. The training script refuses to start
unless a results file records that hypothesis H4 of `../provenance_conflict_v3/` held,
and a launch also needs Stephen's approval by name.

## What it is for

Held-out v2 showed every adapter failing the three contradiction probes, and conflict
v3 (preregistered in `../provenance_conflict_v3/`) tests whether that holds on 24 new
ones. If H4 holds, the decision rule there allows one training run targeting conflict
reporting, on data disjoint from both held-out sets. This folder is that data, fixed
before the v3 result is known.

## Pack

`provenance_conflict_pack_v6.jsonl`: 200 chat examples in the corpus v0.5 format, sha256
`77a5963bf9fab9dab46dc3ac6ddfc9c1795896fe567cb1f92030fc4be8883029`.

| Type | n | What the assistant turn does |
| --- | --- | --- |
| two receipts disagree | 60 | names both receipts, both values and both digests; does not pick one |
| two agree, one disagrees | 60 | reports the split; agreement between two receipts does not settle it |
| consistent pair | 60 | states the agreed value and cites the receipts; asserts no conflict |
| single receipt | 20 | states the value and cites the receipt |

Consistent pairs are included so the model does not learn to report a conflict
everywhere, which conflict v3's negative control would catch.

`generate_conflict_pack_v6.py --check-disjoint research/` verifies that no field,
receipt path or question (or its first 40 characters) is shared with held-out v2 or
conflict v3. `tests/test_provenance_conflict_v6_train.py` runs that check in CI.

## Training recipe (staged)

`sft_provenance_native_v06.py`: corpus v0.5 plus this pack, LoRA r16 on
`SZLHOLDINGS/szl-receiptagent-qwen35-0.8b-v2m-estate-sft-v1`, 3 epochs, lr 1e-4 (the v5
recipe), output `SZLHOLDINGS/szl-provenance-native-v6-lora` (private). It aborts with
`ABORT_H4_NOT_HELD` unless `--h4-result` points to a file recording `"H4": "HELD"` and the
receipts commit, and with `ABORT_PACK_CHANGED` if the pack's digest differs.

## Limits

- Synthetic receipts and templated assistant turns: the pack teaches a reporting
  pattern, not knowledge of real estate state.
- 200 examples mixed into corpus v0.5; their effect on the other v2 behaviours is
  unknown until measured.
- v6 must be evaluated on a new held-out set, never on held-out v2 or conflict v3.
