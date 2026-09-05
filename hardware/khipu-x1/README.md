# KHIPU-X1

**FPGA-first governed LLM accelerator software reference.**

This directory is the software truth surface and future hardware workspace for
KHIPU-X1. It is not a fabricated chip and does not claim performance
superiority, measured energy, FPGA execution or ASIC execution.

## Implemented

### Wave 1 — execution reference

- KIDS v0.1 logical descriptors;
- deterministic NumPy simulator;
- INT8 GEMM, RMSNorm and SHA3 commitments;
- ordered SHA3-256 execution-receipt chains;
- fail-closed replay, reserved-opcode and abort handling;
- explicit rejection of false `fpga` / `asic` execution paths.

### Wave 2 — software control plane

- deterministic graph IR and shape/dtype checked lowering to KIDS descriptors;
- safe deterministic `.khipu` package builder/verifier with no extraction;
- RC1 one-shot authorization-boundary emulator;
- exact cross-repository source lock for the observed design inputs;
- adversarial tests for package traversal/duplicates, signature tampering,
  replay, non-ACT mode and unavailable physical actuation.

### Wave 3 — hardware-facing wire ABI

- fixed 192-byte little-endian KIDS-BIN command descriptor;
- fixed 128-byte batch header with per-descriptor, body and header digests;
- stable numeric opcode registry and explicit reserved fields;
- numeric buffer handles only — no host pointers or physical addresses;
- deterministic positive and negative golden vectors;
- strict rejection of tampering, reserved bits, alias ambiguity, reordering and
  logical fields that cannot be represented without loss.

### Wave 4 — quantization and transformer readiness

- deterministic symmetric INT8 quantization, per tensor or per declared axis;
- exact source/value/scale commitments and measured reconstruction error;
- strict offline inspection of caller-supplied Hugging Face-style configs;
- analytic parameter, ideal weight-memory and KV-cache estimates;
- explicit required/implemented/missing operation report for causal or YARQA
  attention;
- target memory/bandwidth worksheet labeled as operator/datasheet input, not a
  measured accelerator result;
- fail-closed full-model status while embedding, RoPE, attention, KV, residual,
  gated-MLP and hardware receipt operations remain missing.

### Wave 5 — bounded safetensors inventory

- non-executing inspection of canonical local `model.safetensors` or indexed
  sharded models;
- exact header-derived tensor, parameter, dtype and byte inventories;
- optional whole-file and tensor-range SHA-256 commitments;
- strict unique-key UTF-8 JSON, header-padding, offset, no-hole, no-overlap and
  complete-buffer validation;
- exact index `weight_map` to shard-content reconciliation;
- path traversal, symbolic-link, ambiguous-root, duplicate-tensor and unsupported
  sub-byte-dtype rejection;
- deterministic comparison of exact header counts with the independent analytic
  transformer estimate;
- no framework tensor construction, dynamic model code, weight execution,
  quality judgment, license judgment or hardware-compatibility claim.

## Quick start

```bash
cd hardware/khipu-x1
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest -q
python tools/generate_wire_golden.py --check
```

## Truth labels

- `SCAFFOLDED`: interface or design document exists.
- `SOFTWARE_EMULATED`: reference code executed on CPU.
- `PACKAGE_VERIFIED_ONLY`: container commitments verified; model not executed.
- `LOCAL_NON_EXECUTING_BYTE_VALIDATION`: local bytes and layout were inspected;
  weights were not executed.
- `FPGA_MEASURED`: permitted only after exact device/bitstream testing.
- `BLOCKED`: attempted path was refused with evidence.
- `UNAVAILABLE`: capability does not exist or was not measured.

Current hardware status: **UNAVAILABLE — target FPGA not selected**.  
RC1 status: **EMULATOR ONLY — no GPIO or physical actuation**.  
Package status: **integrity verifier only — not a model-quality or license claim**.  
Wire ABI status: **software conformance only — no hardware parser exists**.  
Quantization status: **software reference measurements on supplied tensors**.  
Transformer status: **configuration inspection, not model conversion or execution**.  
Safetensors status: **local non-executing byte validation, not model execution**.

## Program boundary

This is for one owner prototype. No production tooling, mass-production order or
ASIC tapeout is authorized by this directory.

## Next waves

1. implement embedding, RoPE, Q/K/V, GQA/MQA attention, KV-cache, residual and
   gated-MLP software-reference operations;
2. add deterministic model-to-reference mapping from validated inventory and
   caller-supplied architecture configuration;
3. select an FPGA target and freeze its memory/bandwidth/thermal contract;
4. prototype the host runtime queue and RTL command parser;
5. prove parser safety properties and run measured-device conformance.
