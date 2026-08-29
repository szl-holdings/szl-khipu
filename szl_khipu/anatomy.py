# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Five-organ integrity kernel — fail-closed substrate of szl-holdings/anatomy.

Not a Three.js rehost. The 3D atlas at SZLHOLDINGS/anatomy is SLSA L1 static viz.
This module runs the organs that atlas depicts:

  HEART / YUYAY      — advisory Λ gate (F4, F11)
  CIRCULATORY / YAWAR — SHA-256 receipt chain (F7, F22)
  BRAIN / YACHAY      — YARQA canal attention, read-only (F1)
  NERVOUS / OTel      — loop-tax silhouette, energy UNAVAILABLE (F12)
  SKELETON / Khipu    — locked-8 structural silhouettes (F18, F19)

WILLAY is conscience: inspectable signed refusals, tamper-EVIDENT not tamper-proof.
Any DOWN organ or a WILLAY veto fail-closes the body.
Λ uniqueness remains Conjecture 1 OPEN. proven_trust is False.
Energy is UNAVAILABLE. Never a fabricated joule. Locked-proven stays exactly 8.
"""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from .chain import UnifiedReceiptChain
from .doctrine import CONJECTURE_1, DOCTRINE, YUYAY_FLOORS, proven_trust
from .formulas import run_puriq
from .lambda_gate import evaluate_lambda
from .ouroboros import loop_tax
from .yarqa import yarqa_attn

ORGAN_SPEC: tuple[dict[str, Any], ...] = (
    {
        "id": "brain",
        "name": "BRAIN",
        "quechua": "YACHAY",
        "formulas": ("F1",),
        "role": "read-only reasoning cortex — never holds write authority",
    },
    {
        "id": "heart",
        "name": "HEART",
        "quechua": "YUYAY",
        "formulas": ("F4", "F11"),
        "role": "13-axis conjunctive critique gate — advisory Λ",
    },
    {
        "id": "circulatory",
        "name": "CIRCULATORY",
        "quechua": "YAWAR",
        "formulas": ("F7", "F22"),
        "role": "append-only receipt bus — SHA-256",
    },
    {
        "id": "nervous",
        "name": "NERVOUS",
        "quechua": "OTel",
        "formulas": ("F12",),
        "role": "telemetry spine — energy UNAVAILABLE",
    },
    {
        "id": "skeleton",
        "name": "SKELETON",
        "quechua": "Khipu",
        "formulas": ("F18", "F19"),
        "role": "locked-8 formula spine — CHECKED ≠ Lean PROVEN",
    },
)

WILLAY_CLASSIFIERS: tuple[dict[str, str], ...] = (
    {
        "id": "cyber",
        "title": "Cyber dual-use",
        "fires_on": "offensive exploit generation, credential theft, ransomware playbooks",
        "lineage": "inspectable signed refusal — not an Anthropic classifier",
    },
    {
        "id": "bio",
        "title": "Bio dual-use",
        "fires_on": "pathogen enhancement, synthesis assistance beyond public literature",
        "lineage": "inspectable signed refusal",
    },
    {
        "id": "hidden",
        "title": "Hidden-reasoning extraction",
        "fires_on": "attempts to dump chain-of-thought or strip governance receipts",
        "lineage": "inspectable signed refusal",
    },
    {
        "id": "bypass",
        "title": "Governance bypass",
        "fires_on": "prompt injection that asks to skip Λ, the ledger, or WILLAY",
        "lineage": "inspectable signed refusal",
    },
    {
        "id": "harm",
        "title": "Self-harm",
        "fires_on": "requests for self-harm methods or encouragement",
        "lineage": "inspectable signed refusal",
    },
)

WILLAY_NOTE = (
    "Refusals are tamper-EVIDENT, not tamper-proof. Auditable rules. "
    "Trust ceiling 0.97. WILLAY is conscience, not a sixth proven organ."
)

LOCKED_EIGHT_IDS = ("F1", "F4", "F7", "F11", "F12", "F18", "F19", "F22")


class AnatomyEval(dict[str, Any]):
    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def _organ(
    id_: str,
    name: str,
    quechua: str,
    formulas: tuple[str, ...],
    status: str,
    honesty: str,
    detail: str,
    metric: float,
) -> dict[str, Any]:
    return {
        "id": id_,
        "name": name,
        "quechua": quechua,
        "formulas": list(formulas),
        "status": status,
        "honesty": honesty,
        "detail": detail,
        "metric": float(metric),
    }


def evaluate_anatomy(
    *,
    zero_heart: bool = False,
    leak_canal: bool = False,
    tamper_chain: bool = False,
    fabricate_joule: bool = False,
    break_skeleton: bool = False,
    willay_fire: bool = False,
    seed: int = 11,
) -> AnatomyEval:
    """Run all five organs. Fail-closed if any is DOWN or WILLAY refuses."""
    if proven_trust is True:
        raise RuntimeError("refusing proven_trust true")

    axes = list(YUYAY_FLOORS)
    if zero_heart:
        axes[0] = 0.0
    heart = evaluate_lambda(axes)
    heart_down = bool(heart["blocked"])

    chain = UnifiedReceiptChain()
    chain.emit("anatomy", "brain", {"seed": int(seed)})
    chain.emit("anatomy", "heart", {"lambda": float(heart["value"])})
    chain.emit("anatomy", "skeleton", {"locked": 8})
    if tamper_chain and chain.receipts:
        rec = chain.receipts[1]
        rec.prev = "deadbeef" + rec.prev[8:]
        chain._receipts[1] = rec  # noqa: SLF001 — deliberate tamper for the fail-closed test
    chain_ok, chain_depth, chain_brk = chain.verify()
    yawar_down = not chain_ok

    rng = np.random.default_rng(int(seed))
    q = rng.standard_normal((12, 4))
    k = rng.standard_normal((12, 4))
    v = rng.standard_normal((12, 4))
    _out, _probs, leaked = yarqa_attn(q, k, v, n_canals=3)
    leaked_f = float(leaked)
    if leak_canal:
        leaked_f = max(leaked_f, 1.0)
    brain_down = leaked_f > 1e-9

    tax = loop_tax(
        [{"ok": False, "ms": 220}, {"ok": True, "ms": 900}],
        wall_ms=1300,
        max_budget=4,
    )
    nervous_down = bool(fabricate_joule)

    puriq = run_puriq(int(seed))
    if break_skeleton:
        for row in puriq:
            if row.get("id") in ("F18", "f18", "RS_singleton") or "F18" in str(row.get("id", "")):
                row["ok"] = False
                break
        else:
            puriq[0]["ok"] = False
    skeleton_pass = sum(1 for r in puriq if r.get("ok"))
    skeleton_down = skeleton_pass < len(puriq)

    organs = [
        _organ(
            "brain",
            "BRAIN",
            "YACHAY",
            ("F1",),
            "DOWN" if brain_down else "LIVE",
            "LIVE",
            (
                f"cross-canal leak {leaked_f:.3e} — YACHAY cannot reason across a broken partition"
                if brain_down
                else f"read-only cortex · canal leak {leaked_f:.3e} · no write authority"
            ),
            leaked_f,
        ),
        _organ(
            "heart",
            "HEART",
            "YUYAY",
            ("F4", "F11"),
            "DOWN" if heart_down else "LIVE",
            "ADVISORY",
            (
                f"Λ {float(heart['value']):.4f} · {heart['reason']}"
                if heart_down
                else f"Λ {float(heart['value']):.4f} · advisory · Conjecture 1 OPEN"
            ),
            float(heart["value"]),
        ),
        _organ(
            "circulatory",
            "CIRCULATORY",
            "YAWAR",
            ("F7", "F22"),
            "DOWN" if yawar_down else "LIVE",
            "LIVE",
            (
                f"chain break at {chain_brk} — prev pointer does not walk. Fail closed."
                if yawar_down
                else f"3-hop SHA-256 · depth {chain_depth} · head {chain.head[:12]}"
            ),
            0.0 if chain_ok else 1.0,
        ),
        _organ(
            "nervous",
            "NERVOUS",
            "OTel",
            ("F12",),
            "DOWN" if nervous_down else "LIVE",
            "UNAVAILABLE",
            (
                "fabricated joule refused — energy stays UNAVAILABLE"
                if nervous_down
                else f"loop-tax {tax.get('exit', tax)} · energy UNAVAILABLE · never a fabricated joule"
            ),
            1.0 if nervous_down else 0.0,
        ),
        _organ(
            "skeleton",
            "SKELETON",
            "Khipu",
            ("F18", "F19"),
            "DOWN" if skeleton_down else "LIVE",
            "ADVISORY",
            (
                f"locked-8 silhouettes {skeleton_pass}/{len(puriq)} — a sorry cannot be painted green"
                if skeleton_down
                else (
                    f"locked-8 silhouettes {skeleton_pass}/{len(puriq)} · "
                    f"CHECKED ≠ Lean PROVEN @ {DOCTRINE['kernelCommit']}"
                )
            ),
            float(skeleton_pass),
        ),
    ]

    live_count = sum(1 for o in organs if o["status"] == "LIVE")
    organ_down = any(o["status"] == "DOWN" for o in organs)
    blocked = organ_down or willay_fire
    if willay_fire:
        reason = (
            "WILLAY conscience veto — governance bypass refused "
            "(tamper-EVIDENT, not tamper-proof)"
        )
    elif organ_down:
        down = ", ".join(o["name"] for o in organs if o["status"] == "DOWN")
        reason = f"organ integrity FAIL · {down} DOWN · fail closed"
    else:
        reason = (
            f"organ integrity {live_count}/5 LIVE · Λ advisory · "
            "energy UNAVAILABLE · Conjecture 1 OPEN"
        )

    return AnatomyEval(
        organs=organs,
        live_count=int(live_count),
        blocked=bool(blocked),
        willay={
            "refused": bool(willay_fire),
            "category": "bypass" if willay_fire else "none",
            "note": WILLAY_NOTE,
            "classifiers": [dict(c) for c in WILLAY_CLASSIFIERS],
        },
        energy="UNAVAILABLE",
        energy_j=None,
        lambda_advisory=True,
        conjecture_1="OPEN",
        locked_proven=8,
        kernel_commit=DOCTRINE["kernelCommit"],
        chain_head=chain.head,
        chain_ok=bool(chain_ok),
        proven_trust=False,
        reason=reason,
        conjecture_1_statement=CONJECTURE_1,
        not_a_rehost="szl-holdings/anatomy 3D atlas is SLSA L1 static viz — this kernel is the integrity check",
    )


def anatomy_metrics(ev: Mapping[str, Any]) -> dict[str, float]:
    organs = {o["id"]: o for o in ev["organs"]}
    return {
        "liveCount": float(ev["live_count"]),
        "blocked": 1.0 if ev["blocked"] else 0.0,
        "lambda": float(organs["heart"]["metric"]),
        "leaked": float(organs["brain"]["metric"]),
        "chainBreaks": float(organs["circulatory"]["metric"]),
        "energyFabricated": float(organs["nervous"]["metric"]),
        "skeletonOk": float(organs["skeleton"]["metric"]),
        "willayRefuse": 1.0 if ev["willay"]["refused"] else 0.0,
    }
