# Khipu Yachay — external evaluation intake v1

**Research only; not an independent evaluator, production qualification or deployment.**

This stdlib Python runner reads the exact frozen Open-Set R1 model at SHA-256 `1f5dfaf9da2ff2a6228eed02df0cdf12aa9407bf1d5df51f654d53c92c60f47e` and a separate synthetic case bundle. It never trains, downloads models, changes weights or publishes data. Historical khipu interpretation and Quechua-language proficiency are not evaluated.

### How to run

```text
python -B research/khipu_yachay/experiments/heldout_intake_v1/evaluate.py --manifest <private>/manifest.json --cases <private>/cases.jsonl --out <new-private-file>.json
```

The output must not already exist. Inputs are bound to exact SHA-256 bytes; JSON duplicates, changed files, malformed rights declarations, missing OOD denominators and literal overlap with prior training/development/evaluation questions fail closed. Results separately report correct in-domain intents, unnecessary abstentions, unrelated-question false acceptances and declared source-group counts. Diagnostic Wilson intervals are conditional on the submitted cases, not generalization guarantees.

The manifest schema is `szl.yachay.external-intent-manifest/v1`, with `case_count`, `cases_sha256`, `model_sha256`, `data_class=EVALUATOR_AUTHORED_SYNTHETIC`, `evaluation_permission=CALLER_DECLARED_NOT_INDEPENDENTLY_VERIFIED`, `training_admitted=false`, `evaluator_identity_verified=false`, and `group_definition=SOURCE_FAMILY_DECLARED_NOT_ATTESTED`. Case rows use schema `szl.yachay.external-intent-case/v1` with `id, question, expected, source_group, rights_class`. Expected is one of the five existing intents or `ABSTAIN`; rights_class is `CALLER_DECLARED_EVAL_ONLY`. Minimum 10 known-intent and 10 unrelated questions and two declared source groups.

**Independence and permissions are never established by a self-declared string.** A separately authorized external evaluator must control a genuinely untouched case set, rights clearance and the review process. This tool always emits `HOLD_FOR_EXTERNAL_REVIEW_AND_PROVENANCE`, even with perfect scores. Do not upload confidential, unlicensed or community-restricted records; the tool does not verify legal rights or consent.

### Findings carried forward

The fixed synthetic CPU training for Open-Set R1 used 720 first-party examples, but the older developer-known 52-case test still had 7/12 unrelated false acceptances. A dual-witness agreement experiment reduced this to 5/12 and failed its predeclared acceptance gate. Neither method was activated in production. The earlier 80/52/100-case tests remain developer-influenced, not sealed external validation.

A separate clean Windows checkout exposed a genuine byte-integrity defect: `core.autocrlf=true` converted the LF-encoded Open-Set R1 JSON model and receipt artifacts into CRLF, breaking their exact SHA-256 pins. The narrow `open_set_r1/.gitattributes` with `*.json -text` protects all five source-bound artifacts. The test suite verifies their original Git-object digests. No weights or existing production route are changed.

### Admission gates

Owner source review, required CI, untouched external evaluation, rights and Andean scholarly consultation, real deployment and model readback are separate gates. A completed offline process is not training success or production permission.
