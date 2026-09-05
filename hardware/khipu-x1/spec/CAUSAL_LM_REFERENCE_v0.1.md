# KHIPU-X1 Bounded Causal-LM Reference v0.1

Status: **SOFTWARE_EMULATED / NUMPY ONLY**  
Static mapping status: **LOCAL_STATIC_FULL_MODEL_MAPPING**  
Hardware status: **UNAVAILABLE**  
Energy status: **UNAVAILABLE**  
Tokenizer status: **UNAVAILABLE**

## Purpose

This specification defines the first complete, bounded causal-language-model
software truth surface for KHIPU-X1. It composes exact locally validated
safetensors bytes, explicit architecture configuration, deterministic decoder
operations, final normalization and a language-model head into a complete
forward pass and bounded greedy-generation loop.

It exists to provide a reference that future compiler, runtime, FPGA and ASIC
implementations can be tested against. It is not a production model server and
does not import arbitrary model code.

## End-to-end execution order

```text
integer token IDs
  -> embedding lookup
  -> decoder layer 0
  -> ...
  -> decoder layer N-1
  -> final RMSNorm
  -> tied or untied LM head
  -> logits
  -> deterministic greedy token selection
  -> ordered receipt
```

Each decoder layer is the Wave 6 pre-norm reference:

```text
attention RMSNorm
  -> Q/K/V projections
  -> RoPE
  -> causal GQA/MQA or YARQA attention
  -> output projection
  -> residual add
  -> feed-forward RMSNorm
  -> SwiGLU gated MLP
  -> residual add
```

## Static complete-model mapping

The Wave 8 mapper consumes:

1. a local model directory;
2. a Wave 5 `ModelWeightInventory` containing full-file SHA-256 commitments;
3. an explicit `TransformerSpec` produced from caller-supplied configuration;
4. exact global tensor names and the bounded dense-layer naming profile;
5. explicit limits for layer count, file bytes, tensor bytes and total loaded
   bytes.

It then maps:

- `model.embed_tokens.weight` as `[vocab_size, hidden_size]`;
- every configured dense decoder layer through the Wave 7 exact mapping rules;
- `model.norm.weight` as `[hidden_size]`;
- either `lm_head.weight` from safetensors or an exact transpose of the embedding
  matrix when weight tying is declared.

The mapper never searches for aliases, guesses an architecture, imports model
classes, executes configuration code, downloads weights, or follows symbolic
links. Full-file hashes are reverified before bounded tensor reads.

## Tied and untied LM heads

For an untied model, the source LM-head tensor must have safetensors shape
`[vocab_size, hidden_size]`; it is explicitly transposed into the reference
layout `[hidden_size, vocab_size]`.

For a tied model, a separate LM-head tensor is not required. The reference head
must equal the exact float32 embedding transpose. A mismatch between the
configuration's tying declaration and the supplied weight object fails closed.

## Forward contract

`run_causal_lm` accepts only non-empty rank-2 integer token IDs with shape
`[batch, sequence]`. Every ID must be within the declared vocabulary, and the
sequence must not exceed `max_position_embeddings`.

The function:

- validates every global and layer weight against the explicit configuration;
- performs no tokenizer or chat-template processing;
- executes each configured layer in order;
- requires the receipt depth to advance exactly once per layer;
- applies final RMSNorm and the LM head;
- rejects non-finite logits;
- emits a final `causal_lm_reference_executed` receipt.

The final receipt binds token IDs, hidden state, normalized state, logits,
weight-manifest digest, source-configuration digest, execution mode and explicit
unavailable states.

## Causal and YARQA modes

Causal mode uses the Wave 6 causal GQA/MQA contract.

YARQA mode additionally requires one non-negative canal identifier per sequence
position. Cross-canal probability remains exactly zero in the software
reference. Canal identifiers are explicit inputs and are not inferred from
text, token IDs, metadata or model weights.

## Deterministic greedy selection

`greedy_next_token` selects the maximum logit at the final sequence position.
NumPy's first-maximum behavior is the normative tie break: when several tokens
share the maximum value, the lowest vocabulary index is selected.

No temperature, top-k, top-p, repetition penalty, beam search, random number
generator or speculative-decoding behavior exists in v0.1.

## Bounded generation

`greedy_generate` performs repeated complete forward passes and appends one token
per iteration. The contract:

- requires `max_new_tokens` to be an integer from 1 through 64;
- rejects a prompt plus generation budget beyond `max_position_embeddings`;
- optionally stops when every batch element emits the configured EOS token;
- records the requested budget and actual generated length;
- uses explicit prompt and generated canal state in YARQA mode;
- emits `greedy_generation_completed` after the forward receipts.

This is deliberately a correctness-oriented implementation. It recomputes the
entire sequence on every generation step and does not claim KV-optimized decode,
throughput or latency suitability.

## Receipt and evidence boundary

A successful static mapping emits `safetensors_causal_lm_mapped`. A forward pass
emits one decoder receipt per layer followed by
`causal_lm_reference_executed`. A generation run adds one forward sequence per
new token and then `greedy_generation_completed`.

These receipts establish deterministic ordering and byte/value commitments
inside this software implementation. They do not prove:

- natural-language quality or factual correctness;
- tokenizer or prompt-template identity;
- license rights or model provenance beyond the supplied local commitments;
- security or safety of a model;
- FPGA or ASIC execution;
- measured speed, power, energy or thermal behavior;
- a physical-world action or outcome.

Every hardware and energy field remains explicitly `UNAVAILABLE`.

## Conformance requirements

The Wave 8 tests must establish at least:

- complete tied and untied model mapping;
- exact tied-head derivation from embedding bytes;
- forward output shapes and valid ordered receipts;
- bounded deterministic greedy generation;
- YARQA full-model execution with explicit canal state;
- missing global tensor and excessive layer-count rejection;
- out-of-range token, generation-budget and missing-canal rejection;
- lowest-index argmax tie behavior.

All earlier KHIPU-X1 suites remain part of the integrated acceptance gate.

## Deferred work

Future waves may add:

1. tokenizer vocabulary, special-token and chat-template binding;
2. a KV-cache-optimized complete-model decode path;
3. compilation of complete-model operations to KIDS and KIDS-BIN;
4. deterministic packaging of the mapped model and execution manifest;
5. host runtime queues, device memory planning and DMA contracts;
6. FPGA target selection, RTL parsing, bitstream identity and differential
   measured-device conformance;
7. board-level power measurement and signed measured-energy receipts.

Until each path exists and is observed on the exact target, its status remains
`UNAVAILABLE`.