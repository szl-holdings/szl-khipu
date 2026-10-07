#!/usr/bin/env python3
"""Selective-risk accounting for mixed Khipu NAVIGATE + ABSTAIN suites.

Metric only. Nothing here trains, signs, publishes or promotes:
``evaluate`` always returns ``publication_eligible: False`` and
``promotion: "HOLD"``. A verdict is a software check of graded rows against
an owner-supplied budget. It is not a statement about any model.

Definitions (schema ``szl.khipu-selective-risk/v1``):

* ``total`` is the original row count. No row is ever dropped.
* A row is *abstained* (the rejected count) only when the grader reports a
  valid, explicit ``ABSTAIN``. Every other row is *accepted*.
* Malformed semantics M1 (fail-closed): a decision that is not exactly
  ``NAVIGATE`` or ``ABSTAIN`` is ``MALFORMED``. A malformed output is accepted
  and wrong, so it adds to both coverage and risk. It is never dropped.
* ``accepted = total - abstained`` and
  ``accepted_errors = accepted - correct_accepted``, which covers malformed
  outputs, NAVIGATE on an ABSTAIN-expected row, and wrong or invented routes.
* ``coverage = accepted / total``.
* ``selective_risk = accepted_errors / accepted``. It is ``"UNKNOWN"`` when
  ``accepted == 0``, and UNKNOWN is never PASS.

Callers pass rows that a named grader has already scored. A caller must pass
``ABSTAIN`` only for an abstention its grader accepts as valid (for example,
an ABSTAIN that still cites handles should be passed as malformed). Numbers
from different graders are not comparable. Ratios are reported as integer
``{"num", "den"}`` pairs, never floats, and no confidence interval is claimed.

Standard library only.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from fractions import Fraction

SCHEMA = "szl.khipu-selective-risk/v1"
NAVIGATE = "NAVIGATE"
ABSTAIN = "ABSTAIN"
MALFORMED = "MALFORMED"
UNKNOWN = "UNKNOWN"
PASS = "PASS"
FAIL = "FAIL"
INVALID_SUITE = "INVALID_SUITE"
EXPECTED_DECISIONS = (NAVIGATE, ABSTAIN)
RISK_DEFINITION = (
    "selective_risk = accepted_errors / accepted, accepted = total - abstained; "
    "UNKNOWN when accepted == 0"
)
MALFORMED_SEMANTICS = "M1: a non-ABSTAIN malformed output is accepted and wrong; never dropped"
_RATIO = re.compile(r"(0|[1-9][0-9]*)/([1-9][0-9]*)")
_COUNTS = (
    "total",
    "expected_navigate",
    "expected_abstain",
    "abstained",
    "accepted",
    "accepted_errors",
)


def _ratio(num: int, den: int) -> dict | str:
    return {"num": num, "den": den} if den else UNKNOWN


def normalize_row(expected: str, decision: object, answer_correct: bool) -> dict:
    """Validate one graded row.

    ``expected`` must be ``NAVIGATE`` or ``ABSTAIN``. Any ``decision`` other
    than exactly ``NAVIGATE`` or ``ABSTAIN`` becomes ``MALFORMED``.
    ``answer_correct`` must be a bool and may be True only when both
    ``expected`` and ``decision`` are ``NAVIGATE``.
    """
    if not isinstance(expected, str) or expected not in EXPECTED_DECISIONS:
        raise ValueError(f"expected must be NAVIGATE or ABSTAIN, got {expected!r}")
    if not isinstance(answer_correct, bool):
        raise ValueError(f"answer_correct must be a bool, got {answer_correct!r}")
    if not (isinstance(decision, str) and decision in EXPECTED_DECISIONS):
        decision = MALFORMED
    if answer_correct and not (expected == NAVIGATE and decision == NAVIGATE):
        raise ValueError(
            "answer_correct may be True only when expected and decision are both NAVIGATE"
        )
    return {"expected": expected, "decision": decision, "answer_correct": answer_correct}


def _rows(rows: Iterable[Mapping]) -> list[dict]:
    out = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("each row must be a mapping with expected, decision, answer_correct")
        try:
            out.append(normalize_row(row["expected"], row["decision"], row["answer_correct"]))
        except KeyError as exc:
            raise ValueError(f"row is missing {exc.args[0]!r}") from None
    return out


def account(rows: Iterable[Mapping]) -> dict:
    """Integer counts for graded rows. The denominator ``total`` never shrinks."""
    norm = _rows(rows)
    total = len(norm)
    expected_navigate = sum(1 for r in norm if r["expected"] == NAVIGATE)
    expected_abstain = total - expected_navigate
    abstained = sum(1 for r in norm if r["decision"] == ABSTAIN)
    abstained_correct = sum(
        1 for r in norm if r["decision"] == ABSTAIN and r["expected"] == ABSTAIN
    )
    malformed = sum(1 for r in norm if r["decision"] == MALFORMED)
    answered_valid = sum(1 for r in norm if r["decision"] == NAVIGATE)
    false_navigate = sum(
        1 for r in norm if r["decision"] == NAVIGATE and r["expected"] == ABSTAIN
    )
    correct_accepted = sum(1 for r in norm if r["answer_correct"])
    wrong_route = sum(
        1
        for r in norm
        if r["decision"] == NAVIGATE and r["expected"] == NAVIGATE and not r["answer_correct"]
    )
    accepted = total - abstained
    accepted_errors = accepted - correct_accepted
    return {
        "schema": SCHEMA,
        "risk_definition": RISK_DEFINITION,
        "malformed_semantics": MALFORMED_SEMANTICS,
        "total": total,
        "expected_navigate": expected_navigate,
        "expected_abstain": expected_abstain,
        "abstained": abstained,
        "abstained_correct": abstained_correct,
        "over_abstained": abstained - abstained_correct,
        "malformed": malformed,
        "answered_valid": answered_valid,
        "false_navigate": false_navigate,
        "wrong_route": wrong_route,
        "accepted": accepted,
        "correct_accepted": correct_accepted,
        "accepted_errors": accepted_errors,
        "coverage": _ratio(accepted, total),
        "coverage_valid": _ratio(answered_valid, total),
        "selective_risk": _ratio(accepted_errors, accepted),
        "abstain_recall": _ratio(abstained_correct, expected_abstain),
        # Legacy split counts, recomputed from the same rows so historical
        # abstain c/n and grounding c/n figures can be checked side by side.
        "legacy": {
            "abstain": f"{abstained_correct}/{expected_abstain}",
            "grounding": f"{correct_accepted}/{expected_navigate}",
        },
    }


def baseline_all_abstain(rows: Iterable[Mapping]) -> dict:
    """Every row abstains. Coverage is 0 and selective risk is UNKNOWN."""
    return account(
        {"expected": r["expected"], "decision": ABSTAIN, "answer_correct": False}
        for r in _rows(rows)
    )


def baseline_all_answer(rows: Iterable[Mapping]) -> dict:
    """Every row is answered, with oracle routing on NAVIGATE-expected rows.

    Its selective risk is ``expected_abstain / total``.
    """
    return account(
        {
            "expected": r["expected"],
            "decision": NAVIGATE,
            "answer_correct": r["expected"] == NAVIGATE,
        }
        for r in _rows(rows)
    )


def _budget_value(name: str, value: object) -> Fraction:
    match = _RATIO.fullmatch(value) if isinstance(value, str) else None
    if isinstance(value, Fraction):
        frac = value
    elif match:
        frac = Fraction(int(match.group(1)), int(match.group(2)))
    else:
        raise ValueError(
            f"{name} must be a fractions.Fraction or a 'p/q' string; got {value!r} "
            "(floats, NaN and other types are rejected)"
        )
    if not 0 <= frac <= 1:
        raise ValueError(f"{name} must lie in [0, 1]; got {frac}")
    return frac


def _counts(acct: Mapping) -> dict:
    if not isinstance(acct, Mapping):
        raise ValueError("verdict needs the mapping returned by account()")
    counts = {}
    for key in _COUNTS:
        value = acct.get(key)
        if type(value) is not int or value < 0:
            raise ValueError(f"account field {key!r} must be a non-negative int, got {value!r}")
        counts[key] = value
    if (
        counts["expected_navigate"] + counts["expected_abstain"] != counts["total"]
        or counts["abstained"] > counts["total"]
        or counts["accepted"] != counts["total"] - counts["abstained"]
        or counts["accepted_errors"] > counts["accepted"]
    ):
        raise ValueError("account counts are inconsistent")
    return counts


def verdict(acct: Mapping, *, max_selective_risk, min_coverage) -> dict:
    """PASS, FAIL or INVALID_SUITE for an ``account`` result against a budget.

    Both budget values are required keywords with no defaults. Each must be a
    ``Fraction`` or a ``'p/q'`` string in [0, 1]. Rules, in order:

    * INVALID_SUITE when the suite lacks NAVIGATE-expected or ABSTAIN-expected rows.
    * FAIL ``ZERO_ACCEPTED_RISK_UNKNOWN`` when nothing was accepted.
    * FAIL when selective risk exceeds ``max_selective_risk``.
    * FAIL unless selective risk is strictly below the all-answer baseline risk.
    * FAIL when coverage is below ``min_coverage``.
    """
    max_risk = _budget_value("max_selective_risk", max_selective_risk)
    min_cov = _budget_value("min_coverage", min_coverage)
    counts = _counts(acct)
    budget = {
        "schema": SCHEMA,
        "max_selective_risk": f"{max_risk.numerator}/{max_risk.denominator}",
        "min_coverage": f"{min_cov.numerator}/{min_cov.denominator}",
    }
    canonical = json.dumps(budget, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    total, accepted = counts["total"], counts["accepted"]
    reasons: list[str] = []
    if counts["expected_navigate"] == 0:
        reasons.append("NO_NAVIGATE_EXPECTED_ROWS")
    if counts["expected_abstain"] == 0:
        reasons.append("NO_ABSTAIN_EXPECTED_ROWS")
    if reasons:
        status = INVALID_SUITE
    else:
        if accepted == 0:
            reasons.append("ZERO_ACCEPTED_RISK_UNKNOWN")
        else:
            risk = Fraction(counts["accepted_errors"], accepted)
            if risk > max_risk:
                reasons.append("SELECTIVE_RISK_ABOVE_BUDGET")
            if risk >= Fraction(counts["expected_abstain"], total):
                reasons.append("RISK_NOT_BELOW_ALL_ANSWER_BASELINE")
        if Fraction(accepted, total) < min_cov:
            reasons.append("COVERAGE_BELOW_BUDGET")
        status = FAIL if reasons else PASS
    return {
        "status": status,
        "reasons": reasons,
        "budget": budget,
        "budget_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "selective_risk": _ratio(counts["accepted_errors"], accepted),
        "coverage": _ratio(accepted, total),
        "baseline_all_answer_risk": _ratio(counts["expected_abstain"], total),
    }


def evaluate(rows: Iterable[Mapping], *, max_selective_risk, min_coverage) -> dict:
    """Account the rows, both baselines and a budget verdict.

    This is a metric only. It grants no promotion and no publication:
    ``publication_eligible`` is always False and ``promotion`` is always HOLD.
    """
    norm = _rows(rows)
    candidate = account(norm)
    return {
        "schema": SCHEMA,
        "candidate": candidate,
        "baselines": {
            "all_abstain": baseline_all_abstain(norm),
            "all_answer": baseline_all_answer(norm),
        },
        "verdict": verdict(
            candidate, max_selective_risk=max_selective_risk, min_coverage=min_coverage
        ),
        "publication_eligible": False,
        "promotion": "HOLD",
    }
