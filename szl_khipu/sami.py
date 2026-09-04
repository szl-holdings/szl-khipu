# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""SamiWitness — sealed fortune. Original cut.

The bound carries energy_status UNAVAILABLE and no joule. Stamp a joule
or paint the channel LIVE after seal fail-closes. Not RAPL. Not a carbon score.
"""

from __future__ import annotations

from typing import Any

from .chaski import djb2

SAMI_STATUS = "UNAVAILABLE"


def run_sami(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    sealed_status = SAMI_STATUS
    sealed_joule = None
    digest = djb2(f"{int(seed)}|{sealed_status}|null")
    status = sealed_status
    joule: float | None = sealed_joule
    if mode == 1:
        joule = 12.4
    if mode == 2:
        status = "LIVE"
    now = djb2(f"{int(seed)}|{status}|{'null' if joule is None else joule}")
    honest = status == SAMI_STATUS and joule is None
    hold = 1 if now == digest and honest and mode == 0 else 0
    if hold:
        reason = "SamiWitness HOLDS · energy UNAVAILABLE · no joule · not RAPL · not a carbon score"
    elif mode == 1:
        reason = "SamiWitness BROKEN · joule stamped after the fortune was sealed · fail closed"
    else:
        reason = "SamiWitness BROKEN · energy channel painted LIVE after seal · fail closed · not a silent meter"
    return {
        "hold": hold,
        "broken": 0 if hold else 1,
        "status": status,
        "joule": joule,
        "claimed": sealed_status,
        "digest": digest,
        "now": now,
        "mode": mode,
        "reason": reason,
        "what_not": "Not RAPL. Not a carbon score. Never a fabricated joule. Original cut.",
    }
