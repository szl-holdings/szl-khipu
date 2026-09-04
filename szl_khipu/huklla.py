# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""HukllaWitness — sealed oneness. Original cut.

Two receipts are sealed as one pair. Split or swap the mate after the
huklla digest fail-closes. Not Tinku confluence. Not a join. Not a zipper.
"""

from __future__ import annotations

from typing import Any

from .chaski import djb2


def run_huklla(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    left = djb2(f"left:{int(seed)}")
    right = djb2(f"right:{int(seed)}")
    pair = [left, right]
    digest = djb2(f"{int(seed)}|{left}+{right}")
    live = list(pair)
    if mode == 1:
        live.pop()
    if mode == 2:
        live.reverse()
    now = djb2(f"{int(seed)}|" + "+".join(live))
    hold = 1 if now == digest and live == pair and mode == 0 else 0
    if hold:
        reason = "HukllaWitness HOLDS · two receipts stay one pair · not Tinku · not a join"
    elif mode == 1:
        reason = "HukllaWitness BROKEN · pair split after seal · fail closed"
    else:
        reason = "HukllaWitness BROKEN · mates swapped after seal · fail closed · not a silent unzip"
    return {
        "hold": hold,
        "broken": 0 if hold else 1,
        "pair": live,
        "claimed": pair,
        "digest": digest,
        "now": now,
        "mode": mode,
        "reason": reason,
        "what_not": "Not Tinku confluence. Not a join. Not a zipper. Original cut.",
    }
