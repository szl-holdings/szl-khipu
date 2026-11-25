<!-- SPDX-License-Identifier: Apache-2.0
(c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173 -->

# Global frontier transfer study: China, Ireland, South Korea

Status: **MODELED**. This directory holds a literature study and three stdlib
reference sketches with offline tests. It contains no measured SZL result, no
ledger format, no admission gate and no model call. Λ stays Conjecture 1; the
locked formula count stays 8.

Every mechanism below is another group's published work and is cited as prior
art. Figures quoted from a vendor are that vendor's own published figures and
are not SZL results.

## How the sources were read (2026-11-24)

- arXiv, w3.org, terminusdb.com and verl.readthedocs.io were not reachable from
  the session that did this study. Paper bodies were read through the Hugging
  Face paper pages (`huggingface.co/papers/<id>`), model cards and GitHub. The
  arXiv URLs are listed as the canonical source but were not fetched directly.
- Pages were read through a summarising fetch tool, so equations here are a
  paraphrase of the page text. **Check each against the PDF before pinning a
  golden vector to it.**
- **UNVERIFIED** marks anything that could not be confirmed on a fetched page.

## 1. DeepSeek (China)

Source: DeepSeek-V3 report, arXiv 2412.19437; DeepSeek-R1, arXiv 2501.12948.

- **Auxiliary-loss-free load balancing.** A per-expert bias `b_i` is added to
  the affinity score only for top-K selection; the gating value still uses the
  unbiased score. After each step `b_i` falls by γ for an overloaded expert and
  rises by γ for an underloaded one (γ = 0.001, later 0).
- **Sequence-wise balance loss.** `L_Bal = α Σ_i f_i P_i`, α = 0.0001.
- **Multi-head latent attention.** Keys and values are rebuilt from a compressed
  latent (`d_c = 512`) plus a decoupled RoPE key; only those two are cached.
- **Multi-token prediction.** Sequential auxiliary modules sharing the embedding
  and output head, weighted λ = 0.3 then 0.1, dropped at inference.
- **FP8 mixed precision.** The Linear operator's three GEMMs run in FP8 with
  per-tile and per-block scaling and partial sums promoted to FP32 every 128
  elements; master weights stay FP32.
- **R1 pipeline.** GRPO with rule-based accuracy and format rewards, then
  rejection-sampled SFT, then a final RL stage.

Licence: V3 code MIT, V3 weights under a separate Model License; R1 code and
weights MIT. Vendor figures (DeepSeek's, not ours): 671B total / 37B active
parameters, 14.8T tokens, 2.788M H800 GPU-hours, all benchmark tables.

## 2. ByteDance Seed: verl / HybridFlow (China)

Source: arXiv 2409.19256; `volcengine/verl` docs.

- **Hybrid controller.** One single-process controller owns the RL control flow
  and inter-model data transfer; each model's distributed computation runs
  multi-controller.
- **WorkerGroup transfer protocols.** `@register(dispatch_mode=...)` binds a
  worker method to a distribute/collect pair; the controller makes one call.
- **ResourcePool.** Colocated models run sequentially; separate pools run
  asynchronously.
- **3D-HybridEngine.** Training and generation parallel groups are arranged so
  weights overlap per device (the authors report zero parameter redundancy).
- **Fault handling.** The paper calls itself orthogonal to fault-tolerance work
  and says it incorporates checkpointing of parameters, dataloader IDs and RNG
  state. Repo config exposes `trainer.resume_mode`, `save_freq`, `save_contents`.
  **UNVERIFIED:** no per-step retry or exactly-once re-execution is documented.

Licence: Apache-2.0. Vendor figures (the HybridFlow authors'): throughput gains
of 1.53× to 20.57× against three named baselines on 128 A100-80GB GPUs.

## 3. TerminusDB (Ireland)

Source: `terminusdb/terminusdb` and `terminusdb/terminusdb-store` on GitHub.

- **Layer stack.** A database is a stack of immutable layers; each stores
  additions and removals over its parent.
- **Label as mutable head.** `set_head` succeeds only if the new layer descends
  from the current head and the label version matches (compare-and-swap).
  `force_set_head` skips the ancestry check.
- **Squash versus rollup.** `squash` builds a new base and discards history;
  `rollup` builds an equivalent combined layer and keeps history readable.
- **Branch API.** `/squash`, `/reset`, `/rebase` (with a per-commit report).
- **JSON diff and patch.** `SwapValue` with `@before`/`@after`, `Insert`,
  `Delete`; `match_final_state`; conflicts return 409 with typed witnesses.
- **Time travel.** Query the state at any historical commit.

**UNVERIFIED:** the "content-addressed" description of layers and the internal
succinct structures. Licence: Apache-2.0 for both repositories.

## 4. ADAPT Centre (Ireland)

- **DPV** (`w3c/dpv`, v2.3): an RDFS/SKOS vocabulary for purposes, data
  categories, processing, measures, legal bases and risk, with AI and EU AI Act
  extensions. Part of the editing work was funded through the ADAPT SFI Centre.
- **AIRO** (`DelaramGlp/airo`): an OWL ontology published by ADAPT Centre,
  Trinity College Dublin, with `AISystem`, `Risk`, `RiskControl`,
  `hasResidualRisk` and related terms, plus SHACL and SPARQL rules.
- **AI Cards** (arXiv 2406.18211): **UNVERIFIED** beyond search summaries.
- **W3C PROV:** **UNVERIFIED** in this study (w3.org unreachable). The fetched
  AIRO file has no PROV references, so PROV is not attributed to ADAPT here.

Licence: DPV under the W3C Document License; AIRO CC BY 4.0.

## 5. LG AI Research EXAONE (South Korea)

Source: EXAONE 4.0, arXiv 2507.11407; EXAONE Deep, arXiv 2503.12524; model cards.

- **Hybrid modes.** Reasoning and non-reasoning data trained jointly at a 1.5:1
  token ratio; the authors report that a higher ratio made the model reason
  when non-reasoning mode was requested.
- **AGAPO RL.** No PPO clip, all-incorrect groups kept with a small negative
  advantage, leave-one-out group advantage, sequence-level KL penalty.
- **Hybrid reward.** Verifiable, preference, language-consistency and
  conciseness terms.
- **KoMT-Bench.** MT-Bench in Korean with a square-root score penalty for
  non-Korean responses.

Licence: weights under the EXAONE AI Model License (non-commercial), so they are
reference-only for SZL. KoMT-Bench LGPL-3.0. All model-card tables are LG AI
Research's figures.

## 6. Upstage (South Korea)

Source: SOLAR 10.7B, arXiv 2312.15166; Dataverse; Evalverse; `upstage/dp-bench`.

- **Depth up-scaling.** Duplicate a 32-layer base, drop the last 8 layers of one
  copy and the first 8 of the other, concatenate to 48, then continue training.
- **Dataverse.** Config-driven Spark ETL with a registry of blocks.
- **Evalverse.** Submodule wrappers over existing evaluation harnesses.
- **Document-parse metrics.** `NID = 1 − indel / (len(ref) + len(pred))`;
  `TEDS = 1 − EditDist(Ta, Tb) / max(|Ta|, |Tb|)`.

Licence: Dataverse and Evalverse Apache-2.0 (both archived 2024-10-21);
SOLAR-10.7B-v1.0 Apache-2.0, the Instruct variant CC-BY-NC-4.0; dp-bench MIT.
H6 scores and the dp-bench leaderboard are Upstage's figures.

## Candidate adaptations

Each row is a design idea, not a result. "Test in this PR" means a sketch and an
offline test exist in `transfer.py` and `tests/test_global_frontier_transfer.py`.
A passing sketch test shows the idea is internally consistent; it does not show
it works on the real Khipu ledger or on SaladCloud.

| # | Idea | Prior art | Promotion test | State |
|---|------|-----------|----------------|-------|
| 1 | Receipt-ledger branches as immutable delta layers | terminusdb-store layers | Replay reproduces the head and state; any changed layer changes the head or breaks the chain | Test in this PR |
| 2 | Head pointer that only advances to a descendant, with no force path | `set_head` ancestry check + version CAS | Sibling, ancestor, unknown and stale-version moves return false and leave the head unchanged | Test in this PR |
| 3 | Rollup for query speed that keeps originals verifiable | rollup vs squash | Rollup state equals full replay; original chain still verifies | ROADMAP |
| 4 | Ledger diff/patch with conflict witnesses | `/diff`, `/patch`, `match_final_state` | `patch(a, diff(a, b)) == b`; a `@before` mismatch yields a witness and is never applied | ROADMAP |
| 5 | Bias-only dispatcher for preemptible workers | DeepSeek-V3 `b_i ± γ` on selection only | Seeded skewed simulation: load variance below the no-bias baseline; recorded score always the unbiased affinity | Test in this PR |
| 6 | Controller/worker recovery with step-indexed commits | verl controller + checkpoint; exactly-once is SZL's own addition | Kill a simulated worker mid-step; step commits once; final digest equals an uninterrupted seeded run | ROADMAP |
| 7 | Fixed-interval precision promotion check | FP8 with 128-element accumulation | Golden vector: chunked promotion error within a pinned bound against float64 | ROADMAP |
| 8 | Mode-leak and language-consistency probe set (Korean, English, Chinese, Irish) | EXAONE 4.0 modes, KoMT-Bench penalty, R1 format reward | Rule-based scorer returns pinned scores on stored pass/fail fixtures; live-model output stays SAMPLE | ROADMAP |
| 9 | NID / TEDS-S scorer | dp-bench formulas | Identical text 1.0, disjoint text 0.0, one hand-computed table case | ROADMAP |
| 10 | DPV/AIRO-typed receipt annotations | DPV v2.3, AIRO | Unknown terms rejected offline; annotations never change the admit computation | ROADMAP |

Limits of the three sketches:

- Layer names are a SHA3-256 of a canonical JSON body. This is not the Khipu
  receipt format, carries no DSSE envelope and no signature.
- `Branch` is in-memory and single-process; the version check is not a
  distributed compare-and-swap.
- `dispatch` is a simulation over supplied affinities. No SaladCloud node was
  contacted and no scheduling improvement is claimed for real workloads.

## Run

```bash
python -m pytest tests/test_global_frontier_transfer.py -q
```

## Sources

- <https://arxiv.org/abs/2412.19437> (read via <https://huggingface.co/papers/2412.19437>)
- <https://arxiv.org/abs/2501.12948> (read via <https://huggingface.co/papers/2501.12948>)
- <https://github.com/deepseek-ai/DeepSeek-V3>
- <https://github.com/deepseek-ai/DeepSeek-R1>
- <https://arxiv.org/abs/2409.19256> (read via <https://huggingface.co/papers/2409.19256>)
- <https://github.com/volcengine/verl>
- <https://github.com/terminusdb/terminusdb>
- <https://github.com/terminusdb/terminusdb-store>
- <https://github.com/w3c/dpv>
- <https://github.com/DelaramGlp/airo>
- <https://arxiv.org/abs/2406.18211> (search-result confirmation only)
- <https://github.com/LG-AI-EXAONE/KoMT-Bench>
- <https://arxiv.org/abs/2507.11407> (read via <https://huggingface.co/papers/2507.11407>)
- <https://huggingface.co/LGAI-EXAONE/EXAONE-4.0-32B>
- <https://huggingface.co/LGAI-EXAONE/EXAONE-Deep-32B>
- <https://arxiv.org/abs/2312.15166> (read via <https://huggingface.co/papers/2312.15166>)
- <https://github.com/UpstageAI/dataverse>
- <https://github.com/UpstageAI/evalverse>
- <https://huggingface.co/datasets/upstage/dp-bench>
