# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""YARQA-ATTN — irrigation-canal compartment attention.

Softmax is computed only inside canals. For nonempty rows this is equivalent
to dense attention with an exact negative-infinity mask outside each canal.

The output-only path uses established block-sparse / IO-aware attention ideas
(Dao et al., https://arxiv.org/abs/2205.14135); it is a NumPy implementation,
not a FlashAttention kernel or a claim of a new attention algorithm.
"""

from __future__ import annotations

import operator
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


def yarqa_attn_output(
    Q: np.ndarray,
    K: np.ndarray,
    V: np.ndarray,
    n_canals: int,
    *,
    query_block_size: int = 64,
) -> np.ndarray:
    """Return canal-local attention without sequence-square intermediates.

    Inputs are rank-2, finite real arrays; Q/K share (S, D), V has (S, Dv).
    The result uses float64, as does :func:`yarqa_attn`. Each query tile sees
    only its canal's keys. Temporary score storage is at most
    ``min(query_block_size, max(1, S // 2)) * ceil(S / n_canals)`` elements.
    The S=1 case copies V without computing scores. Dense diagnostic
    probabilities and measured leakage are available through the old API.

    Unlike the legacy API's clamping, this new API rejects nonintegral or
    nonpositive controls and empty canals. An empty sequence accepts one
    canal and returns shape (0, Dv). This NumPy API has no autograd support.
    """
    controls = []
    for name, value in (("n_canals", n_canals), ("query_block_size", query_block_size)):
        if isinstance(value, (bool, np.bool_)):
            raise ValueError(f"{name} must be a positive integer")
        try:
            value = operator.index(value)
        except TypeError as exc:
            raise ValueError(f"{name} must be a positive integer") from exc
        if value <= 0:
            raise ValueError(f"{name} must be a positive integer")
        controls.append(value)
    n_canals, query_block_size = controls
    inputs = tuple(np.asarray(a) for a in (Q, K, V))
    if any(np.iscomplexobj(a) for a in inputs):
        raise ValueError("Q, K, V must be real-valued arrays")
    Q, K, V = (np.asarray(a, dtype=np.float64) for a in inputs)
    if any(a.ndim != 2 for a in (Q, K, V)):
        raise ValueError("Q, K, V must be rank-2 (S, D)")
    s, d = Q.shape
    if K.shape != Q.shape or V.shape[0] != s:
        raise ValueError("Q/K must share shape and V must share sequence length")
    if d == 0 or V.shape[1] == 0:
        raise ValueError("head and value dimensions must be positive")
    if n_canals > max(s, 1):
        raise ValueError("n_canals must not create empty canals")
    if not all(np.isfinite(a).all() for a in (Q, K, V)):
        raise ValueError("Q, K, V must contain only finite values")
    if s <= 1:
        return V.copy()
    bounds = canal_bounds(s, n_canals)
    rows = min(query_block_size, max(1, s // 2))
    out = np.empty((s, V.shape[1]), dtype=np.float64)
    scale = 1.0 / np.sqrt(d)
    for start, stop in zip(bounds[:-1], bounds[1:]):
        a, b = int(start), int(stop)
        for q_start in range(a, b, rows):
            q_stop = min(q_start + rows, b)
            with np.errstate(over="ignore", invalid="ignore"):
                scores = np.matmul(Q[q_start:q_stop], K[a:b].T)
                scores *= scale
            if not np.isfinite(scores).all():
                raise ValueError("attention scores overflowed float64")
            # Normalize in place: score, exponential, and probability storage
            # are the same tile. No full attention matrix is constructed.
            with np.errstate(over="ignore", under="ignore"):
                scores -= scores.max(axis=1, keepdims=True)
                np.exp(scores, out=scores)
            scores /= scores.sum(axis=1, keepdims=True)
            out[q_start:q_stop] = np.matmul(scores, V[a:b])
    if not np.isfinite(out).all():
        raise ValueError("attention output overflowed float64")
    return out
