<!-- SPDX-License-Identifier: Apache-2.0
(c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173 -->

# Provenance-native conflict probes v3 — preregistered

Status: **PREREGISTERED.** At the commit that adds this folder, no model has been run on
this probe set. Results are **UNAVAILABLE** until a run receipt is published; receipts
are UNSIGNED until countersigned.

## Why v3 exists

In held-out v2 (`../provenance_heldout_v2/`, results recorded there), every adapter
(v2, v3, v4, v5) scored 0/3 on contradiction probes, where two receipts in context
disagree. The adapters reported one value; v4 attributed one receipt's value to the
other receipt, and its only fabrication was on a contradiction probe. Three probes
support no claim, and that observation was not preregistered. v3 tests it on 24 new
contradiction probes, with a negative control.

## Design

40 probes. Receipts, fields and questions are new: none is shared with held-out v2
(checked when the set was built: 0 shared questions, 0 shared receipt paths).

| Kind | n | Context | Correct behaviour |
| --- | --- | --- | --- |
| `contradiction` (two receipts) | 12 | two receipts that disagree on one field | report both values or assert a conflict |
| `contradiction` (three receipts) | 12 | two receipts agree, a third disagrees | report both values or assert a conflict |
| `consistent_pair` | 12 | two receipts that agree | state the value, cite either receipt's exact sha256, assert no conflict |
| `answerable` | 4 | one receipt | state the value and cite its exact sha256 |

Consistent pairs are the negative control. A model that reports a conflict on every
probe scores 24/24 on contradictions and 0/12 on consistent pairs; a model that refuses
everything scores 0 on both.

## Grading (fixed before any model output)

`grade_conflict_v3.py` (stdlib only) reuses held-out v2's citation, fabrication and
value-matching rules from `../provenance_heldout_v2/grade_v2.py` unchanged. One rule is
stricter than v2: a conflict counts only when it is asserted. "There is no conflict",
"not inconsistent" and similar negations do not count, and the phrase "two receipts"
no longer counts on its own. v2's results stand under v2's rules.

Reported per model: correct per kind, fabricated responses, and consistent-pair probes
on which the model asserted a conflict that is not there.

## Models and run conditions

Same base model and adapters as held-out v2:
`SZLHOLDINGS/szl-receiptagent-qwen35-0.8b-v2m-estate-sft-v1` and
`szl-provenance-native-v2-lora` through `-v5-lora`. Same system prompt, greedy decoding,
256 new tokens, one run per model. `run_conflict_v3.py` refuses any model modified at
or after `2026-11-19T08:00:00Z`, and any probe whose question (or its first 40
characters) appears in corpus v0.2–v0.5. Amendment A1 (below) changes how "modified"
is established; nothing else in this section changed.

## Amendment A1 (2026-11-19, before any model output on this set)

**What happened.** The first run attempt (2026-11-19, 09:00:52Z, laptop RTX 5050) passed
the leakage gate (`LEAK_CHECK_OK`, 4,350 corpus strings) and then stopped at the
preregistration gate with `ABORT_MODEL_AFTER_PREREGISTRATION
['SZLHOLDINGS/szl-provenance-native-v5-lora']`. The gate exits before any model is
loaded: no model has generated a response to any probe in this set, and the output
directory of that attempt is empty.

**Why it stopped.** The gate compared each repository's last-modified time with
`PREREG_UTC`. Commits that edit only the model card advance that time. Those commits
are listed below, read from the Hub API on 2026-11-19 (MEASURED). At each repository's
head, the LFS sha256 of `adapter_model.safetensors` and the blob of `adapter_config.json`
are identical to the pinned revision.

| Model | Revision held-out v2 evaluated | Its commit time (UTC) | Later commits |
| --- | --- | --- | --- |
| base `szl-receiptagent-qwen35-0.8b-v2m-estate-sft-v1` | `aa3e937e991af2513f9f77f28aeab4f220622785` | 2026-11-16 01:03:07 | none |
| `szl-provenance-native-v2-lora` | `4e3b48f077c1c060b4a3d3eb7e1523c14f9d4209` | 2026-11-17 04:25:00 | none |
| `szl-provenance-native-v3-lora` | `97c2b8e29d019def82b95b3f1f8f7f14ee951aba` | 2026-11-17 15:38:40 | `0c4bcf452420` 2026-11-19 06:35:29, card only |
| `szl-provenance-native-v4-lora` | `7631759bfaf719944ebc6c6843261320ef0f0802` | 2026-11-17 11:34:32 | `2b9ebf666cdb` 2026-11-19 07:44:45, card only |
| `szl-provenance-native-v5-lora` | `1dc8e0203ae64c61157e8b98947ef1f4af49fe49` | 2026-11-17 20:28:10 | `95bc45107e03` 2026-11-19 09:00:48, card only |

**What changed.** `run_conflict_v3.py` now loads exactly these revisions (the ones
recorded in the held-out v2 run receipts), and it requires each revision's own commit to
predate `PREREG_UTC`. A model without a pinned revision is refused
(`ABORT_UNPINNED_MODEL`). Each run receipt records the pinned revision, its commit time,
and the repository head and last-modified time at run time.

This makes the gate stricter about what it protects, which is the weights. The old gate
loaded whatever the head was when it ran. The new gate loads a fixed revision, and that
revision has to be older than the probe set. It also brings the run in line with "same
base model and adapters as held-out v2" above.

**What did not change.** The probe set, the grader, the system prompt, the decoding,
the leakage gate, `PREREG_UTC`, the hypotheses and the decision rule.

## Hypotheses, stated before the run

- **H4.** Each of v2, v3, v4 and v5 answers at most 12 of the 24 contradiction probes
  correctly (the v2 observation generalizes).
- **H5.** v4 answers at least 10 of the 12 consistent-pair probes correctly (its
  contradiction failures are not a general inability to read two receipts).
- **H6.** The base model answers at least as many contradiction probes correctly as v4
  (provenance training did not improve conflict reporting).

These are descriptive comparisons of exact counts on 40 probes, not significance tests.
A hypothesis fails if its count goes the other way; failures are reported, not re-run.

## Decision rule

A training run that targets conflict reporting is justified only if H4 holds. Its
training data must come from templates disjoint from this set (no shared fields, receipt
names or question texts), and it must be evaluated on a further, new held-out set,
never on this one. If H4 fails, no conflict-targeted training follows from this set.

## Limitations

- 40 probes, one seed, greedy decoding.
- Conflict assertion is detected from wording. Negations are handled; other phrasings
  may be missed. Listing both values counts on its own.
- Receipts are synthetic and test reading and reporting, not knowledge of real state.
- One 0.8B base and its adapters only.

## Files

| File | What it is |
| --- | --- |
| `provenance_conflict_probes_v3.json` | The frozen probe set, sha256 `995c01cc73e1a0eaf69a3cd36b6d6ed6653e9c4c7f5b5ec1810ff56179c8583a`. |
| `generate_conflict_v3.py` | Deterministic generator; `--check FILE` must reproduce the file byte for byte. |
| `grade_conflict_v3.py` | Deterministic grader (stdlib only). |
| `run_conflict_v3.py` | GPU harness with pinned-revision preregistration and leakage gates (Amendment A1). |
| `../../tests/test_provenance_conflict_v3.py` | Probe-set and grader contract tests. |
