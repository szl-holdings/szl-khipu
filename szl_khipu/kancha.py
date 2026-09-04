# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""KanchaWitness — sealed courtyard. Original cut.

Gates named at seal stay shut. Open a gate or add a new one after the
kancha digest fail-closes. Not a firewall. Not Wasi rooms. Not a namespace.
"""

from __future__ import annotations

from typing import Any

from .chaski import djb2

KANCHA_GATES: tuple[str, ...] = ("east", "west", "north")


def run_kancha(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    sealed = [{"gate": g, "open": 0} for g in KANCHA_GATES]
    digest = djb2(f"{int(seed)}|" + ",".join(f"{g['gate']}:{g['open']}" for g in sealed))
    live = [dict(g) for g in sealed]
    if mode == 1:
        live[0]["open"] = 1
    if mode == 2:
        live.append({"gate": "south", "open": 0})
    now = djb2(f"{int(seed)}|" + ",".join(f"{g['gate']}:{g['open']}" for g in live))
    shut = len(live) == len(KANCHA_GATES) and all(g["open"] == 0 for g in live)
    hold = 1 if now == digest and shut and mode == 0 else 0
    if hold:
        reason = "KanchaWitness HOLDS · courtyard gates sealed shut · not a firewall · not Wasi rooms"
    elif mode == 2:
        reason = "KanchaWitness BROKEN · south gate added after the courtyard was sealed · fail closed"
    else:
        reason = "KanchaWitness BROKEN · sealed gate opened after digest · fail closed · not a silent perimeter"
    return {
        "hold": hold,
        "broken": 0 if hold else 1,
        "n": len(live),
        "gates": live,
        "claimed": list(KANCHA_GATES),
        "digest": digest,
        "now": now,
        "mode": mode,
        "reason": reason,
        "what_not": "Not a firewall. Not Wasi rooms. Not a namespace. Original cut.",
    }
