# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""GreenLight — fail-closed promotion. A sorry cannot be painted green."""

from __future__ import annotations

from typing import Any

from .doctrine import DOCTRINE


def evaluate_greenlight(
    paint_sorry: int = 0,
    claim_proven: int = 0,
    stamp_joule: int = 0,
) -> dict[str, Any]:
    locked = int(DOCTRINE["lockedProvenCount"])  # type: ignore[arg-type]
    checks = [
        {
            "id": "sorry",
            "ok": paint_sorry != 1,
            "detail": (
                "BLOCKED · a sorry cannot be painted green"
                if paint_sorry == 1
                else f"sorry stays sorry · locked-8 is {locked}, not 21"
            ),
        },
        {
            "id": "conjecture1",
            "ok": claim_proven != 1,
            "detail": (
                "BLOCKED · proven_trust cannot be true while Λ is Conjecture 1"
                if claim_proven == 1
                else "proven_trust locked false · uniqueness OPEN"
            ),
        },
        {
            "id": "energy",
            "ok": stamp_joule != 1,
            "detail": (
                "BLOCKED · fabricated joule · energy UNAVAILABLE"
                if stamp_joule == 1
                else "energy UNAVAILABLE · never a fabricated joule"
            ),
        },
    ]
    painted = sum(1 for c in checks if not c["ok"])
    blocked = painted > 0
    return {
        "painted": painted,
        "blocked": 1 if blocked else 0,
        "greenlit": 0 if blocked else 1,
        "provenTrust": False,
        "energy": "UNAVAILABLE",
        "lockedProven": locked,
        "conjecture1": "OPEN",
        "checks": checks,
        "reason": (
            next((c["detail"] for c in checks if not c["ok"]), "promotion blocked")
            if blocked
            else "GREEN-LIGHT · LIVE bound · proven_trust false · energy UNAVAILABLE"
        ),
    }


def run_greenlight(**kwargs: int) -> dict[str, Any]:
    ev = evaluate_greenlight(**kwargs)
    return {
        **ev,
        "provenTrust": 0,
    }
