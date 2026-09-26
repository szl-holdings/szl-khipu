#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reproducible CPU comparison; execute from any cwd, with no Hub access."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import tracemalloc
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def source_binding():
    def git(*args):
        return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()

    files = ("szl_khipu/yarqa.py", "benchmarks/yarqa_cpu.py")
    return {
        "source_revision": git("rev-parse", "HEAD"),
        "source_files_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files
        },
        "tracked_worktree_dirty": bool(git("diff", "--name-only", "HEAD")),
    }


def run(args):
    # Import after thread controls have been applied in main, before NumPy/BLAS
    # initialization. These are requested controls, not observed thread counts.
    import numpy as np

    sys.path.insert(0, str(ROOT))
    from szl_khipu.yarqa import canal_bounds, yarqa_attn, yarqa_attn_output

    def dense_masked(q, k, v, canals):
        bounds = canal_bounds(len(q), canals)
        ids = np.searchsorted(bounds[1:], np.arange(len(q)), side="right")
        scores = q @ k.T / np.sqrt(q.shape[1])
        scores[ids[:, None] != ids[None, :]] = -np.inf
        weights = np.exp(scores - scores.max(axis=1, keepdims=True))
        weights /= weights.sum(axis=1, keepdims=True)
        return weights @ v

    blas_info = io.StringIO()
    with contextlib.redirect_stdout(blas_info):
        np.show_config()
    report = {
        "schema": "szl.yarqa-cpu-benchmark/v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "observation": "LOCAL_MEASUREMENT",
        "integrity": "SHA256_ONLY_NOT_A_SIGNATURE",
        **source_binding(),
        "hardware": {"system": platform.system(), "release": platform.release(),
                     "machine": platform.machine(), "processor": platform.processor(),
                     "logical_cpus": os.cpu_count(), "gpu": "NOT_EXERCISED"},
        "software": {"python": platform.python_version(), "numpy": np.__version__,
                     "numpy_config": blas_info.getvalue()},
        "thread_controls_requested": {
            name: os.environ[name] for name in
            ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")
        },
        "protocol": {"warmup": args.warmup, "samples": args.samples,
                     "dtype": "float64", "query_block_size": args.query_block_size,
                     "rtol": 1e-12, "atol": 1e-12,
                     "timing": "perf_counter_ns; interleaved method order; no tracing",
                     "memory": "separate tracemalloc run; traced allocation proxy only; "
                               "excludes inputs allocated before tracing and may omit BLAS/native allocations",
                     "peak_process_memory_bytes": None,
                     "energy_joules": None, "autograd": "NOT_SUPPORTED_NUMPY_API",
                     "comparability": "legacy returns dense probabilities and leakage diagnostics; "
                                      "dense_masked_output and block_local_output return outputs only"},
        "cases": [],
    }
    for size in args.seq:
        for canals in args.canals:
            if canals > size:
                raise ValueError("benchmark canal count cannot exceed sequence length")
            for seed in args.seeds:
                rng = np.random.default_rng(seed)
                q, k, v = (rng.normal(0, 0.5, size=(size, args.dim)) for _ in range(3))
                input_hash = hashlib.sha256()
                input_hash.update(canonical({"shape": q.shape, "dtype": "<f8"}).encode())
                for array in (q, k, v):
                    input_hash.update(array.astype("<f8", copy=False).tobytes(order="C"))
                reference = dense_masked(q, k, v, canals)
                methods = {
                    "legacy_diagnostics": lambda: yarqa_attn(q, k, v, canals),
                    "dense_masked_output": lambda: dense_masked(q, k, v, canals),
                    "block_local_output": lambda: yarqa_attn_output(
                        q, k, v, canals, query_block_size=args.query_block_size),
                }
                row = {"sequence": size, "head_dim": args.dim, "value_dim": args.dim,
                       "canals": canals, "seed": seed, "input_sha256": input_hash.hexdigest(),
                       "methods": {}}
                for name, method in methods.items():
                    observed = method()
                    actual = observed.out if name == "legacy_diagnostics" else observed
                    passed = bool(np.allclose(actual, reference, rtol=1e-12, atol=1e-12))
                    row["methods"][name] = {
                        "correctness_parity_pass": passed,
                        "max_abs_error": float(np.max(np.abs(actual - reference))),
                        "samples_us": [],
                    }
                    if not passed:
                        raise RuntimeError(f"parity failed for {name}: S={size}, C={canals}")
                    del observed, actual
                    for _ in range(args.warmup):
                        method()
                    tracemalloc.start()
                    observed = method()
                    _, peak = tracemalloc.get_traced_memory()
                    tracemalloc.stop()
                    del observed
                    row["methods"][name]["traced_peak_allocation_bytes"] = peak
                    largest_canal = math.ceil(size / canals)
                    score_rows = min(args.query_block_size, max(1, size // 2), largest_canal)
                    row["methods"][name]["largest_score_tensor_bytes_derived"] = (
                        (0 if size == 1 else score_rows * largest_canal) * 8
                        if name == "block_local_output" else size * size * 8
                    )
                names = list(methods)
                for sample in range(args.samples):
                    order = names[sample % len(names):] + names[:sample % len(names)]
                    for name in order:
                        started = time.perf_counter_ns()
                        observed = methods[name]()
                        elapsed_us = (time.perf_counter_ns() - started) / 1000
                        row["methods"][name]["samples_us"].append(elapsed_us)
                        del observed
                for metrics in row["methods"].values():
                    metrics["p50_us"] = float(np.percentile(metrics["samples_us"], 50))
                    metrics["p95_us"] = float(np.percentile(metrics["samples_us"], 95))
                report["cases"].append(row)
                print(f"S={size} C={canals} seed={seed} parity=PASS", file=sys.stderr)
    report["receipt_sha256"] = hashlib.sha256(canonical(report).encode()).hexdigest()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seq", type=int, nargs="+", default=[256, 1024, 4096])
    parser.add_argument("--canals", type=int, nargs="+", default=[1, 4, 16])
    parser.add_argument("--seeds", type=int, nargs="+", default=[7, 17, 42])
    parser.add_argument("--dim", type=int, default=64)
    parser.add_argument("--query-block-size", type=int, default=64)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--samples", type=int, default=11)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if min(*args.seq, *args.canals, args.dim, args.query_block_size, args.threads) < 1:
        parser.error("shape, canals, tile size, and thread controls must be positive")
    if args.samples < 3 or args.warmup < 0:
        parser.error("samples must be >=3 and warmup >=0")
    if max(args.seq) > 8192:
        parser.error("this bounded CPU benchmark supports sequences up to 8192")
    if args.out.exists():
        parser.error("output already exists; select a new receipt path")
    for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[name] = str(args.threads)
    report = run(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"saved {args.out}; receipt_sha256={report['receipt_sha256']}")


if __name__ == "__main__":
    main()
