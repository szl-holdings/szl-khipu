# KHIPU-X1 transformer configuration importer v0.1

Status: **CONFIG INSPECTION + ANALYTIC ESTIMATE**  
Full-model lowering: **BLOCKED — REQUIRED DEVICE OPS ARE MISSING**

The importer consumes a caller-supplied Hugging Face-style configuration mapping
without network access, dynamic imports, `trust_remote_code`, model downloads or
weight execution. It validates bounded Llama-like decoder dimensions and emits:

- normalized topology and exact source-config digest;
- an analytic parameter estimate, not a counted weight inventory;
- ideal FP32/BF16/INT8/INT4 payload sizes excluding quantization/runtime overhead;
- BF16 and ideal INT8 KV-cache estimates for an explicit context and batch;
- required, implemented and missing device operations;
- an explicit readiness status;
- optional target-memory worksheet using operator-supplied datasheet values.

The current full decode path fails closed because embedding gather, RoPE,
attention, KV-cache mutation, residual add, gated-MLP elementwise operations and
hardware receipt emission are not implemented in the KHIPU execution reference.
The helper projection probe uses only GEMM_INT8, RMSNORM and SHA3_COMMIT and must
never be represented as a converted transformer.

The target worksheet's full-weight-stream time is an analytic bandwidth lower
bound. It is not a tokens-per-second, latency, power or deployability result.
