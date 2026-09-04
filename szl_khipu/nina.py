# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""NinaWitness — sealed spark. Original cut.

One spark is lit at seal. Restoke or stamp the spark as a joule after
the nina digest fail-closes. Not a lighter. Not RAPL. Not SamiWitness.
"""

from __future__ import annotations

from typing import Any

from .chaski import djb2

NINA_SPARKS = 1


def run_nina(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    sparks = NINA_SPARKS
    digest = djb2(f"{int(seed)}|{sparks}|null")
    live_sparks = sparks
    live_joule: float | None = None
    if mode == 1:
        live_sparks = sparks + 1
    if mode == 2:
        live_joule = 1.0
    now = djb2(f"{int(seed)}|{live_sparks}|{'null' if live_joule is None else live_joule}")
    hold = 1 if now == digest and live_sparks == 1 and live_joule is None and mode == 0 else 0
    if hold:
        reason = "NinaWitness HOLDS · one spark sealed · not a lighter · not RAPL · not SamiWitness"
    elif mode == 2:
        reason = "NinaWitness BROKEN · spark stamped as a joule after seal · fail closed"
    else:
        reason = "NinaWitness BROKEN · spark restoked after seal · fail closed · not a silent flame"
    return {
        "hold": hold,
        "broken": 0 if hold else 1,
        "sparks": live_sparks,
        "joule": live_joule,
        "digest": digest,
        "now": now,
        "mode": mode,
        "reason": reason,
        "what_not": "Not a lighter. Not RAPL. Not SamiWitness. Never a fabricated joule. Original cut.",
    }
