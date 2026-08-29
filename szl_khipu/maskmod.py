# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Score-mod / mask-mod attention silhouettes (causal, sliding, prefix)."""

from __future__ import annotations

from typing import Any

import numpy as np

from .receipt_attn import softmax_rows


def causal_mask(n: int) -> np.ndarray:
    """Keep j <= i (1 = allowed)."""
    n = int(n)
    i = np.arange(n)[:, None]
    j = np.arange(n)[None, :]
    return (j <= i).astype(np.float64)


def sliding_mask(n: int, window: int = 3) -> np.ndarray:
    """Keep j <= i and i - j <= window."""
    n = int(n)
    i = np.arange(n)[:, None]
    j = np.arange(n)[None, :]
    return ((j <= i) & ((i - j) <= int(window))).astype(np.float64)


def prefix_mask(n: int, prefix: int = 4) -> np.ndarray:
    """Causal plus bidirectional prefix: keep j <= i or j < prefix."""
    n = int(n)
    i = np.arange(n)[:, None]
    j = np.arange(n)[None, :]
    return ((j <= i) | (j < int(prefix))).astype(np.float64)


def _mask_for(kind: str, n: int, window: int, prefix: int) -> np.ndarray:
    k = kind.lower()
    if k == "causal":
        return causal_mask(n)
    if k == "sliding":
        return sliding_mask(n, window=window)
    if k == "prefix":
        return prefix_mask(n, prefix=prefix)
    raise ValueError(f"unknown mask kind: {kind}")


def maskmod_attn(
    Q: np.ndarray,
    K: np.ndarray,
    V: np.ndarray,
    kind: str = "causal",
    window: int = 3,
    prefix: int = 4,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Masked scaled-dot-product. Returns (out, probs, future_mass)."""
    Q = np.asarray(Q, dtype=np.float64)
    K = np.asarray(K, dtype=np.float64)
    V = np.asarray(V, dtype=np.float64)
    n, d = Q.shape
    scale = 1.0 / np.sqrt(d)
    scores = (Q @ K.T) * scale
    keep = _mask_for(kind, n, window, prefix) > 0.5
    scores = np.where(keep, scores, -np.inf)
    probs = softmax_rows(scores)
    out = probs @ V
    return out, probs, future_mass(probs)


def future_mass(probs: np.ndarray) -> float:
    """Sum of attention mass on j > i (strictly future tokens)."""
    p = np.asarray(probs, dtype=np.float64)
    n = p.shape[0]
    i = np.arange(n)[:, None]
    j = np.arange(n)[None, :]
    return float(p[j > i].sum())


def maskmod_result(
    Q: np.ndarray,
    K: np.ndarray,
    V: np.ndarray,
    kind: str = "causal",
) -> dict[str, Any]:
    out, probs, fm = maskmod_attn(Q, K, V, kind=kind)
    return {"out": out, "probs": probs, "future_mass": fm, "kind": kind}
