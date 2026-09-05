# KHIPU-X1 symmetric INT8 quantization v0.1

Status: **SOFTWARE REFERENCE**  
Hardware status: **UNAVAILABLE**

The reference quantizer accepts finite numeric NumPy tensors and emits signed
INT8 values in `[-127, 127]` with zero point 0. Scale is derived by absolute
maximum either for the whole tensor or independently for every index along one
declared axis. All-zero ranges use scale 1.0 and are counted explicitly.

Evidence includes source, quantized-value and scale commitments; MSE and maximum
absolute reconstruction error; endpoint and zero-range counts; axis, shapes,
dtypes and rounding rule. These are measurements of the supplied tensor only.
They are not model-quality, task-accuracy, speed, energy or FPGA claims.

Determinism contract:

- source calculation uses float32;
- rounding uses NumPy `rint` (nearest, ties to even);
- scale payloads are explicit little-endian float32;
- quantized payload is C-order INT8;
- metadata is canonical sorted UTF-8 JSON;
- payload hashes bind dtype, shape and bytes.

The `.payloads(name)` helper creates bounded `.khipu` payload entries but does
not publish, execute or promote them.
