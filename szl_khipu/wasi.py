# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""WasiWitness — sealed house. Original cut.

Rooms are named when the house is sealed. Add or drop a room after the
wasi digest fail-closes. Not a filesystem. Not a namespace. Not a CRDT.
"""

from __future__ import annotations

from typing import Any

from .chaski import djb2

WASI_ROOMS: tuple[str, ...] = ("hearth", "patio", "loft", "well")


def run_wasi(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    sealed = list(WASI_ROOMS)
    digest = djb2(f"{int(seed)}|" + "/".join(sealed))
    live = list(sealed)
    if mode == 1:
        live.append("annex")
    if mode == 2:
        live.pop()
    now = djb2(f"{int(seed)}|" + "/".join(live))
    same = "/".join(live) == "/".join(WASI_ROOMS)
    hold = 1 if now == digest and same and mode == 0 else 0
    if hold:
        reason = "WasiWitness HOLDS · house rooms sealed · not a filesystem · not a namespace"
    elif mode == 1:
        reason = "WasiWitness BROKEN · annex added after the house was sealed · fail closed"
    else:
        reason = "WasiWitness BROKEN · room dropped after seal · fail closed · not a silent house rehost"
    return {
        "hold": hold,
        "broken": 0 if hold else 1,
        "n": len(WASI_ROOMS),
        "rooms": live,
        "claimed": list(WASI_ROOMS),
        "digest": digest,
        "now": now,
        "mode": mode,
        "reason": reason,
        "what_not": "Not a filesystem. Not a namespace. Not a CRDT. Original cut.",
    }
