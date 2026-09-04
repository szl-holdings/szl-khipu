# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""YawarWitness — sealed lineage. Original cut.

Each receipt names its parent digest. Swap a parent or splice a bastard
after the bloodline is sealed fail-closes. Not a blockchain. Not git. Not Chaski.
"""

from __future__ import annotations

from typing import Any

from .chaski import djb2

YAWAR_N = 4


def run_yawar(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    origin = djb2(f"yawar:{int(seed) & 0xFFFFFFFF}")
    sealed = [origin]
    for i in range(1, YAWAR_N):
        sealed.append(djb2(f"{sealed[i - 1]}|{int(seed)}|{i}"))
    digest = djb2(">".join(sealed))
    live = list(sealed)
    if mode == 1:
        live[-1] = djb2(f"{live[0]}|bastard")
    if mode == 2:
        live.insert(2, djb2(f"{live[1]}|splice"))
    now = djb2(">".join(live))
    lineage = 1 if len(live) == YAWAR_N else 0
    if lineage:
        for i in range(1, len(live)):
            if live[i] != djb2(f"{live[i - 1]}|{int(seed)}|{i}"):
                lineage = 0
                break
    hold = 1 if now == digest and lineage == 1 and mode == 0 else 0
    if hold:
        reason = "YawarWitness HOLDS · bloodline is parent-digest · not a blockchain · not git · not Chaski"
    elif mode == 2:
        reason = "YawarWitness BROKEN · bastard node spliced after the bloodline was sealed · fail closed"
    else:
        reason = "YawarWitness BROKEN · parent swapped after seal · fail closed · not a silent chain rehost"
    return {
        "hold": hold,
        "broken": 0 if hold else 1,
        "n": YAWAR_N,
        "line": live,
        "claimed": sealed,
        "lineage": lineage,
        "digest": digest,
        "now": now,
        "mode": mode,
        "reason": reason,
        "what_not": "Not a blockchain. Not git. Not Chaski FIFO. Original cut.",
    }
