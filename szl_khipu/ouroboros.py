# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Loop tax: MEASURED attempt times vs DERIVED overhead. Never fabricate joules."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

Attempt = Mapping[str, Any]


def loop_tax(
    attempts: Sequence[Attempt],
    wall_ms: float | None,
    max_budget: int,
) -> dict[str, Any]:
    """Self-check arithmetic from szl-ouroboros.

    attempts [220 fail, 900 ok], wall=1300 →
      modelMs=1120, peak=900, overhead=180, serializationTax=220, deadHop=220.
    """
    model_ms = float(sum(float(a["ms"]) for a in attempts))
    peak = float(max((float(a["ms"]) for a in attempts), default=0.0))
    if wall_ms is None:
        overhead: float | None = None
        overhead_label = "UNAVAILABLE"
    else:
        overhead = max(0.0, float(wall_ms) - model_ms)
        overhead_label = "DERIVED"
    serialization_tax = max(0.0, model_ms - peak)
    dead_hop = 0.0
    for a in attempts:
        if bool(a["ok"]):
            break
        dead_hop += float(a["ms"])
    steps = len(attempts)
    within = steps <= int(max_budget)
    any_ok = any(bool(a["ok"]) for a in attempts)
    if not within:
        exit_kind = "budgetExhausted"
    elif any_ok:
        exit_kind = "converged"
    else:
        exit_kind = "aborted"
    return {
        "modelMs": model_ms,
        "peakAttemptMs": peak,
        "overheadMs": overhead,
        "serializationTaxMs": serialization_tax,
        "deadHopMs": dead_hop,
        "withinBudget": within,
        "exit": exit_kind,
        "honesty": {
            "modelMs": "MEASURED",
            "peakAttemptMs": "MEASURED",
            "overheadMs": overhead_label,
            "serializationTaxMs": "DERIVED",
            "deadHopMs": "DERIVED",
        },
    }


OUROBOROS_SELFCHECK: dict[str, Any] = loop_tax(
    [
        {"ok": False, "ms": 220},
        {"ok": True, "ms": 900},
    ],
    1300,
    4,
)
