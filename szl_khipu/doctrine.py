# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Frozen doctrine facts. Do not paint a sorry green."""

from __future__ import annotations

from typing import Final

DOCTRINE: Final[dict[str, object]] = {
    "version": "v11 LOCKED",
    "kernelCommit": "c7c0ba17",
    "lockedDeclarations": 749,
    "uniqueAxioms": 14,
    "trackedSorries": 163,
    "lockedProvenCount": 8,
    "lockedIds": ("F1", "F4", "F7", "F11", "F12", "F18", "F19", "F22"),
    "trustCeiling": 0.97,
    "conjecture1": (
        "Any two aggregators satisfying A1–A4 agree on every input. OPEN (sorry). "
        "Unconditional uniqueness under kernel A1–A5 is machine-checked FALSE."
    ),
    "energyPolicy": "MEASURED-NVML or UNAVAILABLE. Never a fabricated joule.",
    "lambdaAdvisory": True,
    "provenTrust": False,
}

YUYAY_AXES: Final[tuple[str, ...]] = (
    "moralGrounding",
    "measurabilityHonesty",
    "empiricalGrounding",
    "logicalConsistency",
    "sourceTransparency",
    "reproducibility",
    "licenseHygiene",
    "scopeDiscipline",
    "claimCalibration",
    "evalAwareness",
    "deceptionKeywords",
    "conflictingDirectives",
    "reversalDirective",
)

YUYAY_FLOORS: Final[tuple[float, ...]] = (
    0.95,
    0.95,
    0.90,
    0.90,
    0.90,
    0.90,
    0.90,
    0.90,
    0.90,
    0.90,
    0.90,
    0.90,
    0.90,
)

CONJECTURE_1: Final[str] = str(DOCTRINE["conjecture1"])

ENERGY_POLICY: Final[str] = str(DOCTRINE["energyPolicy"])

# Uniqueness is OPEN. Lambda is advisory. Proven trust is false.
proven_trust: Final[bool] = False
advisory: Final[bool] = True

AXIOMS: Final[dict[str, str]] = {
    "A1": "IsMonotone",
    "A2": "IsHomogeneous  Λ(c·x)=c·Λ(x)",
    "A3": "IsEgyptianExact  Λ(c,…,c)=c",
    "A4": "IsBounded  Λ(x)≤max(x)",
    "A5": "IsPermutationInvariant",
}

LOCKED_EIGHT: Final[tuple[str, ...]] = DOCTRINE["lockedIds"]  # type: ignore[assignment]

QUECHUA: Final[dict[str, str]] = {
    "khipu": "knotted-cord ledger / witnessed consensus",
    "yarqa": "irrigation canal / compartment attention",
    "hatun": "great / orchestrator",
    "yuyay": "thought / 13-axis conjunctive gate",
    "willay": "to tell / signed refusal",
    "chaski": "runner / message FIFO",
    "nan": "road / frontier",
    "tinkuy": "meeting / command center",
    "puriq": "to walk / locked formula set",
}

assert len(YUYAY_AXES) == 13
assert len(YUYAY_FLOORS) == 13
assert YUYAY_FLOORS[0] == 0.95 and YUYAY_FLOORS[1] == 0.95
assert all(f == 0.90 for f in YUYAY_FLOORS[2:])
assert len(LOCKED_EIGHT) == 8
assert DOCTRINE["trustCeiling"] == 0.97
assert proven_trust is False
assert advisory is True
