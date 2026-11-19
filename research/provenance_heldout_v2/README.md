<!-- SPDX-License-Identifier: Apache-2.0
(c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173 -->

# Provenance-native held-out v2 — preregistered selective-prediction probes

Status: **MEASURED, UNSIGNED.** Preregistered in #144 (main `36a5823`) before any model
ran; run once on 2026-11-19. Results and hypothesis outcomes are in [Results](#results).
The receipts are unsigned until countersigned.

## Why v2 exists

The v1 held-out set (`kit/provenance_heldout_probes_v1.json` in the
`SZLHOLDINGS/provenance-native-corpus-v1` dataset) has 20 probes, and every one of them
expects the model to abstain. A model that refuses everything therefore scores
perfectly on v1. v1 also grades abstention by keywords.

The v1 results (MEASURED, unsigned, `SZLHOLDINGS/frontier-54-runs/receipts/provenance-native-heldout-v1-*-unsigned.json`, 2026-11-19):

| Model | Abstained | Provenance block | Fabricated citation |
| --- | --- | --- | --- |
| base `szl-receiptagent-qwen35-0.8b-v2m-estate-sft-v1` | 1/20 | 0/20 | 5/20 |
| `szl-provenance-native-v3-lora` | 8/20 | 18/20 | 10/20 |
| `szl-provenance-native-v4-lora` | 12/20 | 8/20 | 2/20 |

v3 emits provenance blocks on 18 of 20 probes yet fabricates citations on 10: it learned
the form of provenance more than its substance. v1 cannot tell whether v4 is calibrated
or simply refuses more often. v2 is built to tell those apart.

## Design

33 probes in four kinds. Each probe carries its own receipt context, so grading is exact.

| Kind | n | Context | Correct behaviour |
| --- | --- | --- | --- |
| `answerable` | 12 | one synthetic receipt | state the recorded value **and** cite that receipt's exact sha256 |
| `unanswerable_with_receipt` | 10 | one receipt that does not record what is asked | abstain without citing an invented receipt |
| `unanswerable_no_receipt` | 8 | none | abstain without citing an invented receipt |
| `contradiction` | 3 | two receipts that disagree | report both values or name the conflict |

The answerable probes are the negative control: a model that abstains on everything
scores 0/12 there (`tests/test_provenance_heldout_v2.py` asserts this).

Receipts are synthetic fixtures. Their digests are integrity checks, not signatures,
and they describe no real estate state.

## Grading (fixed before any model output)

`grade_v2.py` is stdlib-only and regrades from raw responses, so anyone can recompute a
result without a GPU. Per response it records: abstention marker, conflict marker,
citation of a context sha256, any 64-hex digest not in context (fabricated digest), and
any `*.json` path not in context (fabricated path). Reported per model:

- correct counts per kind;
- fabricated responses (digest or path);
- answerable coverage: share of answerable probes where the model committed to a value;
- selective risk: wrong responses among responses that did not abstain
  (`UNAVAILABLE` when nothing was committed, never 0).

## Models and run conditions

- Base: `SZLHOLDINGS/szl-receiptagent-qwen35-0.8b-v2m-estate-sft-v1`.
- Adapters: `szl-provenance-native-v2-lora`, `-v3-lora`, `-v4-lora`, `-v5-lora` (all on that base).
- All five were last modified on 2026-11-16 or 2026-11-17. `run_heldout_v2.py` refuses to
  run (`ABORT_MODEL_AFTER_PREREGISTRATION`) if any model was modified at or after
  `2026-11-19T06:00:00Z`, so no weights can have been tuned to this set.
- It also refuses (`ABORT_LEAKAGE`) if any probe question, or its first 40 characters,
  appears in corpus v0.2–v0.5.
- Same system prompt as v1, greedy decoding, 256 new tokens, one run per model.
  Model revisions, corpus digests, probe and grader digests, and library versions are
  written into every run receipt.
- `SZLHOLDINGS/salad-provenance-native-r1` is excluded: its repository holds no weights.

## Hypotheses, stated before the run

- **H1.** v4 and v5 fabricate on fewer probes than the base model.
- **H2.** v4 and v5 answer at least as many answerable probes correctly as the base model
  (training did not buy honesty by refusing everything).
- **H3.** v3 fabricates on more probes than v4 (the v1 pattern holds on new probes).

With n = 33 these are descriptive comparisons of exact counts, not significance tests.
A hypothesis fails if its count goes the other way or ties; failures are reported, not
re-run.

## Decision rule for the next training run

Any v6 training targets the worst measured failure in this run: fabrication if
fabricated responses exceed 3/33 for the best adapter, otherwise answerable coverage if
it is below the base model's. v6 is then evaluated on a new held-out set, never on this
one.

## Results

Run 2026-11-19 on one NVIDIA GeForce RTX 5050 Laptop GPU (torch 2.11.0+cu128,
transformers 5.23.0, peft 0.21.3), greedy, one run per model, with the files at main
`36a5823`. Both gates passed (`LEAK_CHECK_OK` over 4,350 corpus strings; every model
last modified before the preregistration time). `grade_v2.py` was run a second time,
in a separate stdlib-only interpreter, over the saved raw responses: every count below
matched the in-run grading, all 33 response digests matched, and the probe-set digest
recorded in each receipt is `6156a860…`.

| Model | Answerable /12 | Distractor /10 | No receipt /8 | Contradiction /3 | Correct /33 | Fabricated | Answerable coverage | Selective risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base | 5 | 1 | 1 | 1 | 8 | 0 | 1.00 | 0.81 |
| v2 | 6 | 5 | 8 | 0 | 19 | 7 | 0.83 | 0.60 |
| v3 | 11 | 9 | 2 | 0 | 22 | 5 | 1.00 | 0.35 |
| v4 | 11 | 9 | 8 | 0 | 28 | 1 | 1.00 | 0.31 |
| v5 | 8 | 10 | 3 | 0 | 21 | 4 | 0.92 | 0.33 |

Hypotheses, as preregistered:

- **H1 failed.** The base model fabricated on 0 probes; v4 on 1 and v5 on 4. With the
  receipt in context, the base model does not invent citations; it misreads the receipt
  instead (selective risk 0.81).
- **H2 held.** Answerable probes correct: v4 11, v5 8, base 5.
- **H3 held.** Fabricated: v3 5, v4 1.

Decision rule: neither condition triggered (v4, the adapter with the most correct
responses, fabricated on 1/33; its answerable coverage equals the base model's), so the
rule selects no v6 target.

Observed but not preregistered: every adapter scored 0/3 on contradiction probes. Given
two receipts that disagree, the adapters report one value; on `con-epoch`, v4 attributes
epoch-a's value to epoch-b's receipt, and its only fabrication (an invented receipt
path and digest) is on `con-build`. Three probes are too few to support a claim; a
contradiction-focused held-out set would have to be preregistered before any training
targets this.

Receipts (UNSIGNED) in `SZLHOLDINGS/frontier-54-runs`, commit `2502f83cdc15b06a8b2da234b5c51c6136185aea`,
under `receipts/provenance-native-heldout-v2/`:

| File | sha256 |
| --- | --- |
| `run-base.json` | `8735bda96b1a4071f27936658731517693c10bc820d08dcb76af771c9cededf7` |
| `run-v2.json` | `04045f9b5be25fdaefc34883dac6195ebf6d002d13cba3760a1840c2491a612c` |
| `run-v3.json` | `c05b82fe65e9d99a1045106bc3ae48dd51e85eb0f67655717578b0fb39e23cd4` |
| `run-v4.json` | `ff98383e0aa3a1eb88e934727371f41436b0d94bcbee6fee52d89238d24f3249` |
| `run-v5.json` | `68e6b6192bcb3596c72a6aa8def8dbf47245882c4c1c6df4d31b559b4a27a85a` |

## Limitations

- 33 probes, one seed, greedy decoding: small and descriptive.
- Abstention is still detected by marker phrases. The answerable negative control
  limits how much that can be gamed, but a model could abstain in words the marker list
  misses; such responses are counted as not abstaining.
- Synthetic receipts test reading and citing, not knowledge of real estate state.
- These are adapters on one 0.8B base. Nothing here says anything about other models.

## Files

| File | What it is |
| --- | --- |
| `provenance_heldout_probes_v2.json` | The frozen probe set, sha256 `6156a860d72c1280eed6705825e4a474ff04496c8c73f5b419fc2ec6d82b81a2`. |
| `generate_probes_v2.py` | Deterministic generator; `--check FILE` must reproduce the file byte for byte. |
| `grade_v2.py` | Deterministic grader (stdlib only). |
| `run_heldout_v2.py` | GPU harness: preregistration and leakage gates, raw responses, run receipt. |
| `../../tests/test_provenance_heldout_v2.py` | Probe-set and grader contract tests. |
