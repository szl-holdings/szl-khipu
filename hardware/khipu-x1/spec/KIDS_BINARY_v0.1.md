# KIDS-BIN v0.1 — normative binary command ABI

Status: **SOFTWARE CONFORMANCE REFERENCE**  
Hardware status: **UNAVAILABLE — no FPGA or ASIC implementation is claimed**

KIDS-BIN converts the logical KIDS v0.1 descriptor into a fixed-size,
little-endian command that an eventual FPGA command processor can parse without
JSON. It carries numeric buffer handles, never host pointers or physical
addresses. A separately authenticated runtime/driver will own DMA mappings.

## Descriptor: 192 bytes

| Offset | Bytes | Field |
|---:|---:|---|
| 0 | 4 | ASCII magic `KX1D` |
| 4 | 1 | wire major (`0`) |
| 5 | 1 | wire minor (`1`) |
| 6 | 1 | numeric opcode |
| 7 | 1 | active input count, 0–3 |
| 8 | 2 | flags, little-endian |
| 10 | 2 | header size = `192` |
| 12 | 4 | total descriptor size = `192` |
| 16 | 8 | sequence, uint64 |
| 24 | 8 | nonce, uint64 |
| 32 | 12 | three uint32 input handles; unused = `0xFFFFFFFF` |
| 44 | 4 | uint32 output handle; absent = `0xFFFFFFFF` |
| 48 | 8 | opcode argument 0 |
| 56 | 8 | opcode argument 1 / graph-node tag |
| 64 | 32 | model SHA-256 |
| 96 | 32 | policy SHA-256 |
| 128 | 32 | graph SHA-256 or all zero when unbound |
| 160 | 32 | SHA-256 of bytes 0–159 |

The digest is an integrity check, not authorship. Authorization and device
identity belong to RC1 or another authenticated outer envelope.

## Batch: 128-byte header + N descriptors

| Offset | Bytes | Field |
|---:|---:|---|
| 0 | 4 | ASCII magic `KX1S` |
| 4 | 1 | wire major |
| 5 | 1 | wire minor |
| 6 | 2 | flags; must be zero in v0.1 |
| 8 | 2 | header size = `128` |
| 10 | 2 | descriptor size = `192` |
| 12 | 4 | descriptor count |
| 16 | 8 | first sequence |
| 24 | 8 | last sequence |
| 32 | 8 | first nonce |
| 40 | 8 | last nonce |
| 48 | 32 | SHA-256 of descriptor body |
| 80 | 16 | reserved zero |
| 96 | 32 | SHA-256 of bytes 0–95 |

Sequence and nonce must be strictly increasing. Exactly the final descriptor
sets `LAST_IN_BATCH`.

## Flags

- bit 0 `SCALE_PRESENT`
- bit 1 `EPS_PRESENT`
- bit 2 `GRAPH_BOUND`
- bit 3 `NODE_BOUND`
- bit 4 `LAST_IN_BATCH`
- bits 5–15 reserved zero

## Argument encoding

- `GEMM_INT8`: optional scale is IEEE-754 binary32 in low 32 bits of `arg0`;
  upper 32 bits are zero.
- `RMSNORM`: positive finite epsilon is binary32 in low 32 bits of `arg0`;
  upper 32 bits are zero.
- `ABORT`: uint32 reason code in low 32 bits of `arg0`.
- graph node identity, when present, is the first eight bytes of
  `SHA-256(UTF-8 node id)` interpreted little-endian in `arg1`.

Any unrepresentable attribute, unknown logical flag, reserved opcode, nonzero
reserved field, digest mismatch, malformed arity or aliasing of distinct logical
buffer names fails closed.

## Numeric opcode registry

| Code | Opcode |
|---:|---|
| `0x00` | NOP |
| `0x01` | LOAD (reserved) |
| `0x02` | STORE (reserved) |
| `0x10` | GEMM_INT8 |
| `0x11` | GEMM_BF16 (reserved) |
| `0x20` | RMSNORM |
| `0x21` | ROPE (reserved) |
| `0x30` | ATTN_CAUSAL (reserved) |
| `0x31` | ATTN_YARQA (reserved) |
| `0x40` | KV_GATHER (reserved) |
| `0x41` | KV_SCATTER (reserved) |
| `0x50` | SHA3_COMMIT |
| `0x51` | RECEIPT_EMIT (reserved) |
| `0x60` | BARRIER |
| `0x70` | ZEROIZE (reserved) |
| `0x7F` | ABORT |

Golden vectors under `golden/` are normative for the software reference. A
future RTL parser must reproduce them byte-for-byte and reject the associated
negative vectors before an `FPGA_MEASURED` label is permitted.
