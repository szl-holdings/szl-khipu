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

It maps the embedding, every configured dense decoder layer, final norm, and a
tied or untied LM head. The mapper never searches for aliases, guesses an
architecture, imports model classes, executes configuration code, downloads
weights, or follows symbolic links. Full-file hashes are reverified before
bounded tensor reads.

## Tied and untied LM heads

For an untied model, the source LM-head tensor must have safetensors shape
`[vocab_size, hidden_size]`; it is explicitly transposed into the reference
layout `[hidden_size, vocab_size]`. Global source names must be unique.

For a tied model, a separate LM-head tensor is not required. The reference head
must equal the exact float32 embedding transpose. A mismatch between the
configuration's tying declaration and the supplied weight object fails closed.

## Forward contract

`run_causal_lm` accepts only non-empty rank-2 integer token IDs with shape
`[batch, sequence]`. Every ID must be within the declared vocabulary, and the
sequence must not exceed `max_position_embeddings`.

The function validates every global and layer weight, performs no tokenizer or
chat-template processing, executes each configured layer in order, applies final
RMSNorm and the LM head, rejects non-finite logits, and emits a final
`causal_lm_reference_executed` receipt after the per-layer receipts.

## Causal and YARQA modes

Causal mode uses the Wave 6 causal GQA/MQA contract.

YARQA mode additionally requires one non-negative canal identifier per sequence
position. Cross-canal probability remains exactly zero in the underlying
software reference. Canal identifiers are explicit inputs and are not inferred
from text, token IDs, metadata or model weights.

## Deterministic greedy selection

`greedy_next_token` selects the maximum logit at the final sequence position.
NumPy's first-maximum behavior is normative: when several tokens share the
maximum value, the lowest vocabulary index is selected.

No temperature, top-k, top-p, repetition penalty, beam search, random number
generator or speculative-decoding behavior exists in v0.1.

## Bounded generation

`greedy_generate` performs repeated complete forward passes and appends one token
per iteration. It requires `max_new_tokens` from 1 through 64, rejects a prompt
plus generation budget beyond `max_position_embeddings`, optionally stops when
every batch element emits EOS, and emits `greedy_generation_completed`.

This is deliberately correctness-oriented. It recomputes the entire sequence on
every generation step and does not claim KV-optimized decode, throughput or
latency suitability.

## Receipt and evidence boundary

A successful static mapping emits `safetensors_causal_lm_mapped`. A forward pass
emits one decoder receipt per layer followed by
`causal_lm_reference_executed`. A generation run adds one forward sequence per
new token and then `greedy_generation_completed`.

These receipts establish deterministic ordering and byte/value commitments
inside this software implementation. They do not prove natural-language
quality, factual correctness, tokenizer identity, license rights, model safety,
FPGA or ASIC execution, measured speed, measured energy or a physical-world
outcome. Hardware and energy remain explicitly `UNAVAILABLE`.

## Conformance requirements

The Wave 8 tests establish:

- complete tied and untied model mapping;
- exact tied-head derivation from embedding bytes;
- forward output shapes and valid ordered receipts;
- bounded deterministic greedy generation;
- YARQA complete-model execution with explicit canal state;
- missing global tensor, duplicate global name and excessive layer-count
  rejection;
- out-of-range token, generation-budget and missing-canal rejection;
- lowest-index argmax tie behavior.

All earlier KHIPU-X1 suites remain part of the integrated acceptance gate.

## Deferred work

Future waves may add tokenizer vocabulary, special-token and chat-template
binding; a KV-cache-optimized full-model decode path; complete-model lowering to
KIDS/KIDS-BIN; deterministic model packaging; device memory and DMA contracts;
FPGA target selection and RTL; and signed board-level energy measurements.
Until each path exists and is observed on the exact target, its status remains
`UNAVAILABLE`.