# KHIPU-X1 Safetensors Decoder Mapping v0.1

Status: **LOCAL_STATIC_WEIGHT_MAPPING**  
Hardware status: **UNAVAILABLE**  
Energy status: **UNAVAILABLE**

## Purpose

This specification defines the first bounded bridge from exact, locally
validated safetensors bytes into the deterministic KHIPU-X1 NumPy decoder-block
reference. It maps one explicitly selected dense decoder layer. It does not
execute dynamic model code, discover arbitrary architectures, run a full model,
or claim accelerator execution.

## Inputs

The mapper requires all of the following:

1. a local model directory;
2. a `ModelWeightInventory` previously produced by the strict Wave 5 parser;
3. full-file SHA-256 commitments for every referenced shard;
4. an explicit `TransformerSpec` from offline configuration inspection;
5. an in-range decoder-layer index;
6. exact source tensor names, or the bounded `model.layers.N.*` dense naming
   profile;
7. caller-supplied byte ceilings for files, tensors and the total mapped layer.

Any missing or inconsistent input fails closed.

The offline configuration contract preserves the activation as the bounded
`TransformerSpec.hidden_act` field. An absent source field defaults to `silu`;
an invalid identifier or an activation outside the Wave 7 dense-reference
allowlist is rejected rather than inferred from tensor names.

## Supported source dtypes

- `F32`
- `F16`, promoted deterministically to float32
- `BF16`, decoded from little-endian 16-bit words and promoted to float32

Integer, sub-byte, quantized, sparse and unknown weight formats are not mapped
by v0.1. Wave 4 quantization remains a separate software-reference step; this
mapper does not infer or apply a quantization scheme.

## Canonical dense tensor roles

The bounded default profile expects:

```text
model.layers.N.input_layernorm.weight
model.layers.N.self_attn.q_proj.weight
model.layers.N.self_attn.k_proj.weight
model.layers.N.self_attn.v_proj.weight
model.layers.N.self_attn.o_proj.weight
model.layers.N.post_attention_layernorm.weight
model.layers.N.mlp.gate_proj.weight
model.layers.N.mlp.up_proj.weight
model.layers.N.mlp.down_proj.weight
```

Alternative names must be supplied explicitly through
`DecoderLayerTensorNames`; implicit alias search is forbidden.

## Source and reference layouts

Safetensors linear weights are interpreted using the common source layout
`[output_width, input_width]`. The KHIPU-X1 NumPy reference uses
`[input_width, output_width]`. Matrix weights therefore undergo one explicit,
receipted `transpose_2d` transform. Norm vectors use the identity transform.

Expected source shapes are derived only from the explicit `TransformerSpec`:

- attention norm: `[hidden_size]`
- Q projection: `[query_heads * head_dim, hidden_size]`
- K/V projections: `[kv_heads * head_dim, hidden_size]`
- output projection: `[hidden_size, query_heads * head_dim]`
- feed-forward norm: `[hidden_size]`
- gate/up projections: `[intermediate_size, hidden_size]`
- down projection: `[hidden_size, intermediate_size]`

A shape mismatch is an error, not an invitation to guess an architecture.

## Integrity and local-file rules

Before any tensor is materialized, the mapper:

- resolves the caller-supplied root with `strict=True`;
- rejects a symbolic-link root or weight file;
- requires the root basename to match the inventory root;
- resolves each inventory path beneath that exact root;
- verifies current file size against the inventory;
- recomputes and matches the full-file SHA-256;
- checks file identity before and after each bounded range read;
- recomputes each read range SHA-256 and compares it when the inventory contains
  a tensor-range commitment;
- rejects short reads, unsupported dtypes and non-finite values;
- enforces per-file, per-tensor and total materialization limits.

The file hash is reverified by the mapper rather than trusting an earlier
inventory result. This is still local process evidence, not remote attestation
or protection against a privileged hostile operating system.

## Dense reference restrictions

Version 0.1 supports only the bias-free SwiGLU/SiLU dense decoder shape already
implemented by the Wave 6 reference. It rejects:

- attention or MLP bias tensors;
- unsupported activation functions;
- mixture-of-experts layouts;
- missing or duplicate logical tensor names;
- layer indexes outside the inspected configuration;
- architecture inference from tensor names alone.

## Mapping receipt

A successful mapping appends one `safetensors_decoder_layer_mapped` event to a
new SHA3-linked `ReceiptChain`. The event binds:

- inventory and source-config digests;
- model type, layer index and attention mode;
- every exact source tensor name;
- source file, dtype, shape, byte count and full-file SHA-256;
- recomputed tensor-range SHA-256;
- explicit identity or transpose transformation;
- mapped shape and mapped-array commitment;
- the final mapping digest;
- explicit `NOT_PERFORMED` model-code and network states;
- explicit `UNAVAILABLE` hardware and energy states.

The receipt establishes ordered integrity for this software mapping event. It
does not prove model quality, license rights, semantic equivalence, safety,
performance, energy efficiency, FPGA execution, ASIC execution or physical
outcomes.

## Conformance

The Wave 7 tests must establish at least:

- exact source-to-reference matrix transposition;
- successful execution of the mapped layer through the Wave 6 decoder reference;
- full-file commitment requirement;
- post-inventory tamper detection;
- missing-tensor and wrong-shape rejection;
- unsupported-dtype and byte-ceiling rejection;
- layer-range, bias, activation and duplicate-name rejection.

## Deferred work

The following remain future waves:

- embedding, final norm and tied/untied LM-head mapping;
- bounded mapping of every layer in a complete small model;
- tokenizer and chat-template binding;
- logits and deterministic sampling;
- graph compilation to KIDS/KIDS-BIN;
- device memory planning and DMA;
- FPGA target selection, RTL, bitstream generation and measured conformance.

Until those paths exist and are observed, full-model and hardware status remain
`UNAVAILABLE`.