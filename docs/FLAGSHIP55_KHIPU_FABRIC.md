# Flagship55 / Khipu: three-specialist learning fabric (design only)

**Status:** PROPOSED / source-indexed research. **Observed:** 2026-11-17 UTC.
**Owner:** SZL Holdings. **Canonical Khipu source:** `szl-holdings/szl-khipu`.
**This document launches no training, downloads no weights, admits no datasets, changes no controllers, and makes no model-quality claim.**

## Objective and honest physical topology

Build one Flagship55 student with three internal, *separately versioned specialist adapter roles*:
(1) **YACHAY / Teacher** provides source-grounded explanations, proof plans and
curated corrections; (2) **WILLAY / Guide** proposes doctrine-aligned plans and
recognizes insufficient authority; (3) **KHIPU / Skeptic** challenges statements,
requests counterexamples, estimates abstention risk and assembles evidence requests.

A fourth component, the **deterministic referee**, is **not a neural model**:
the trusted Lean checker, provenance validator and external governance gate issue
the final proof/admission verdict. A learned skeptic can ask for checks but cannot
declare a conjecture proved or override a failed control.

A full teacher model is normally a **frozen, separate training-time model**.
Its teaching may be distilled into the YACHAY specialist; it is not literally
contained inside the student by virtue of training on its outputs. The three
specialists may become independent, compatible LoRA adapters behind a router on
one *pinned* backbone, provided compatibility and baseline evaluation pass.
Alternatively sidecar models require separately measured VRAM/latency/licensing.
A diagram with three boxes is **not** three trained models or a deployed MoE.
The current manifest marks all three roles `PROPOSED`, with no weights.

```
versioned first-party sources / licensed datasets / pinned research
          |               [no raw private rows on public surfaces]
          v
source-and-rights index (Khipu graph; immutable revisions; withheld items)
          |
  reviewed examples + blind heldout + verifier-replayed proof terms
          |                  [external deterministic referee]
          v
frozen mentor observations -> teacher distillation [separate stage/receipt]
          |
          v
    Flagship55 student (candidate)
       |        |         |
    YACHAY    WILLAY    KHIPU  <- three proposed specialist LoRA roles
       \        |        /
       bounded routing, explicit fallbacks
          |
 deterministic policy & Lean/evidence authority [no model veto override]
          |
answer / uncertainty / proof object + source-citation knot + honest status
```

## Binding and evidence baseline

The prior Flagship54 adapter is **not automatically Flagship55 weights**.
`SZLHOLDINGS/salad-flagship54-v1@92da3f1e3fcc2f190c0198bdb33ff1d734294e17`
has a pinned 37,000/37,000 trainer state and a source-verified owner-laptop
11-file checkpoint (287,883,513 bytes), independently read back 2026-11-17
06:35:59 UTC. Five final-export objects (118,733,024 bytes) match corresponding
checkpoint objects. This establishes **artifact integrity**, NOT evaluated
quality, independently observed Salad shutdown, training success certification,
hosting, or production qualification. Flagship55 must be compared with both
the exact original base and this frozen adapter; do not assume continuation wins.

The original adapter cites
`SZLHOLDINGS/SZL-Nemotron-Mini-4B-Estate-v1`, PEFT 0.21.2, rank 32,
alpha 64, attention q/k/v/o projections and a saved chat template. Base weights,
tokenizer, model license and adapter compatibility need their own immutable
bindings. **No silent backbone swap, adapter averaging or LoRA merger.**

## Khipu's math: source-bound distinctions, not all-as-truth

The mathematical authority is
[`lutar-lean@bcfc25badcd73d6b6f013853c1fb8bf384b2e460`](https://github.com/szl-holdings/lutar-lean/tree/bcfc25badcd73d6b6f013853c1fb8bf384b2e460)
and its `claims/locked-formulas.v1.json`; Khipu's software doctrine is
`szl_khipu/doctrine.py`. Preserve exact theorem statements, hypotheses,
toolchain, axiom disclosures and compiled-vs-proposed provenance.

- **Locked set exactly eight:** F1, F4, F7, F11, F12, F18, F19, F22.
  This is a specific Lean *surface*, not a blanket proof of Khipu runtime,
  networking, cryptography, economics, the nonlinear Kuramoto system or physics.
  F4 is a backward-edge Nat-DAG property; F7 is in-memory list order;
  F18 is shard-count arithmetic, not a Reed-Solomon implementation.
- **Λ, A1–A5:** the advisory weighted-geometric-mean and named axioms.
  Under A1–A5 **unconditional uniqueness is false as stated**, with a
  documented `maxAgg_ne_Lambda` counterexample; older `Conjecture 1 OPEN`
  labels must not be mistaken for evidence that its bare form might be true.
  Conditional uniqueness results require their extra assumptions. Λ is **not**
  calibrated correctness probability, a proof, or an authorization to act.
- **Other formulas:** CONDITIONAL / AXIOM / EXPERIMENTAL / OPEN / REFUTED /
  MEASURED / HISTORICAL each retain their exact label and source. A `sorry`
  is not solved by having the same theorem name in a training set.
- **Evidence-meet rule:** mandatory gates are conjunctive and noncompensatory.
  A good model score cannot compensate for missing source, rights, independent
  proof replay, privacy controls or holdout binding. Existing security and
  production owners retain authority.

## Dataset and research census: include in the index, not indiscriminately in gradients

Read-only official Hub SDK dataset inventory on 2026-11-17 07:09:41 UTC returned
**136** accessible `SZLHOLDINGS` dataset identities below a cap of **501**
(91 public, 45 private; 20 with no license tag). Pagination was handled by the
SDK. This is *accessible provider metadata coverage*, not a proof of every
external, archived, private-on-disk or otherwise undiscoverable research corpus.
The detailed census stays under owner-only `SZL-private-evidence`; no private
asset identities or rows are copied into this public repository.

The [public reference index](../research/flagship55/public_dataset_index.v1.json)
now carries all **91 public** identities returned by that bounded census, each
with its observed immutable Hub revision and explicit `REFERENCE_ONLY` state.
The separate design manifest still has **13 selected public examples** for
strict initial packet admission. No private identities or dataset contents enter
the public index. This is not a complete Khipu corpus ingestion; external,
archived, inaccessible and unapproved research remain outside coverage.
Only independently reviewed slices can enter gradients. In particular:

| Kind | Default use | Promotion gate |
| --- | --- | --- |
| Lean declaration, counterexample, failed proof, open conjecture | Context/retrieval with exact truth label | No `PROVED` reinterpretation; proof term needs independent kernel replay |
| Human-owned math research with licensed content | Retrieval/context | Exact revision, rights, privacy, evaluation exclusion and author review |
| Candidate SFT/GRPO datasets | DISCOVERED_ONLY | Dataset bytes and license, provenance, semantic dedup, decontamination, split and model budget |
| Biomedical / lab records / private Brain graph | EXCLUDED_FROM_GRADIENTS by default | Specific permissions and research governance; no ambient graph-to-training path |
| Benchmark, eval battery, heldout questions, receipts | EVALUATION_ONLY or EVIDENCE_ONLY | Never train on evaluated labels |
| Unlicensed, gated, restricted or unknown-use assets | BLOCKED for training | Source-by-source rights and consent review |
| Open public math datasets already indexed | REFERENCE_ONLY | Public visibility or Apache tag is not training clearance |

The catalog snapshot does **not** assert that any of 136 datasets is approved.
Known first-party starting points include pinned public datasets for Lean,
axioms, ancient mathematics, formulas and invariants; `szl-quant-sft-v1` is
**explicitly blocked by the existing training BOM despite its license tag**.
Other license or privacy holds must be preserved. Do not copy external scientific
papers or third-party datasets wholesale into model weights; use citations and
per-source licensing. A full index must also reconcile Github repositories,
model cards, Massed nodes, lab data agreements and authorized owners.

## Curriculum, experts and falsifiable evaluation

Retain the [Forge Flagship55 proposal](https://github.com/szl-holdings/szl-forge/blob/6a62d9c212b79696c9a1b70556d575b423091966/docs/frontier-20261115/flagship55-run-manifest-v0.md)
as an **unapproved candidate**. Its 70/20/5/5 mixture is not a training decision;
do not substitute this expanded graph for the owner-pinned manifest.

1. **Source induction:** preserve provenance, language, cultural attribution and
   claim type; independently replay allowed Lean proofs in a credential-free
   isolated process. Untrusted Lean code is executable code, not safe data.
2. **Student SFT baseline:** compare frozen original base vs Flagship54 vs
   controlled Flagship55 candidates on source-disjoint datasets and unmodified
   tokenizer. Never choose hyperparameters on the blind final test.
3. **Teaching:** compare source-grounded SFT traces with a frozen teacher's
   distilled corrections; each teacher output is advisory until checked.
4. **Three expert ablations:** no experts / YACHAY only / WILLAY only / KHIPU
   skeptic only / all three. Measure router errors, latency, VRAM, calibration
   and heldout accuracy. Prefer adapter routing over multi-model serving only
   if hardware, license and tests demonstrate improvement.
5. **Optional verifier-reward RL:** bounded GRPO only after reward hacking,
   axiom smuggling, invalid Lean, data contamination, prompt injection, false
   abstention and over-abstention negative controls pass. A source compile
   verdict is not independent proof replay or deploy permission.
6. **Release:** bind dataset, base, adapters, tokenizer, inference image,
   evaluation version, source snapshot and hardware measurement to one run.
   `TRAINING`, `ARTIFACT_VERIFIED`, `EVALUATED`, `DEPLOYED` and `QUALIFIED`
   are separate gates, with independent owner review.

For abstention, publish risk with **coverage** and sample counts. When the
retained-answer denominator is zero, report `UNAVAILABLE`, not zero-risk.
Report separate slices for *answerable*, *insufficient evidence*,
*contradictory*, *refuted conjecture* and *open problem*. Record baselines,
CIs, fixed benchmark revisions, prompt variants, languages and negative controls.
Don't publish a headline pass rate from training token accuracy.

## Relevant open research (methods to test, not transitive SZL results)

- [DeepSeek-Prover-V2](https://github.com/deepseek-ai/DeepSeek-Prover-V2):
  decompose mathematical subgoals, formalize in Lean, verify before RL.
- [AlphaProof](https://www.nature.com/articles/s41586-025-09833-y):
  Lean proof environment and search; study the method without claiming their
  private training implementation is open.
- [TRL DistillationTrainer](https://huggingface.co/docs/trl/distillation_trainer):
  frozen teacher -> student token distribution; version pin required.
- [MoLoRA (ICML 2026)](https://proceedings.mlr.press/v306/shah26d.html):
  per-token specialist adapters; implementation/license/runtime parity require
  separate inspection before adopting.
- [MOPD-Router (2026)](https://arxiv.org/abs/2609.30837):
  token-level multi-teacher supervision, research-only for now.
- [DataTrove](https://github.com/huggingface/datatrove):
  deduplication / filtering; still requires semantic contamination checks.
- [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai),
  [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness):
  independent, source-bound evaluation harness candidates.

## Exact owners / gates

- **Khipu** owns this metadata-only architecture and mathematical provenance
  reference. It creates no second inference controller, evaluation writer,
  trainer, receipt signer or Salt/Salad shutdown owner.
- **`lutar-lean`** owns theorem statements, proof statuses and Lean.
- **`szl-forge`** owns training recipes, curriculum admission and quality
  evaluation. **`szl-gpu-bridge`** owns provider/GPU integrations and the
  existing Flagship54 guard. **`szl-second-brain`** and Anatomy retain
  data-access/lineage boundaries; no private graph enters gradients.
- No new paid jobs/replicas, hyperparameter changes, budgets, checkpoint
  deletion, credential rotation, security changes, model publications or runtime
  claims are authorized by this document.
- A signed receipt needs a real signing authority: SHA-256 alone proves neither
  authorship nor third-party validation.

**Next gates:** verify independent Flagship54 shutdown + a real matched,
heldout evaluation; complete per-source rights/identity and privacy
reconciliation; verify teacher/guide/skeptic training data and baselines;
obtain owner-pinned recipe, compute decision and required reviews before any
Flagship55 training launch.

## Executable CPU research boundary — November 17, 2026

The stdlib-only [`triad_packet.py`](../research/flagship55/triad_packet.py)
creates a **deterministic review packet**, not model outputs. It binds the
previously reviewed Flagship55 manifest's *canonical JSON* SHA-256,
an allowlisted F1/F4/F7/F11/F12/F18/F19/F22 reference (or the refuted-as-stated
F23), and exact SHA-pinned public dataset handles. It assigns YACHAY, WILLAY and
KHIPU *tasks* while marking every specialist **NOT EXECUTED / NO COMPATIBLE
WEIGHTS**. The independent Lean and policy referees are explicitly **NOT RUN**.
Unknown claims, moving revisions, raw prompts, blocked datasets, or unlisted
fields fail before any output or mutation. Its SHA-256 packet digest is not
a signature, proof, source permission or completed evaluation.

The public metadata catalog has 91 items: all returned public Hub dataset
identities at the recorded snapshot, but no actual dataset rows or private
identity. The 13 selected public examples in `manifest.v0.json` remain the
**only** initially permitted reference handles for this packet. A license tag
does not establish content rights or allow a data path into gradients.
`public_catalog.py` verifies the no-authority, revision and count contracts.

For a bounded example from the repository root:

```sh
python -m research.flagship55.triad_packet \
  --manifest research/flagship55/manifest.v0.json \
  --request research/flagship55/example-triad-request.json
python -m unittest discover -s tests -p "test_flagship55_*" -v
```

The separate `synthetic_risk_coverage()` function counts answered, incorrect
and abstained synthetic developer-labeled examples by answerable, insufficient
evidence, contradictory, refuted-as-stated and open-problem slices. It makes
the zero-answered risk **null/UNAVAILABLE** rather than an invented zero.
It does not choose a threshold, measure Flagship54, assess actual model
generations or qualify Flagship55.

**Related active research HOLD:** `research/khipu_yachay/experiments/open_set_r1`
is a genuinely trained CPU classifier, but its published diagnostics show
intent/generalization regressions. This proposal does not promote that router,
reuse its viewed evaluation results as a heldout benchmark, or imply it is a
Flagship55 teacher. Any subsequent teacher or three-adapter experiments require
their own pinned weights, data-rights admission, independent evaluation and
budget/owner approval. Flagship54 training shutdown remains solely with the
existing guard.
