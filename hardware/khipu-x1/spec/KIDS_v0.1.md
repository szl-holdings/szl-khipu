# KHIPU Instruction and Descriptor Specification — KIDS v0.1

Status: **DRAFT / SOFTWARE-REFERENCE ONLY**  
Execution class: `SOFTWARE_EMULATED` until a matching FPGA implementation exists.

## Design goals

KIDS is the versioned contract between compiler/runtime, driver, FPGA or ASIC, and the receipt verifier. It is deliberately narrow, deterministic and fail-closed.

## Descriptor logical schema

| Field | Type | Required | Meaning |
|---|---:|:---:|---|
| `version` | string | yes | KIDS schema version; first value `0.1` |
| `sequence` | uint64 | yes | Strictly increasing queue sequence |
| `nonce` | uint64 | yes | Strictly increasing anti-replay value |
| `opcode` | enum | yes | Defined operation |
| `inputs` | array[string] | no | Logical buffer handles |
| `output` | string/null | no | Logical output buffer handle |
| `attrs` | object | yes | Operation-specific validated attributes |
| `model_digest` | hex64 | yes | SHA-256 commitment to model/package identity |
| `policy_digest` | hex64 | yes | SHA-256 commitment to policy/authorization context |
| `flags` | array[string] | no | Optional declared behavior, never silent |

Canonical software encoding is UTF-8 JSON with sorted keys, compact separators and finite numeric values only. Binary hardware encoding is a later KIDS revision and must include a normative byte layout plus golden test vectors.

## v0.1 executable operations

### `NOP`

No data effect. Generates an ordered receipt event.

### `GEMM_INT8`

Inputs: activation matrix `A`, weight matrix `B`. Both are signed INT8. Accumulation is INT32. An optional finite scalar `scale` converts the result to float32. Shape rule: `A[..., K]` and `B[K, N]`.

### `RMSNORM`

Input: finite numeric tensor. Normalize over the final axis using `x / sqrt(mean(x^2) + eps)`. An optional same-width weight vector is permitted. `eps` must be finite and positive.

### `SHA3_COMMIT`

Input: one registered contiguous buffer. Emits a SHA3-256 commitment over dtype, shape and exact C-order bytes.

### `BARRIER`

Ordering point. In the software reference it emits a receipt only.

### `ABORT`

Fails closed and stops the command stream. It never generates a success state.

## Reserved operations

`LOAD`, `STORE`, `GEMM_BF16`, `ROPE`, `ATTN_CAUSAL`, `ATTN_YARQA`, `KV_GATHER`, `KV_SCATTER`, `RECEIPT_EMIT`, `ZEROIZE`.

A reserved operation must return `UNIMPLEMENTED` until an explicitly qualified implementation exists. No transparent CPU fallback may be reported as FPGA execution.

## Required status classes

- `OK`
- `INVALID_DESCRIPTOR`
- `UNSUPPORTED_VERSION`
- `UNIMPLEMENTED`
- `REPLAY_REJECTED`
- `BUFFER_NOT_FOUND`
- `SHAPE_MISMATCH`
- `DTYPE_MISMATCH`
- `NONFINITE_INPUT`
- `TIMEOUT`
- `ABORTED`
- `DEVICE_RESET`
- `ATTESTATION_MISMATCH`
- `INTERNAL_ERROR`

## Receipt event minimum

Each operation event binds:

- KIDS version;
- sequence and nonce;
- opcode and normalized attributes;
- model and policy digests;
- execution path (`software_emulator`, `fpga`, `asic`, or `unavailable`);
- input buffer commitments;
- output commitment when present;
- previous-event digest and current-event digest;
- timing and energy only when obtained from the declared measurement source.

A chain verifies ordering and tamper evidence. It does not prove model accuracy, semantic truth, policy quality or real-world outcome.
