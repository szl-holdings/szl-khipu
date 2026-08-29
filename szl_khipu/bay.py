# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Evidence Bay — four rails. Collapse any two and the body fail-closes. Never a11oy.com."""

from __future__ import annotations

from typing import Any

BAY_RAILS = ("transport", "evidence", "verification", "authority")

_BASE = [
    {"id": "hub-listing", "rail": "transport", "home": "transport", "note": "huggingface.co/SZLHOLDINGS"},
    {"id": "space-running", "rail": "transport", "home": "transport", "note": "Space RUNNING is transport"},
    {"id": "atlas-json", "rail": "evidence", "home": "evidence", "note": "a11oy.net/atlas.json"},
    {"id": "record", "rail": "evidence", "home": "evidence", "note": "a11oy.net RECORD"},
    {"id": "lab-sha256", "rail": "verification", "home": "verification", "note": "this lab SHA-256 cords"},
    {"id": "verify-tool", "rail": "verification", "home": "verification", "note": "a-11-oy.com/verify"},
    {"id": "lambda", "rail": "authority", "home": "authority", "note": "Λ advisory · Conjecture 1 OPEN"},
    {"id": "willay", "rail": "authority", "home": "authority", "note": "WILLAY signed refuse"},
]


def evaluate_bay(
    proof_into_product: int = 0,
    hub_as_proof: int = 0,
    space_as_receipt: int = 0,
) -> dict[str, Any]:
    items = [dict(o) for o in _BASE]
    collapses: list[str] = []
    if proof_into_product == 1:
        for i in items:
            if i["id"] == "record":
                i["rail"] = "authority"
        collapses.append("RECORD moved onto a-11-oy.com — evidence collapsed into product")
    if hub_as_proof == 1:
        for i in items:
            if i["id"] == "hub-listing":
                i["rail"] = "evidence"
        collapses.append("Hub listing treated as proof — transport counted as evidence")
    if space_as_receipt == 1:
        for i in items:
            if i["id"] == "space-running":
                i["rail"] = "verification"
        collapses.append("RUNNING Space treated as signed receipt — transport counted as verification")
    occupancy = {r: [i for i in items if i["rail"] == r] for r in BAY_RAILS}
    empty = [r for r in BAY_RAILS if not occupancy[r]]
    blocked = len(collapses) > 0
    return {
        "collapsed": len(collapses),
        "empty": len(empty),
        "blocked": blocked,
        "occupancy": occupancy,
        "collapses": collapses,
        "items": items,
        "neverA11oyCom": True,
        "reason": collapses[0] if blocked else "four rails occupied · no collapse · never a11oy.com",
    }


def run_bay(**kwargs: int) -> dict[str, Any]:
    ev = evaluate_bay(**kwargs)
    return {
        "collapsed": ev["collapsed"],
        "empty": ev["empty"],
        "blocked": 1 if ev["blocked"] else 0,
        "neverA11oyCom": 1,
        "reason": ev["reason"],
        "occupancy": ev["occupancy"],
        "collapses": ev["collapses"],
        "items": ev["items"],
    }
