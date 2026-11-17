# Khipu Yachay — Exact-Byte Admission & Untouched Quality Hold

**Status (2026-11-17):** Source-only, researched, **not deployed**, and no
historical data added to training. This note documents the PR #121 source
snapshot `b16cc3e3f8ffdb776ebb7b0b46263e58a77b6929` and an additional
developer-authored diagnostic. No model weights or original evaluation data
were altered in this repair.

## Material Windows reproducibility finding

A fresh standard Git Windows checkout converted canonical LF JSON and JSONL
objects into CRLF. The model's raw SHA-256 changed, and
`space.app.load_state` **correctly denied startup** with
`MODEL_SOURCE_BINDING_FAILED`. In the affected checkout, one added CR byte
changed the 15,980-byte model, and 540 added CR bytes changed the 100,116-byte
training JSONL. The three other data inputs also changed bytes. This is
**not** evidence of model corruption on GitHub; the underlying immutable Git
blobs matched the prior receipt exactly.

This repair introduces a narrowly scoped `.gitattributes` for model/data
JSON/JSONL, requiring LF checkout on Windows and Linux. The same reviewed
seven asset size+SHA256 commitments now gate both the Python Space startup
and the local Hugging Face release stager. A byte mismatch, modified source
registry, altered KH identifier set, missing receipt or changed training/eval
file is a **HOLD**. Neither tool silently normalizes data at runtime.

SHA-256 proves agreement with the reviewed source contract, not an independent
signature, true archaeology, permission to reuse cultural materials, or
production release admission. Any new training revision requires separately
reviewing the updated source, pin list, weights, data and release controls.

## Fresh, author-generated challenge — negative results must stay visible

A **100-prompt, fixed-before-evaluation**, English diagnostic was run on the
unaltered PR #121 Naive Bayes model using a separate, exactly LF-verified
source checkout. This is **developer-authored** after inspecting the training
source, not an independent or sealed holdout.

| Diagnostic slice | Observed |
| --- | --- |
| Five intents, new natural-language phrasings | **27/50** routed as preassigned |
| Unrelated out-of-scope questions | **17/30** received a non-abstaining route |
| OOD max reported routing score | **0.992704** (NOT calibrated truth probability) |
| Specific unsupported historical-claim prompts | **15/20** routed to limits or abstention |

All responses use the hardcoded curated summaries or an explicit unavailable
answer, and the model reports `truth_qualified=false`; the classifier did not
establish a historical interpretation. **This weak routing quality is a
material hold for broad consumer claims.** The older 76/80 synthetic score
was development-influenced and must not override this evidence.

The unpublished 100-case source prompts were saved in the private owner
evidence directory and hashed **before** querying the model:

`1714e2d9ff3ed619ea65ef2f563ec09bea0df56b52214a1fd863fd620a5cbd74`

This is not evidence of real-world archaeological accuracy or Quechua language
competence, nor a valid estimate of future traffic incidence. It must not be
used to retune the same model then reported as untouched evaluation.

## Forward gates (NOT passed)

1. **No scope expansion:** retain current synthetic training and credited
   archival-ID metadata only. Museum images, article text, detailed khipu
   records and community knowledge require rights/steward review first.
2. **Independent evaluation:** commission a sealed, cross-language and
   source/site-separated benchmark with in-domain, OOD, translation, abstention,
   ambiguity, prompt-injection and rights negative controls. Freeze its grading
   procedure and model/weight hashes before running.
3. **Owner review and source admission:** preserve parallel research PRs
   #118/#119/#120 and require usual sign-off, checks and source readback.
4. **Hugging Face release:** only after an approved write-scope identity,
   explicit targets and expected-parent commits; stage is NOT deployment.
5. **Runtime:** supported Docker base pinned by verified digest, hosted API
   and browser readback, rollback control and independent security review.
6. **Larger LLM:** new rights-cleared corpus, immutable model/tokenizer/base
   revisions, approved GPU budget, measured quality, and separate publication
   approval. The current Nano weights are NOT a 1.5B/large model.

**No production declaration follows from green CI, a model's self-score,
an intact checksum or an attractive visualization.**
