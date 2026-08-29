# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""YUYAY Λ-gate: weighted geometric mean, fail-closed, advisory only.

Uniqueness of Λ is Conjecture 1 OPEN. proven_trust is False.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from .doctrine import CONJECTURE_1, YUYAY_AXES, advisory

ArrayLike = Sequence[float] | np.ndarray


class LambdaEval(dict[str, Any]):
    """Dict with attribute access so ev.value and ev['value'] both work."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def _as_vec(x: ArrayLike) -> np.ndarray:
    return np.asarray(x, dtype=np.float64).ravel()


def wgm(x: ArrayLike, w: ArrayLike) -> float:
    """Weighted geometric mean. Any 0 or non-finite axis → 0. Weights must sum to 1."""
    xv = _as_vec(x)
    wv = _as_vec(w)
    if xv.size != wv.size or xv.size == 0:
        return 0.0
    if not np.isfinite(xv).all() or not np.isfinite(wv).all():
        return 0.0
    if np.any(xv <= 0.0) or np.any(wv < 0.0):
        return 0.0
    if abs(float(wv.sum()) - 1.0) >= 1e-9:
        return 0.0
    log = float(np.dot(wv, np.log(xv)))
    v = float(np.exp(log))
    return v if np.isfinite(v) else 0.0


def yuyay_weights() -> np.ndarray:
    n = len(YUYAY_AXES)
    return np.full(n, 1.0 / n, dtype=np.float64)


def uniform_weights(n: int) -> np.ndarray:
    if n <= 0:
        return np.zeros(0, dtype=np.float64)
    return np.full(n, 1.0 / n, dtype=np.float64)


def check_a1(x: ArrayLike, w: ArrayLike) -> bool:
    """A1 monotone: raising one axis cannot decrease Λ."""
    xv = _as_vec(x)
    wv = _as_vec(w)
    base = wgm(xv, wv)
    for i in range(xv.size):
        if xv[i] >= 1.0:
            continue
        y = xv.copy()
        y[i] = min(1.0, float(xv[i]) + 0.05)
        if wgm(y, wv) + 1e-12 < base:
            return False
    return True


def check_a2(x: ArrayLike, w: ArrayLike, c: float = 0.5) -> bool:
    """A2 homogeneous: Λ(c x) = c Λ(x) for c in (0, 1]."""
    xv = _as_vec(x)
    wv = _as_vec(w)
    lhs = wgm(xv * c, wv)
    rhs = c * wgm(xv, wv)
    return abs(lhs - rhs) <= 1e-9 * max(1.0, abs(rhs))


def check_a3(w: ArrayLike, c: float = 0.7) -> bool:
    """A3 Egyptian-exact: Λ(c, …, c) = c."""
    wv = _as_vec(w)
    xv = np.full(wv.size, c, dtype=np.float64)
    return abs(wgm(xv, wv) - c) <= 1e-9


def check_a4(x: ArrayLike, w: ArrayLike) -> bool:
    """A4 bounded by max."""
    xv = _as_vec(x)
    if xv.size == 0:
        return True
    v = wgm(xv, w)
    return v <= float(np.max(xv)) + 1e-12


def check_a5(x: ArrayLike, w: ArrayLike) -> bool:
    """A5 permutation invariance."""
    xv = _as_vec(x)
    wv = _as_vec(w)
    if xv.size < 2:
        return True
    perm = np.arange(xv.size)[::-1]
    return abs(wgm(xv[perm], wv[perm]) - wgm(xv, wv)) <= 1e-9


def evaluate_lambda(x: ArrayLike, w: ArrayLike | None = None) -> LambdaEval:
    xv = _as_vec(x)
    if w is None:
        wv = yuyay_weights() if xv.size == len(YUYAY_AXES) else uniform_weights(int(xv.size))
    else:
        wv = _as_vec(w)
    value = wgm(xv, wv)
    axioms = [
        {"id": "A1", "ok": check_a1(xv, wv), "detail": "monotone"},
        {"id": "A2", "ok": check_a2(xv, wv), "detail": "homogeneous"},
        {"id": "A3", "ok": check_a3(wv), "detail": "Egyptian-exact"},
        {"id": "A4", "ok": check_a4(xv, wv), "detail": "bounded-by-max"},
        {"id": "A5", "ok": check_a5(xv, wv), "detail": "permutation-invariant"},
    ]
    failed = next((a for a in axioms if not a["ok"]), None)
    blocked = value == 0.0 or failed is not None
    if blocked:
        reason = (
            "zero-routed or non-finite axis"
            if value == 0.0
            else f"axiom {failed['id']} failed"  # type: ignore[index]
        )
    else:
        reason = "advisory pass — uniqueness remains Conjecture 1 OPEN"
    return LambdaEval(value=value, blocked=blocked, reason=reason, axioms=axioms)


def lambda_gate(
    axes: ArrayLike,
    threshold: float = 0.5,
) -> LambdaEval:
    """Advisory conjunctive gate. Never claims proven uniqueness."""
    ev = evaluate_lambda(axes)
    score = float(ev["value"])
    passed = (not bool(ev["blocked"])) and score >= threshold
    return LambdaEval(
        score=score,
        passed=passed,
        threshold=float(threshold),
        advisory=True,
        reason=ev["reason"],
        conjecture=CONJECTURE_1,
        proven_trust=False,
        value=score,
        blocked=not passed,
    )


assert advisory is True
