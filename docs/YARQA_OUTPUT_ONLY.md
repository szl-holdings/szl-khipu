# YARQA output-only CPU attention

`yarqa_attn_output(Q, K, V, n_canals, query_block_size=64)` computes the same
canal-local attention output as `yarqa_attn` on valid finite inputs, while
avoiding full sequence-square score and probability matrices. The existing
`yarqa_attn` diagnostic API still returns its output, probabilities, and leakage.

```python
from szl_khipu import yarqa_attn_output

output = yarqa_attn_output(q, k, v, n_canals=4)
```

The new API uses NumPy float64. It processes query tiles against only the keys
within their canal, normalizing each score tile in place. The tile row count is
capped at half the sequence length so even a one-canal call avoids a full square
score tensor. A singleton sequence returns a copy of V. An empty sequence with
one canal returns an empty output. Nonpositive/nonintegral controls, empty
canals, invalid shapes, complex or non-finite inputs, and score overflow are rejected.
The legacy API's clamping behavior is retained in that API.

This follows established [block-sparse / IO-aware attention ideas from
FlashAttention](https://arxiv.org/abs/2205.14135) and the
[mask-based formulation supported by FlexAttention](https://arxiv.org/abs/2412.05496).
No upstream implementation was copied. Exact negative-infinity masking outside
nonempty canals is mathematically equivalent to computing softmax inside each
canal; the tests verify this against a dense reference. This change does not
introduce a new attention algorithm or a GPU kernel.

The temporary score tile has at most
`min(query_block_size, max(1, S // 2), ceil(S/C)) * ceil(S/C)` elements.
Input conversion and the S-by-Dv output use separate storage. Full diagnostic
probabilities still require quadratic output storage. NumPy autograd is not
supported; finite-difference sensitivity parity is tested without claiming a
backward kernel.

## Reproduce the CPU comparison

Run from this checkout with NumPy installed:

```powershell
python -B benchmarks/yarqa_cpu.py --out benchmarks/results/yarqa-cpu-local.json
```

The default run uses S=256/1024/4096, D=64, 1/4/16 canals, three seeds, three
warmups, and eleven interleaved timed samples per method. It compares the legacy
diagnostic call, an exact dense masked output-only reference, and the block-local
output-only path. The output-only reference is the primary timing comparison;
the legacy call also pays for probabilities and leakage diagnostics.

The JSON binds the source commit, implementation and benchmark file hashes,
input hashes, CPU/software information, requested BLAS thread controls, raw
timings, p50/p95, and numerical error. Correctness failure stops the run before a
successful receipt is written. Existing output files are never overwritten.

Memory has two explicit labels: `traced_peak_allocation_bytes` is a separate
`tracemalloc` observation and may omit native BLAS allocations; the largest score
tensor byte count is analytically derived. Neither is called measured process
peak RSS. Input allocations precede the traced measurement. GPU, measured energy,
independent witnessing, and autograd remain unmeasured or unsupported. The JSON
digest verifies content integrity, not the truth or independence of measurements.

Report all measured shapes, including slowdowns. This code makes no speedup
claim before a run, and a CPU comparison does not establish GPU performance,
model quality, deployment readiness, or an overall estate promotion.

## Retained local measurement, September 19, 2026

The [complete 27-case CPU receipt](../benchmarks/results/yarqa-cpu-2026-09-19.json)
is retained without editing its observations. It measures source commit
`0e56e9a8451294e462160d64819add10e03f5dde`; both measured files still match
that commit byte-for-byte after the additive integration of current main.
Its canonical body digest is
`300283554146b09a6b4b7ecf8abd5d24a6c1491ae82e5b60694d3e4e5f61338d`.

All 27 cases passed numerical parity against the dense masked reference.
This run used **one warmup and three timed samples**, not the stronger default
protocol above. It requested one BLAS thread, on a Windows CPU, for all three
sequence lengths, canal counts, and seeds. It was not independently witnessed.

The per-case dense-output p50 divided by block-output p50 ranged from 0.770 to
59.554. The block path was **slower** at S=1024, C=1, seed=42 (ratio 0.770);
the largest ratio occurred at S=4096, C=16, seed=7. These are observations of
this short, locally noisy run, not guaranteed speedups, confidence intervals,
or a hardware-comparable performance claim. Every raw sample is included.

Regression tests verify the retained digest, measured file hashes, complete
case coverage, raw timing percentiles, and the reported slowdown. They check
the retained record and current implementation binding; they do not rerun all
27 timings, independently attest measurements, or convert the historical run
into a current-date benchmark. GPU, energy, process peak RSS, autograd,
model-quality impact, and deployment readiness remain unmeasured.
