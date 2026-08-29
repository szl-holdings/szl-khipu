# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Residual-bus reciprocity. F11 silhouette: Σ(out − in − F) = 0.

A silent skip leak cannot pass. Not a ResNet rehost. No ImageNet claim.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def run_ayni(seed: int, leak: int = 0) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    dim = 8
    xin = rng.normal(0, 0.85, size=dim)
    w = rng.normal(0, 0.35, size=(dim, dim))
    bias = (rng.random(dim) - 0.5) * 0.05
    force = np.tanh(w @ xin + bias)
    skip = 0.62 if leak == 1 else 1.0
    xout = xin + skip * force
    residual = xout - xin - force
    return {
        "leak": float(np.max(np.abs(residual))),
        "mass": float(np.abs(residual.sum())),
        "dim": dim,
        "xin": xin.tolist(),
        "force": force.tolist(),
        "xout": xout.tolist(),
        "residual": residual.tolist(),
    }
