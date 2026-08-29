# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Governed RMSNorm / LayerNorm. Digest is integrity, not authorship."""

from __future__ import annotations

from typing import Any

import numpy as np

from .chain import canon, sha256_hex


def _last_gamma(x: np.ndarray, gamma: np.ndarray | None) -> np.ndarray:
    d = x.shape[-1]
    if gamma is None:
        return np.ones(d, dtype=np.float64)
    g = np.asarray(gamma, dtype=np.float64).ravel()
    if g.size != d:
        raise ValueError("gamma last-dim mismatch")
    return g


def rms_norm(
    x: np.ndarray,
    gamma: np.ndarray | None = None,
    eps: float = 1e-5,
) -> tuple[np.ndarray, float, str]:
    """Last-dim RMSNorm. Returns (y, unit_rms residual, digest of rounded y)."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = x[None, :]
        squeeze = True
    else:
        squeeze = False
    g = _last_gamma(x, gamma)
    ms = (x * x).mean(axis=-1, keepdims=True)
    r = np.sqrt(ms + float(eps))
    y = (x / r) * g
    denom = np.where(g == 0.0, 1.0, g)
    u = y / denom
    unit = np.sqrt((u * u).mean(axis=-1))
    unit_rms = float(np.max(np.abs(unit - 1.0)))
    if squeeze:
        y_out = y[0]
    else:
        y_out = y
    digest = sha256_hex(canon(np.round(y_out, 5).tolist()))
    return y_out, unit_rms, digest


def layer_norm(
    x: np.ndarray,
    gamma: np.ndarray | None = None,
    beta: np.ndarray | None = None,
    eps: float = 1e-5,
) -> np.ndarray:
    """Optional last-dim LayerNorm."""
    x = np.asarray(x, dtype=np.float64)
    g = _last_gamma(x, gamma)
    mu = x.mean(axis=-1, keepdims=True)
    var = ((x - mu) ** 2).mean(axis=-1, keepdims=True)
    y = (x - mu) / np.sqrt(var + float(eps)) * g
    if beta is not None:
        b = np.asarray(beta, dtype=np.float64).ravel()
        if b.size != x.shape[-1]:
            raise ValueError("beta last-dim mismatch")
        y = y + b
    return y


def rms_result(
    x: np.ndarray,
    gamma: np.ndarray | None = None,
    eps: float = 1e-5,
) -> dict[str, Any]:
    y, unit_rms, digest = rms_norm(x, gamma, eps=eps)
    return {"y": y, "unit_rms": unit_rms, "digest": digest}
