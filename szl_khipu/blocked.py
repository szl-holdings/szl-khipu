# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Deny-by-default gate. HARD_DENY > lambda veto > HARD_ALLOW. Output is None on BLOCK."""

from __future__ import annotations

from typing import Any


def deny_by_default(
    allow: bool,
    hard_deny: bool,
    lambda_pass: bool,
) -> dict[str, Any]:
    """Fail-closed policy.

    Precedence: HARD_DENY dominates everything, then deny-by-default
    (no explicit ALLOW), then advisory Λ veto, then HARD_ALLOW.
    Output is ALWAYS None on BLOCK.
    """
    if hard_deny:
        return {
            "blocked": True,
            "allowed": False,
            "output": None,
            "reason": "HARD_DENY dominates",
            "dominant": "HARD_SECURITY",
        }
    if not allow:
        return {
            "blocked": True,
            "allowed": False,
            "output": None,
            "reason": "DENY_DEFAULT — no explicit ALLOW",
            "dominant": "HARD_SECURITY",
        }
    if not lambda_pass:
        return {
            "blocked": True,
            "allowed": False,
            "output": None,
            "reason": "advisory Λ veto (still BLOCKED, still advisory)",
            "dominant": "ADVISORY_LAMBDA",
        }
    return {
        "blocked": False,
        "allowed": True,
        "output": {"ok": True},
        "reason": "ALLOW",
        "dominant": "NONE",
    }


four_way_gate = deny_by_default
