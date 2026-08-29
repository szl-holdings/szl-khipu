# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""YARQA-ATTN — irrigation-canal compartment attention.

Softmax is computed ONLY inside canals. Cross-canal scores are hard-zeroed,
not masked-and-softmaxed (which would still leak through the partition function).
"""

from __future__ import annotations

from typing import Any, NamedTuple

import numpy as np


class CanalResult(NamedTuple):
    out: np.ndarray
    probs: np.ndarray
    leaked: float


def canal_bounds(seq: int, n_canals: int) -> np.ndarray:
    """Split `seq` tokens into `n_canals` contiguous canals.

    Remainder goes to the first canals (sizes differ by at most 1).
    Returns endpoints of length n+1, starting at 0 and ending at seq.
    """
    seq = int(seq)
    if seq <= 0:
        return np.array([0], dtype=np.int64)
    n = max(1, min(int(n_canals), seq))
    base, rem = divmod(seq, n)
    sizes = np.full(n, base, dtype=np.int64)
    sizes[:rem] += 1
    return np.concatenate(([0], np.cumsum(sizes)))


def _canal_id(seq: int, bounds: np.ndarray) -> np.ndarray:
    return np.searchsorted(bounds[1:], np.arange(seq), side="right")


def leaked_attn(probs: np.ndarray, bounds: np.ndarray) -> float:
    """Sum of attention mass that sits outside its row's canal. Should be ~0."""
    p = np.asarray(probs, dtype=np.float64)
    s = p.shape[0]
    cid = _canal_id(s, np.asarray(bounds))
    same = cid[:, None] == cid[None, :]
    return float(np.abs(p[~same]).sum())


def yarqa_attn(
    Q: np.ndarray,
    K: np.ndarray,
    V: np.ndarray,
    n_canals: int,
) -> CanalResult:
    """Canal-local scaled-dot-product attention.

    Q, K, V: (S, D)  — V last dim may differ.
    Returns (out, probs, leaked).
    """
    Q = np.asarray(Q, dtype=np.float64)
    K = np.asarray(K, dtype=np.float64)
    V = np.asarray(V, dtype=np.float64)
    if Q.ndim != 2 or K.ndim != 2 or V.ndim != 2:
        raise ValueError("Q, K, V must be rank-2 (S, D)")
    s, d = Q.shape
    if K.shape[0] != s or V.shape[0] != s:
        raise ValueError("Q, K, V must share sequence length")
    if K.shape[1] != d:
        raise ValueError("Q and K must share head dim")
    bounds = canal_bounds(s, n_canals)
    scale = 1.0 / np.sqrt(d)
    scores = (Q @ K.T) * scale
    dv = V.shape[1]
    probs = np.zeros((s, s), dtype=np.float64)
    out = np.zeros((s, dv), dtype=np.float64)
    for c in range(bounds.size - 1):
        a = int(bounds[c])
        b = int(bounds[c + 1])
        if b <= a:
            continue
        block = scores[a:b, a:b]
        m = block.max(axis=1, keepdims=True)
        e = np.exp(block - m)
        z = e.sum(axis=1, keepdims=True)
        z = np.where(z == 0.0, 1.0, z)
        p = e / z
        probs[a:b, a:b] = p
        out[a:b] = p @ V[a:b]
    leaked = leaked_attn(probs, bounds)
    return CanalResult(out=out, probs=probs, leaked=leaked)


def yarqa_result(
    Q: np.ndarray,
    K: np.ndarray,
    V: np.ndarray,
    n_canals: int,
) -> dict[str, Any]:
    out, probs, leaked = yarqa_attn(Q, K, V, n_canals)
    return {
        "out": out,
        "probs": probs,
        "leaked": leaked,
        "bounds": canal_bounds(Q.shape[0], n_canals),
    }
