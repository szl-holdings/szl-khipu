# KHIPU-X1 local safetensors inventory v0.1

Status: **LOCAL NON-EXECUTING BYTE VALIDATION**  
Model execution: **NOT PERFORMED**  
Hardware status: **UNAVAILABLE**

The inventory parser reads only local `.safetensors` files and canonical local
index files. It does not download artifacts, import model code, use
`trust_remote_code`, instantiate framework tensors, memory-map untrusted tensor
values, run inference or establish license/model quality.

The implementation was written independently against the public safetensors
format description; no upstream parser source is vendored into this module.

The bounded parser validates:

- unsigned little-endian 64-bit header length;
- UTF-8 JSON object beginning with `{` and unique keys at every object level;
- string-to-string `__metadata__`;
- exact tensor descriptor fields: `dtype`, `shape`, `data_offsets`;
- bounded names, rank, dimensions and parameter product;
- byte-aligned dtype/shape size agreement;
- offsets sorted by byte range, with no overlap, no hole and exact coverage of
  the complete file data buffer;
- offsets against the actual file size;
- optional SHA-256 commitments for the full file and each tensor range;
- safe local shard paths and exact index-to-shard tensor mapping;
- rejection of symbolic-link model roots, shard files, and every intermediate
  directory component in a referenced shard path;
- optional `metadata.total_size` agreement with validated tensor data bytes.

Sub-byte dtypes are explicitly unsupported in v0.1 rather than guessed. A model
inventory reports an exact parameter count from validated header shapes, not a
claim that those bytes implement the architecture declared by `config.json`.
The separate comparison helper keeps exact observed counts and analytic
configuration estimates visibly distinct.

Format reference: <https://github.com/huggingface/safetensors#format>
