# KHIPU-X1 Transformer Reference v0.1

Status: **SOFTWARE-REFERENCE / NUMPY ONLY**  
Hardware status: **UNAVAILABLE**  
Energy status: **UNAVAILABLE**

## Purpose

This specification defines the deterministic software truth surface used to
validate future KHIPU-X1 compiler, runtime, FPGA and ASIC implementations. It
implements one bounded pre-norm decoder block and its supporting operations. It
is not a complete language-model runtime and does not load arbitrary model code.

## Canonical tensor shapes

- hidden state: `[batch, sequence, hidden_size]`
- query: `[batch, query_heads, sequence, head_dim]`
- key/value: `[batch, kv_heads, sequence, head_dim]`
- attention probabilities: `[batch, query_heads, query_sequence, key_sequence]`
- projection matrices use `[input_width, output_width]`

The contract requires:

`query_heads * head_dim == hidden_size`

and:

`query_heads % kv_heads == 0`

This permits multi-head attention, grouped-query attention and multi-query
attention under one explicit shape contract.

## Implemented operations

1. bounded embedding lookup with integer token IDs;
2. learned RMSNorm over the final axis;
3. pairwise rotary position embeddings with configurable theta and rotary width;
4. numerically stable causal GQA/MQA attention;
5. YARQA canal-isolated causal attention;
6. a bounded in-memory KV cache for incremental reference decoding;
7. SwiGLU gated MLP;
8. one pre-norm decoder block with residual connections;
9. SHA3-linked receipt emission for each decoder-block execution.

## Decoder-block order

```text
hidden
  -> attention RMSNorm
  -> Q/K/V projections
  -> RoPE(Q, K)
  -> causal GQA/MQA or YARQA attention
  -> output projection
  -> residual add
  -> feed-forward RMSNorm
  -> SwiGLU(gate, up, down)
  -> residual add
  -> execution receipt
```

Biases, dropout, speculative decoding, tensor parallelism, mixture-of-experts,
sliding-window attention, logits, token sampling and tokenizer behavior are not
part of v0.1.

## Causal and YARQA semantics

For causal mode, a query at absolute position `p` may attend only to keys whose
absolute position is less than or equal to `p`.

For YARQA mode, the causal rule remains active and an additional partition rule
applies: a query may attend only to keys carrying the same non-negative canal
identifier. A cross-canal probability must be exactly zero in the software
reference. Missing canal IDs, negative IDs or changing a cache between canal and
non-canal modes fail closed.

## KV-cache contract

The v0.1 cache is a bounded NumPy reference buffer. It:

- fixes batch count, KV-head count, maximum sequence length and head dimension
  at construction;
- accepts only matching finite rank-4 K/V tensors;
- rejects capacity overflow;
- rejects switching canal mode after the first append;
- returns copies rather than exposing mutable internal storage;
- exposes a commitment over K, V and optional canal state.

It is not a DMA allocator, paged-KV implementation, device memory manager or
performance model.

## Position contract

Positions must be non-negative integers, contiguous, and aligned with the cache
length. For a cache of length `n`, a submitted segment of length `m` must carry
positions `[n, n+1, ..., n+m-1]`. This removes implicit position inference from
the reference path.

## Execution receipt

Each successful decoder block appends a `transformer_decoder_block_executed`
event to the caller-supplied or newly created `ReceiptChain`. The event binds:

- execution path and truth class;
- attention mode and declared dimensions;
- submitted position range;
- cache length before and after execution;
- commitments for input, Q, new K, new V, attention probabilities, attention
  output and final output;
- explicit `energy_j: null`, `energy_status: UNAVAILABLE`, and
  `hardware_status: UNAVAILABLE`.

The receipt proves ordering and integrity within this implementation. It does
not prove model quality, semantic correctness, safety, authorship, hardware
execution, energy efficiency or a physical-world outcome.

## Determinism and conformance

Given identical NumPy version, inputs, weights, configuration and ordered cache
state, the implementation must produce stable float32 outputs within the
conformance tolerances. Tests must establish at least:

- bounded embedding behavior;
- RoPE position-zero identity and pair-norm preservation;
- no future-value influence on earlier causal positions;
- no cross-canal influence under YARQA;
- incremental-cache output agreement with full causal execution;
- fail-closed invalid head ratios and cache overflow.

## Future hardware mapping

A future accelerator implementation may use fused or lower-precision datapaths,
but it must publish the exact numeric contract, tolerance, bitstream identity,
measurement environment and differential results against this reference.
Until that evidence exists, only `SOFTWARE_EMULATED` is permitted.