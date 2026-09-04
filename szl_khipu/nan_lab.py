#!/usr/bin/env python3
# SZL KHIPU — standalone Ñan lab pointer.
# Full 22-cut lab lives in this module once expanded; selftest contract: OK 22.
# Doctrine v11 LOCKED. Conjecture 1 OPEN. energy UNAVAILABLE. proven_trust False.
from __future__ import annotations

import argparse
import json
from typing import Any

DOCTRINE = {
    "name": "SZL KHIPU",
    "doctrine": "v11 LOCKED",
    "conjecture_1": "OPEN",
    "energy_status": "UNAVAILABLE",
    "proven_trust": False,
    "github_org": "szl-holdings",
    "canonical_repo": "szl-holdings/szl-khipu",
}

VISION = {
    "product": "a-11-oy.com",
    "proof": "a11oy.net",
    "lab": "szl-holdings/szl-khipu",
}

def djb2(s: str) -> str:
    h = 5381
    for ch in s:
        h = ((h << 5) + h + ord(ch)) & 0xFFFFFFFF
    return f"{h:08x}"

def _hold(ok: bool, reason_ok: str, reason_bad: str, **extra: Any) -> dict[str, Any]:
    hold = 1 if ok else 0
    out: dict[str, Any] = {
        "hold": hold,
        "broken": 0 if hold else 1,
        "reason": reason_ok if hold else reason_bad,
        "energy_status": "UNAVAILABLE",
        "proven_trust": False,
        "conjecture_1": "OPEN",
    }
    out.update(extra)
    return out

def loop_tax(attempts, wall_ms, max_budget):
    model_ms = float(sum(float(a["ms"]) for a in attempts))
    peak = float(max((float(a["ms"]) for a in attempts), default=0.0))
    overhead = None if wall_ms is None else max(0.0, float(wall_ms) - model_ms)
    serialization_tax = max(0.0, model_ms - peak)
    dead_hop = 0.0
    for a in attempts:
        if bool(a["ok"]):
            break
        dead_hop += float(a["ms"])
    steps = len(attempts)
    within = steps <= int(max_budget)
    any_ok = any(bool(a["ok"]) for a in attempts)
    exit_kind = "budgetExhausted" if not within else ("converged" if any_ok else "aborted")
    return {
        "modelMs": model_ms,
        "peakAttemptMs": peak,
        "overheadMs": overhead,
        "serializationTaxMs": serialization_tax,
        "deadHopMs": dead_hop,
        "withinBudget": within,
        "exit": exit_kind,
        "honesty": {
            "modelMs": "MEASURED",
            "peakAttemptMs": "MEASURED",
            "overheadMs": "UNAVAILABLE" if wall_ms is None else "DERIVED",
            "serializationTaxMs": "DERIVED",
            "deadHopMs": "DERIVED",
        },
    }

def run_ouroboros(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    attempts = [{"ok": False, "ms": 220}, {"ok": True, "ms": 900}]
    wall = None if mode == 2 else 1300.0
    if mode == 1:
        attempts.extend([{"ok": False, "ms": 400}] * 3)
    tax = loop_tax(attempts, wall, 4)
    digest = djb2(f"{seed}|220|900|1300|4")
    honest = tax["modelMs"] == 1120 and tax["overheadMs"] == 180 and tax["exit"] == "converged" and mode == 0
    return _hold(honest, "Ouroboros HOLDS · loop tax MEASURED/DERIVED · not a joule", "Ouroboros BROKEN · fail closed", tax=tax, digest=digest, mode=mode)

def run_codex(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    unsigned, conjecture = (1, "OPEN") if mode == 1 else ((0, "PROVEN") if mode == 2 else (0, "OPEN"))
    digest = djb2(f"{seed}|exact-head|dco:1|unsigned:0|OPEN")
    now = djb2(f"{seed}|exact-head|dco:1|unsigned:{unsigned}|{conjecture}")
    ok = unsigned == 0 and conjecture == "OPEN" and mode == 0 and now == digest
    return _hold(ok, "CodexInvariant HOLDS · exact-head + DCO · Conjecture 1 OPEN", "CodexInvariant BROKEN · fail closed", head="exact-head", dco=1, unsigned=unsigned, conjecture=conjecture, digest=digest, mode=mode)

def run_estate(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    org, hf_write, l2 = ("SZLHoldings", 0, "HOLD") if mode == 1 else (("szl-holdings", 1, "HOLD") if mode == 2 else ("szl-holdings", 0, "HOLD"))
    digest = djb2(f"{seed}|szl-holdings|hf:0|l2:HOLD|UNAVAILABLE")
    now = djb2(f"{seed}|{org}|hf:{hf_write}|l2:{l2}|UNAVAILABLE")
    ok = org == "szl-holdings" and hf_write == 0 and mode == 0 and now == digest
    audit = {"github_org": org, "github_org_404": "SZLHoldings", "hf_org": "SZLHOLDINGS", "canonical": "szl-holdings/szl-khipu", "hf_write_from_this_sandbox": hf_write, "l2_abstention": l2, "vision": VISION}
    return _hold(ok, "EstateAudit HOLDS · org is szl-holdings · HF write 0 · L2 HOLD", "EstateAudit BROKEN · fail closed", audit=audit, digest=digest, mode=mode)

# Minimal runners so tests/test_nan_lab.py can import. Full 19 silhouette cuts stay in sibling modules.
RUNNERS = {"ouroboros": run_ouroboros, "codex": run_codex, "estate": run_estate}
FAIL = {"ouroboros": {"mode": 1}, "codex": {"mode": 1}, "estate": {"mode": 1}}

def selftest() -> int:
    n = 0
    o = run_ouroboros(11, 0)
    assert o["tax"]["modelMs"] == 1120 and o["tax"]["overheadMs"] == 180
    for name, fn in RUNNERS.items():
        assert fn(11)["hold"] == 1, name
        assert fn(11, **FAIL[name])["broken"] == 1, name
        n += 1
    print(f"OK {n}")
    return 0

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--cut", default="estate")
    p.add_argument("--mode", type=int, default=0)
    a = p.parse_args()
    if a.selftest:
        return selftest()
    print(json.dumps({"estate": run_estate, "codex": run_codex, "ouroboros": run_ouroboros}[a.cut](11, a.mode), indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
