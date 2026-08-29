# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""RouteWitness — expert-assignment digest. Original cut of Mixtral/Switch MoE.

Swap an expert after routing — BLOCKED. Not Mixtral. No tokens/s claim.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .chaski import djb2

ROUTE_N = 8
ROUTE_E = 4


def run_route(seed: int = 11, tamper: int = 0) -> dict[str, Any]:
    rng = np.random.default_rng(int(seed))
    scores = rng.random((ROUTE_N, ROUTE_E))
    assignment = [int(np.argmax(row)) for row in scores]
    digest = djb2(",".join(str(a) for a in assignment))
    routed = list(assignment)
    if tamper == 1:
        routed[0] = (routed[0] + 1) % ROUTE_E
    now = djb2(",".join(str(a) for a in routed))
    hold = 1 if (now == digest and tamper != 1) else 0
    load = [0] * ROUTE_E
    for e in routed:
        load[e] += 1
    return {
        "hold": hold,
        "broken": 0 if hold else 1,
        "n": ROUTE_N,
        "experts": ROUTE_E,
        "assignment": routed,
        "digest": digest,
        "now": now,
        "load": load,
        "reason": (
            "RouteWitness HOLDS · assignment digest matches · not Mixtral · no tokens/s claim"
            if hold
            else "RouteWitness BROKEN · expert swapped after routing · fail closed · not a silent MoE rehost"
        ),
        "what_not": "Not Mixtral. Not Switch Transformer. Original cut.",
    }
