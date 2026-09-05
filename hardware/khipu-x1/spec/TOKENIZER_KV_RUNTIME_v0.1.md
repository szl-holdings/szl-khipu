# KHIPU-X1 Tokenizer Binding and Functional KV Runtime v0.1

Tokenizer status: **LOCAL_TOKENIZER_ARTIFACT_BINDING**  
Tokenizer execution: **NOT_PERFORMED**  
KV runtime status: **SOFTWARE_EMULATED / NUMPY ONLY**  
Hardware status: **UNAVAILABLE**  
Energy status: **UNAVAILABLE**

## Purpose

Wave 9 closes two software gaps without overstating either one:

1. it binds the exact local tokenizer, special-token and chat-template artifacts
   that surround a model, without executing them; and
2. it adds a functional complete-model prefill and single-token KV-cache decode
   reference, without claiming device execution or performance.

The result is a stronger software truth surface for later KIDS compilation and
FPGA conformance. It is not a production inference server.

## Tokenizer artifact binding

The binder recognizes only a fixed root-level allowlist:

- `tokenizer.json`
- `tokenizer.model`
- `sentencepiece.bpe.model`
- `spiece.model`
- `vocab.json`
- `vocab.txt`
- `merges.txt`
- `tokenizer_config.json`
- `special_tokens_map.json`
- `added_tokens.json`
- `chat_template.jinja`

At least one declared vocabulary source is required. Unknown files are not
silently promoted into the binding contract.

For every recognized artifact, the binder records its path, exact byte count,
SHA-256, media type and vocabulary-source role. It rejects symbolic links,
non-regular files, unstable files, per-file bound violations and aggregate byte
bound violations.

Metadata JSON is decoded as strict UTF-8 with duplicate-key rejection. The
binder records canonical declarations for BOS, EOS, UNK, SEP, PAD, CLS, MASK and
additional special tokens, along with non-negative configured token IDs when
present. Conflicting declarations between `tokenizer_config.json` and
`special_tokens_map.json` fail closed.

Chat templates are commitments only. A template embedded in
`tokenizer_config.json` is hashed as canonical JSON. A `chat_template.jinja`
file is hashed as exact UTF-8 bytes. If both exist, both remain visible; Wave 9
does not choose, render or execute either template.

`verify_tokenizer_binding` repeats the bounded local inventory and rejects any
manifest drift.

## Functional KV state

Each decoder layer is represented by an immutable `LayerKVSnapshot` containing:

- float32 K state;
- float32 V state;
- optional int64 YARQA canal state;
- a SHA3 commitment over the exact arrays.

A `CausalLMKVState` binds:

- every per-layer snapshot commitment;
- batch and sequence lengths;
- maximum sequence length;
- causal or YARQA mode;
- the complete weight-manifest digest;
- source-configuration digest;
- a deterministic state digest;
- the exact receipt-chain head.

Snapshot arrays are returned read-only. Every state use recomputes and checks the
state digest, weight/configuration bindings, shapes, dtypes, finite values,
receipt-chain validity and receipt-head binding.

## Prefill

`prefill_causal_lm` accepts bounded integer token IDs and, for YARQA, one
explicit non-negative canal ID per prompt position. It:

1. validates the complete causal-LM weight contract;
2. performs embedding lookup;
3. executes every decoder layer with a fresh bounded KV cache;
4. snapshots every layer cache;
5. performs final normalization and LM-head projection;
6. emits `causal_lm_kv_prefill_completed` after the layer receipts.

The prefill logits must agree with the complete Wave 8 recomputation path within
the published conformance tolerance.

## Single-token decode

`decode_causal_lm_step` accepts exactly one token per batch item. It validates
the prior state, reconstructs fresh private cache objects from the immutable
snapshots, executes one absolute position through every layer, and returns a new
state. The prior state is not mutated.

In YARQA mode, the new token requires an explicit non-negative canal ID. The
canal state is appended to each layer snapshot and remains part of the state
commitment.

The step emits `causal_lm_kv_decode_step_completed`, binding the prior state
digest, new state digest, token IDs, hidden state, logits, and explicit
unavailable hardware and energy fields.

## Cached greedy generation

`greedy_generate_cached` performs one prefill followed by functional
single-token decode steps. Selection remains deterministic maximum-logit with a
lowest-index tie break. The hard generation ceiling remains 64 tokens, and the
prompt plus requested budget must fit within `max_position_embeddings`.

The final state includes every generated token, including EOS when emitted. A
`causal_lm_cached_generation_completed` receipt binds the final token sequence,
generated suffix, final KV state and decode strategy.

## Failure and mutation boundary

Wave 9 fails closed for, among other cases:

- missing vocabulary artifacts;
- malformed, duplicate-key or conflicting tokenizer metadata;
- tokenizer byte drift after binding;
- symbolic links and resource-bound violations;
- out-of-range token IDs;
- state, weight, configuration or receipt-head mismatch;
- writable, malformed or non-finite KV snapshots;
- decode batches or token counts that do not match state;
- capacity exhaustion;
- missing or invalid YARQA canal state;
- generation budgets outside the explicit limits.

The functional state design copies the receipt chain and reconstructs fresh
cache objects before each step. It is a correctness/isolation mechanism, not a
claim of memory efficiency.

## Evidence boundary

Wave 9 does not:

- tokenize text;
- execute or select a chat template;
- import tokenizer or model code;
- access a network;
- establish semantic equivalence to a third-party tokenizer;
- provide paged KV, continuous batching or production scheduling;
- compile a model to KIDS/KIDS-BIN;
- execute on FPGA or ASIC hardware;
- measure latency, throughput, power, energy or thermals;
- establish model quality, license rights, safety or physical outcomes.

All such states remain explicitly `UNAVAILABLE` or `NOT_PERFORMED`.

## Conformance

The integrated tests establish:

- deterministic tokenizer manifests and successful reverification;
- tamper, duplicate-key, conflict, symlink and resource-bound rejection;
- prefill agreement with full recomputation;
- single-token cached decode agreement with full-sequence recomputation;
- original-state immutability;
- cached greedy token agreement with repeated full recomputation;
- YARQA cached decode agreement and canal-state continuity;
- state-digest, weight-manifest and receipt-head tamper rejection;
- capacity, step-shape, canal and generation-budget rejection.

## Deferred work

The next software waves may implement a specific tokenizer algorithm under an
exact artifact profile, bind rendered prompt tokens to their source artifacts,
lower prefill/decode graphs to KIDS/KIDS-BIN, define device memory and DMA
contracts, and create a host queue emulator. FPGA selection, RTL, bitstream
identity and measured-device conformance remain separate later gates.