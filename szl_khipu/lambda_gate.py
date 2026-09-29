# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""YUYAY Λ-gate: weighted geometric mean, fail-closed, advisory only.

Inputs follow szl.lambda/v1 (szl-holdings/szl-lambda-gate ``spec/szl.lambda.v1.json``;
golden vectors pinned in ``tests/fixtures/lambda_v1_vectors.SOURCE``):

* axes and weights are 1-D sequences (or numpy arrays) of real numbers, of equal,
  non-zero length; ``bool``, strings and other non-numbers are rejected;
* every axis is finite and 0 <= x <= 1; nothing is clamped;
* every weight is finite and w > 0; |fsum(w) - 1| <= 1e-12; nothing is renormalised.

``wgm`` is total: it never raises, and it returns 0.0 (the veto) for a zero axis and for
every input v1 rejects, so it never returns a value above 1. ``evaluate_lambda`` and
``lambda_gate`` report the v1 ``code`` that fired, so a veto and a rejected input can be
told apart.

Uniqueness of Λ is Conjecture 1 OPEN. proven_trust is False.
"""

from __future__ import annotations

import math
import numbers
from collections.abc import Sequence
from typing import Any

import numpy as np

from .doctrine import CONJECTURE_1, YUYAY_AXES, advisory

ArrayLike = Sequence[float] | np.ndarray

#: szl.lambda/v1 constants (spec/szl.lambda.v1.json in szl-lambda-gate).
V1_SCHEMA = "szl.lambda/v1"
WEIGHT_SUM_TOL = 1e-12
TIE_EPS = 1e-9

LAMBDA_TYPE_INVALID = "LAMBDA_TYPE_INVALID"
LAMBDA_EMPTY = "LAMBDA_EMPTY"
LAMBDA_LENGTH_MISMATCH = "LAMBDA_LENGTH_MISMATCH"
LAMBDA_NONFINITE_AXIS = "LAMBDA_NONFINITE_AXIS"
LAMBDA_AXIS_OUT_OF_RANGE = "LAMBDA_AXIS_OUT_OF_RANGE"
LAMBDA_NONFINITE_WEIGHT = "LAMBDA_NONFINITE_WEIGHT"
LAMBDA_WEIGHT_NONPOSITIVE = "LAMBDA_WEIGHT_NONPOSITIVE"
LAMBDA_WEIGHT_SUM = "LAMBDA_WEIGHT_SUM"
LAMBDA_TAU_INVALID = "LAMBDA_TAU_INVALID"

GO = "GO"
NO_GO = "NO_GO"
ABSTAIN = "ABSTAIN"
BLOCK = "BLOCK"

ZERO_VETO = "ZERO_VETO"
BELOW_TAU = "BELOW_TAU"
NUMERIC_TIE = "NUMERIC_TIE"

_PASS_REASON = "advisory pass — uniqueness remains Conjecture 1 OPEN"


class LambdaEval(dict[str, Any]):
    """Dict with attribute access so ev.value and ev['value'] both work."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


class _V1Rejected(Exception):
    """An input outside szl.lambda/v1. Internal: callers see a code, never this."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _as_vec(x: ArrayLike) -> np.ndarray:
    return np.asarray(x, dtype=np.float64).ravel()


def _is_real(value: Any) -> bool:
    return isinstance(value, numbers.Real) and not isinstance(value, (bool, np.bool_))


def _is_finite(value: Any) -> bool:
    # Rationals (int, numpy ints, Fraction) are finite however large; only floats can be NaN/Inf.
    return isinstance(value, numbers.Rational) or math.isfinite(value)


def _elements(value: Any, name: str) -> list[Any]:
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            raise _V1Rejected(LAMBDA_TYPE_INVALID, f"{name} is a 0-d array, not a vector")
        return value.ravel().tolist()
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise _V1Rejected(LAMBDA_TYPE_INVALID, f"{name} is {type(value).__name__}, not a sequence")
    try:
        return list(value)
    except (TypeError, ValueError, IndexError) as exc:
        raise _V1Rejected(LAMBDA_TYPE_INVALID, f"{name} could not be read: {type(exc).__name__}") from None


def _v1_vectors(x: Any, w: Any) -> tuple[np.ndarray, np.ndarray]:
    """Validate (x, w) against szl.lambda/v1 and return them as float64 vectors.

    Checks run in phases, each over every element, so the reported code does not depend
    on axis order: TYPE (container) > EMPTY > LENGTH_MISMATCH > TYPE (element) >
    NONFINITE_AXIS > AXIS_OUT_OF_RANGE > NONFINITE_WEIGHT > WEIGHT_NONPOSITIVE > WEIGHT_SUM.
    """
    xs = _elements(x, "axes")
    ws = _elements(w, "weights")
    if not xs or not ws:
        raise _V1Rejected(LAMBDA_EMPTY, f"len(axes)={len(xs)}, len(weights)={len(ws)}")
    if len(xs) != len(ws):
        raise _V1Rejected(LAMBDA_LENGTH_MISMATCH, f"len(axes)={len(xs)} != len(weights)={len(ws)}")
    for name, seq in (("axes", xs), ("weights", ws)):
        for i, v in enumerate(seq):
            if not _is_real(v):
                raise _V1Rejected(LAMBDA_TYPE_INVALID, f"{name}[{i}] is {type(v).__name__}, not a real number")
    for i, v in enumerate(xs):
        if not _is_finite(v):
            raise _V1Rejected(LAMBDA_NONFINITE_AXIS, f"axes[{i}] is not finite")
    for i, v in enumerate(xs):
        if not 0 <= v <= 1:
            raise _V1Rejected(LAMBDA_AXIS_OUT_OF_RANGE, f"axes[{i}] is outside [0, 1]")
    for i, v in enumerate(ws):
        if not _is_finite(v):
            raise _V1Rejected(LAMBDA_NONFINITE_WEIGHT, f"weights[{i}] is not finite")
    for i, v in enumerate(ws):
        if not v > 0:
            raise _V1Rejected(LAMBDA_WEIGHT_NONPOSITIVE, f"weights[{i}] is not > 0")
    try:
        total = math.fsum(ws)
    except OverflowError:
        raise _V1Rejected(LAMBDA_WEIGHT_SUM, "the sum of weights overflows a float") from None
    if not abs(total - 1.0) <= WEIGHT_SUM_TOL:
        raise _V1Rejected(LAMBDA_WEIGHT_SUM, f"sum of weights is not within {WEIGHT_SUM_TOL:g} of 1")
    return (
        np.array([float(v) for v in xs], dtype=np.float64),
        np.array([float(v) for v in ws], dtype=np.float64),
    )


def _log_lambda(xv: np.ndarray, wv: np.ndarray) -> float:
    """log Λ for validated vectors; -inf when some axis is 0 (the veto)."""
    if np.any(xv == 0.0):
        return -math.inf
    return float(np.dot(wv, np.log(xv)))


def _from_log(log_lam: float) -> float:
    # log Λ <= 0 for validated input, so Λ is in [0, 1].
    return 0.0 if log_lam == -math.inf else math.exp(log_lam)


def wgm(x: ArrayLike, w: ArrayLike) -> float:
    """Weighted geometric mean Λ_w(x) in [0, 1]. Total: never raises.

    Returns 0.0 (the veto) for a zero axis and for every input szl.lambda/v1 rejects:
    NaN/±Inf, an axis outside [0, 1], a weight <= 0, |Σw − 1| > 1e-12, a length
    mismatch, empty input or a non-number. The 0.0 does not say which; use
    ``evaluate_lambda`` or ``lambda_gate`` for the v1 code.
    """
    try:
        xv, wv = _v1_vectors(x, w)
    except _V1Rejected:
        return 0.0
    return _from_log(_log_lambda(xv, wv))


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
    """Joint (x, w) reversal leaves Λ unchanged.

    This holds by construction for any weighted sum, so it is an implementation
    self-check, not Lean A5. Lean A5 (IsPermutationInvariant) permutes x alone under
    equal weights, and unequal weights violate it. evaluate_lambda reports Lean A5 as
    NOT_CHECKED.
    """
    xv = _as_vec(x)
    wv = _as_vec(w)
    if xv.size < 2:
        return True
    perm = np.arange(xv.size)[::-1]
    return abs(wgm(xv[perm], wv[perm]) - wgm(xv, wv)) <= 1e-9


def _default_weights(x: Any) -> Any:
    try:
        n = len(_elements(x, "axes"))
    except _V1Rejected:
        return ()  # validation then reports the axes fault, which is checked first
    return yuyay_weights() if n == len(YUYAY_AXES) else uniform_weights(n)


def _evaluate(x: ArrayLike, w: ArrayLike | None) -> tuple[LambdaEval, float]:
    """(evaluation, log Λ). log Λ is NaN when the input is rejected."""
    try:
        xv, wv = _v1_vectors(x, _default_weights(x) if w is None else w)
    except _V1Rejected as rej:
        rejected = LambdaEval(
            value=0.0,
            blocked=True,
            code=rej.code,
            reason=f"{V1_SCHEMA} {rej.code}: {rej.detail}",
            axioms=[],
        )
        return rejected, math.nan
    log_lam = _log_lambda(xv, wv)
    value = _from_log(log_lam)
    axioms = [
        {"id": "A1", "ok": check_a1(xv, wv), "detail": "monotone"},
        {"id": "A2", "ok": check_a2(xv, wv), "detail": "homogeneous"},
        {"id": "A3", "ok": check_a3(wv), "detail": "Egyptian-exact"},
        {"id": "A4", "ok": check_a4(xv, wv), "detail": "bounded-by-max"},
        {
            "id": "A5",
            "ok": check_a5(xv, wv),
            "state": "NOT_CHECKED",
            "detail": "NOT_CHECKED: Lean A5 symmetry; ran only a joint (x, w) reversal, true by construction",
        },
    ]
    failed = next((a for a in axioms if not a["ok"]), None)
    code: str | None
    if value == 0.0:
        code = ZERO_VETO
        reason = "zero-routed axis (ZERO_VETO): a veto, not an error"
    elif failed is not None:
        code = f"AXIOM_{failed['id']}_FAILED"
        reason = f"axiom {failed['id']} failed"
    else:
        code = None
        reason = _PASS_REASON
    ev = LambdaEval(value=value, blocked=code is not None, code=code, reason=reason, axioms=axioms)
    return ev, log_lam


def evaluate_lambda(x: ArrayLike, w: ArrayLike | None = None) -> LambdaEval:
    """Λ with its axiom self-checks and a v1 ``code``.

    ``code`` is None for an advisory pass, ``ZERO_VETO`` for a zero axis, a ``LAMBDA_*``
    szl.lambda/v1 error code for a rejected input (value 0.0, no axioms evaluated), or
    ``AXIOM_<id>_FAILED`` (khipu-local, not a v1 code) if a self-check fails.
    ``blocked`` is True whenever ``code`` is not None.
    """
    return _evaluate(x, w)[0]


def _check_tau(tau: Any) -> float:
    if not _is_real(tau):
        raise _V1Rejected(LAMBDA_TAU_INVALID, f"threshold is {type(tau).__name__}, not a real number")
    if not _is_finite(tau):
        raise _V1Rejected(LAMBDA_TAU_INVALID, "threshold is not finite")
    if not 0 < tau <= 1:
        raise _V1Rejected(LAMBDA_TAU_INVALID, "threshold is outside (0, 1]")
    return float(tau)


def _gate_verdict(ev: LambdaEval, log_lam: float, threshold: Any) -> tuple[float | None, str, str | None, str]:
    """(tau, verdict, code, reason) under the szl.lambda/v1 gate rules, in rule order."""
    try:
        tau = _check_tau(threshold)
    except _V1Rejected as rej:
        return None, BLOCK, rej.code, f"{V1_SCHEMA} {rej.code}: {rej.detail}"
    if ev["code"] == ZERO_VETO:
        return tau, NO_GO, ZERO_VETO, ev["reason"]
    if ev["code"] is not None:
        return tau, BLOCK, ev["code"], ev["reason"]
    delta = log_lam - math.log(tau)
    if abs(delta) <= TIE_EPS:
        return tau, ABSTAIN, NUMERIC_TIE, f"|log Λ − log threshold| <= {TIE_EPS:g} (NUMERIC_TIE): abstain, not a pass"
    if delta > 0:
        return tau, GO, None, ev["reason"]
    return tau, NO_GO, BELOW_TAU, "Λ below threshold (BELOW_TAU): advisory, not a pass"


def lambda_gate(
    axes: ArrayLike,
    threshold: float = 0.5,
    *,
    weights: ArrayLike | None = None,
) -> LambdaEval:
    """Advisory conjunctive gate with the szl.lambda/v1 verdict. Never claims proven uniqueness.

    ``verdict`` / ``code``: BLOCK / <error code> when the threshold (checked first) or
    the input is rejected; NO_GO / ZERO_VETO for a zero axis; ABSTAIN / NUMERIC_TIE when
    |log Λ − log threshold| <= 1e-9; GO / None above that band; NO_GO / BELOW_TAU below
    it. The compare is in log space on the unrounded value. ``passed`` is True only on GO.
    """
    ev, log_lam = _evaluate(axes, weights)
    tau, verdict, code, reason = _gate_verdict(ev, log_lam, threshold)
    score = float(ev["value"])
    passed = verdict == GO
    return LambdaEval(
        score=score,
        passed=passed,
        threshold=tau,
        verdict=verdict,
        code=code,
        advisory=True,
        reason=reason,
        conjecture=CONJECTURE_1,
        proven_trust=False,
        value=score,
        blocked=not passed,
    )


assert advisory is True
