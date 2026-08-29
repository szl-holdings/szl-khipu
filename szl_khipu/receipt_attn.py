# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Tiled online-softmax attention (FlashAttention ALGORITHM, not a CUDA rehost).

No speedup claim. No joule claim. Residual vs naive is the honesty metric.
"""

from __future__ import annotations

from typing import Any, NamedTuple

import numpy as np


class AttnResult(NamedTuple):
    out: np.ndarray
    probs: np.ndarray
    residual: float


def softmax_rows(scores: np.ndarray) -> np.ndarray:
    s = np.asarray(scores, dtype=np.float64)
    finite = np.isfinite(s)
    fill = np.where(finite, s, -np.inf)
    m = np.max(fill, axis=-1, keepdims=True)
    e = np.exp(s - m)
    e = np.where(np.isfinite(e), e, 0.0)
    z = e.sum(axis=-1, keepdims=True)
    z = np.where(z == 0.0, 1.0, z)
    return e / z


def naive_attn(
    Q: np.ndarray,
    K: np.ndarray,
    V: np.ndarray,
) -> AttnResult:
    """Standard scaled-dot-product attention. residual is 0."""
    Q = np.asarray(Q, dtype=np.float64)
    K = np.asarray(K, dtype=np.float64)
    V = np.asarray(V, dtype=np.float64)
    if Q.ndim != 2 or K.ndim != 2 or V.ndim != 2:
        raise ValueError("Q, K, V must be rank-2 (S, D)")
    s, d = Q.shape
    if K.shape != (s, d):
        raise ValueError("Q and K must share shape")
    if V.shape[0] != s:
        raise ValueError("V must share sequence length")
    scale = 1.0 / np.sqrt(d)
    scores = (Q @ K.T) * scale
    probs = softmax_rows(scores)
    out = probs @ V
    return AttnResult(out=out, probs=probs, residual=0.0)


def tiled_attn(
    Q: np.ndarray,
    K: np.ndarray,
    V: np.ndarray,
    br: int = 4,
    bc: int = 4,
) -> AttnResult:
    """Online-softmax tiled attention. Returns (out, probs, residual vs naive)."""
    Q = np.asarray(Q, dtype=np.float64)
    K = np.asarray(K, dtype=np.float64)
    V = np.asarray(V, dtype=np.float64)
    n, d = Q.shape
    dv = V.shape[1]
    scale = 1.0 / np.sqrt(d)
    O = np.zeros((n, dv), dtype=np.float64)
    scores = np.zeros((n, n), dtype=np.float64)
    br = max(1, int(br))
    bc = max(1, int(bc))
    for i0 in range(0, n, br):
        i1 = min(n, i0 + br)
        for qi in range(i0, i1):
            m = -np.inf
            ell = 0.0
            acc = np.zeros(dv, dtype=np.float64)
            for j0 in range(0, n, bc):
                j1 = min(n, j0 + bc)
                s_tile = (Q[qi] @ K[j0:j1].T) * scale
                scores[qi, j0:j1] = s_tile
                m_tile = float(np.max(s_tile)) if s_tile.size else -np.inf
                m_new = m_tile if m == -np.inf else max(m, m_tile)
                alpha = 0.0 if m == -np.inf else float(np.exp(m - m_new))
                acc *= alpha
                ell *= alpha
                p = np.exp(s_tile - m_new)
                ell += float(p.sum())
                acc += p @ V[j0:j1]
                m = m_new
            if ell == 0.0:
                continue
            O[qi] = acc / ell
    out_n, probs, _ = naive_attn(Q, K, V)
    residual = float(np.max(np.abs(O - out_n)))
    return AttnResult(out=O, probs=probs, residual=residual)


def attn_result(
    Q: np.ndarray,
    K: np.ndarray,
    V: np.ndarray,
    tiled: bool = True,
    br: int = 4,
    bc: int = 4,
) -> dict[str, Any]:
    if tiled:
        out, probs, residual = tiled_attn(Q, K, V, br=br, bc=bc)
    else:
        out, probs, residual = naive_attn(Q, K, V)
    return {"out": out, "probs": probs, "residual": residual}
