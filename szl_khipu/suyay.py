# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""SuyayWitness — sealed wait. Original cut.

The promised tick is named at seal. Arrive early or late after the
suyay digest fail-closes. Not Pacha clock. Not NTP. Not a timeout.
"""

from __future__ import annotations

from typing import Any

from .chaski import djb2

SUYAY_TICK = 4


def run_suyay(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    promised = SUYAY_TICK
    digest = djb2(f"{int(seed)}|wait:{promised}")
    arrived = promised
    if mode == 1:
        arrived = promised - 1
    if mode == 2:
        arrived = promised + 1
    now = djb2(f"{int(seed)}|wait:{arrived}")
    hold = 1 if now == digest and arrived == promised and mode == 0 else 0
    if hold:
        reason = "SuyayWitness HOLDS · promised tick arrived · not Pacha · not NTP · not a timeout"
    elif mode == 1:
        reason = "SuyayWitness BROKEN · tick arrived early after seal · fail closed"
    else:
        reason = "SuyayWitness BROKEN · tick arrived late after seal · fail closed · not a silent wait"
    return {
        "hold": hold,
        "broken": 0 if hold else 1,
        "promised": promised,
        "arrived": arrived,
        "digest": digest,
        "now": now,
        "mode": mode,
        "reason": reason,
        "what_not": "Not Pacha clock. Not NTP. Not a timeout. Original cut.",
    }
