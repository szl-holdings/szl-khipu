#!/usr/bin/env python3
# SZL KHIPU — Ñan silhouette lab + Ouroboros + Codex + estate.
# Doctrine v11 LOCKED. stdlib only. Conjecture 1 OPEN. energy UNAVAILABLE.
"""python3 -m szl_khipu.nan_lab --selftest  # OK 22
python3 -m szl_khipu.nan_lab --serve 8765
"""
from __future__ import annotations

import argparse
import inspect
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import urlparse

DOCTRINE = {"name": "SZL KHIPU", "doctrine": "v11 LOCKED", "locked_declarations": 749, "axioms": 14, "sorries": 163, "locked_proven": 8, "conjecture_1": "OPEN", "energy_status": "UNAVAILABLE", "proven_trust": False, "hash": "djb2 silhouette · not SHA3", "github_org": "szl-holdings", "github_org_not": "SZLHoldings", "hf_org": "SZLHOLDINGS", "canonical_repo": "szl-holdings/szl-khipu", "what_not": "Not Medusa. Not PBFT. Not Lamport. Not a CRDT. Not RAPL. Not a fabricated joule."}
VISION = {"product": "a-11-oy.com", "proof": "a11oy.net", "lab": "szl-holdings/szl-khipu", "hub": "SZLHOLDINGS/szl-khipu", "l2_abstention": "CONTROLLER_ONLY HOLD"}

def djb2(s: str) -> str:
    h = 5381
    for ch in s:
        h = ((h << 5) + h + ord(ch)) & 0xFFFFFFFF
    return f"{h:08x}"

def _hold(ok: bool, reason_ok: str, reason_bad: str, **extra: Any) -> dict[str, Any]:
    hold = 1 if ok else 0
    out: dict[str, Any] = {"hold": hold, "broken": 0 if hold else 1, "reason": reason_ok if hold else reason_bad, "energy_status": "UNAVAILABLE", "proven_trust": False, "conjecture_1": "OPEN"}
    out.update(extra)
    return out

def run_draft(seed: int = 11, tamper: int = 0) -> dict[str, Any]:
    mask = [(seed + i * 3) % 2 for i in range(4)]
    digest = djb2("|".join(map(str, mask)))
    live = list(mask)
    if tamper:
        live[0] = 1 - live[0]
    now = djb2("|".join(map(str, live)))
    return _hold(now == digest and tamper == 0, "DraftWitness HOLDS", "DraftWitness BROKEN", mask=live, digest=digest, tamper=tamper)

def run_quorum(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    votes = [1, 1, 1, 0]
    digest = djb2(f"{seed}|{votes}")
    live = list(votes)
    if mode == 1:
        live[2] = 0
    if mode == 2:
        live.append(1)
    now = djb2(f"{seed}|{live}")
    return _hold(now == digest and sum(live) >= 3 and len(live) == 4 and mode == 0, "QuorumWitness HOLDS", "QuorumWitness BROKEN", votes=live, digest=digest, mode=mode)

def run_latent(seed: int = 11, tamper: int = 0) -> dict[str, Any]:
    vec = [((seed + i * 7) % 13) / 13.0 for i in range(4)]
    digest = djb2("|".join(f"{x:.4f}" for x in vec))
    live = list(vec)
    if tamper:
        live[0] = 0.99
    now = djb2("|".join(f"{x:.4f}" for x in live))
    return _hold(now == digest and tamper == 0, "LatentWitness HOLDS", "LatentWitness BROKEN", vec=live, digest=digest, tamper=tamper)

def run_breath(seed: int = 11, tamper: int = 0) -> dict[str, Any]:
    digest = djb2(f"{seed}|8|STOP")
    extra = 3 if tamper else 0
    now = djb2(f"{seed}|{8 + extra}|{'MORE' if tamper else 'STOP'}")
    return _hold(now == digest and tamper == 0, "BreathWitness HOLDS", "BreathWitness BROKEN", budget=8, used=8 + extra, digest=digest, tamper=tamper)

def run_echo(seed: int = 11, tamper: int = 0) -> dict[str, Any]:
    prompt, reply = f"ask:{seed}", f"say:{seed}"
    digest = djb2(f"{prompt}||{reply}")
    live = reply if not tamper else f"swap:{seed}"
    now = djb2(f"{prompt}||{live}")
    return _hold(now == digest and tamper == 0, "EchoWitness HOLDS", "EchoWitness BROKEN", prompt=prompt, reply=live, digest=digest, tamper=tamper)

def run_ash(seed: int = 11, tamper: int = 0) -> dict[str, Any]:
    forgot = ["secret", "name", "key"]
    digest = djb2("|".join(forgot))
    live = list(forgot)
    if tamper:
        live.remove("name")
    now = djb2("|".join(live))
    return _hold(now == digest and tamper == 0, "AshWitness HOLDS", "AshWitness BROKEN", forgot=live, digest=digest, tamper=tamper)

def run_rite(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    steps = ["breath", "echo", "ash"]
    digest = djb2(">".join(steps))
    live = list(steps)
    if mode == 1:
        live.remove("echo")
    if mode == 2:
        live = ["ash", "echo", "breath"]
    now = djb2(">".join(live))
    return _hold(now == digest and mode == 0, "RiteWitness HOLDS", "RiteWitness BROKEN", steps=live, digest=digest, mode=mode)

def run_gaze(seed: int = 11, tamper: int = 0) -> dict[str, Any]:
    assigned = [(seed + h * 3) % 3 for h in range(4)]
    digest = djb2("|".join(map(str, assigned)))
    looked = list(assigned)
    if tamper:
        looked[0] = (looked[0] + 1) % 3
    now = djb2("|".join(map(str, looked)))
    return _hold(now == digest and tamper == 0, "GazeWitness HOLDS", "GazeWitness BROKEN", assigned=assigned, looked=looked, digest=digest, tamper=tamper)

def run_pacha(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    ticks = [seed + i for i in range(4)]
    digest = djb2("|".join(map(str, ticks)))
    live = list(ticks)
    if mode == 1:
        live[-1] = live[-2]
    if mode == 2:
        live[-1] = live[-1] + 2
    now = djb2("|".join(map(str, live)))
    mono = all(live[i] == live[i - 1] + 1 for i in range(1, len(live)))
    return _hold(now == digest and mono and mode == 0, "PachaWitness HOLDS", "PachaWitness BROKEN", ticks=live, digest=digest, mode=mode)

def run_tinku(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    a = [djb2(f"a:{seed}:{i}") for i in range(3)]
    b = [djb2(f"b:{seed}:{i}") for i in range(3)]
    knot = djb2("|".join(a + b))
    live_a, live_b = list(a), list(b)
    if mode == 1:
        live_a, live_b = live_b, live_a
    if mode == 2:
        live_a.append(djb2("splice"))
    now = djb2("|".join(live_a + live_b))
    return _hold(now == knot and mode == 0, "TinkuWitness HOLDS", "TinkuWitness BROKEN", streams={"a": live_a, "b": live_b}, digest=knot, mode=mode)

def run_kuti(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    outbound = [djb2(f"out:{seed}:{i}") for i in range(3)]
    home = list(outbound)
    digest = djb2("|".join(outbound + home))
    if mode == 1:
        home[0] = djb2("swap")
    if mode == 2:
        home.pop()
    now = djb2("|".join(outbound + home))
    return _hold(now == digest and home == outbound and mode == 0, "KutiWitness HOLDS", "KutiWitness BROKEN", outbound=outbound, home=home, digest=digest, mode=mode)

def run_yawar(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    line = [djb2(f"yawar:{seed}")]
    for i in range(1, 4):
        line.append(djb2(f"{line[i - 1]}|{seed}|{i}"))
    digest = djb2(">".join(line))
    live = list(line)
    if mode == 1:
        live[-1] = djb2(f"{live[0]}|bastard")
    if mode == 2:
        live.insert(2, djb2("splice"))
    now = djb2(">".join(live))
    return _hold(now == digest and mode == 0, "YawarWitness HOLDS", "YawarWitness BROKEN", line=live, digest=digest, mode=mode)

def run_wasi(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    rooms = ["hearth", "patio", "loft", "well"]
    digest = djb2(f"{seed}|{'/'.join(rooms)}")
    live = list(rooms)
    if mode == 1:
        live.append("annex")
    if mode == 2:
        live.pop()
    now = djb2(f"{seed}|{'/'.join(live)}")
    return _hold(now == digest and mode == 0, "WasiWitness HOLDS", "WasiWitness BROKEN", rooms=live, digest=digest, mode=mode)

def run_sami(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    status, joule = "UNAVAILABLE", None
    digest = djb2(f"{seed}|UNAVAILABLE|null")
    if mode == 1:
        joule = 12.4
    if mode == 2:
        status = "LIVE"
    now = djb2(f"{seed}|{status}|{'null' if joule is None else joule}")
    return _hold(now == digest and mode == 0, "SamiWitness HOLDS", "SamiWitness BROKEN", status=status, joule=joule, digest=digest, mode=mode)

def run_kancha(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    gates = [("east", 0), ("west", 0), ("north", 0)]
    digest = djb2(f"{seed}|" + ",".join(f"{g}:{o}" for g, o in gates))
    live = list(gates)
    if mode == 1:
        live[0] = ("east", 1)
    if mode == 2:
        live.append(("south", 0))
    now = djb2(f"{seed}|" + ",".join(f"{g}:{o}" for g, o in live))
    return _hold(now == digest and mode == 0, "KanchaWitness HOLDS", "KanchaWitness BROKEN", gates=[{"gate": g, "open": o} for g, o in live], digest=digest, mode=mode)

def run_rimay(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    words = ["kay", "pacha", "kawsay"]
    digest = djb2(f"{seed}|{' '.join(words)}")
    live = list(words)
    if mode == 1:
        live[1] = "mundo"
    if mode == 2:
        live.pop()
    now = djb2(f"{seed}|{' '.join(live)}")
    return _hold(now == digest and mode == 0, "RimayWitness HOLDS", "RimayWitness BROKEN", words=live, digest=digest, mode=mode)

def run_nina(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    sparks, joule = 1, None
    digest = djb2(f"{seed}|1|null")
    if mode == 1:
        sparks = 2
    if mode == 2:
        joule = 1.0
    now = djb2(f"{seed}|{sparks}|{'null' if joule is None else joule}")
    return _hold(now == digest and mode == 0, "NinaWitness HOLDS", "NinaWitness BROKEN", sparks=sparks, joule=joule, digest=digest, mode=mode)

def run_suyay(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    promised = 4
    digest = djb2(f"{seed}|wait:{promised}")
    arrived = promised
    if mode == 1:
        arrived = promised - 1
    if mode == 2:
        arrived = promised + 1
    now = djb2(f"{seed}|wait:{arrived}")
    return _hold(now == digest and mode == 0, "SuyayWitness HOLDS", "SuyayWitness BROKEN", promised=promised, arrived=arrived, digest=digest, mode=mode)

def run_huklla(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    left, right = djb2(f"left:{seed}"), djb2(f"right:{seed}")
    digest = djb2(f"{seed}|{left}+{right}")
    live = [left, right]
    if mode == 1:
        live.pop()
    if mode == 2:
        live.reverse()
    now = djb2(f"{seed}|" + "+".join(live))
    return _hold(now == digest and mode == 0, "HukllaWitness HOLDS", "HukllaWitness BROKEN", pair=live, digest=digest, mode=mode)

def loop_tax(attempts, wall_ms, max_budget):
    model_ms = float(sum(float(a["ms"]) for a in attempts))
    peak = float(max((float(a["ms"]) for a in attempts), default=0.0))
    overhead, overhead_label = (None, "UNAVAILABLE") if wall_ms is None else (max(0.0, float(wall_ms) - model_ms), "DERIVED")
    serialization_tax = max(0.0, model_ms - peak)
    dead_hop = 0.0
    for a in attempts:
        if bool(a["ok"]):
            break
        dead_hop += float(a["ms"])
    within = len(attempts) <= int(max_budget)
    any_ok = any(bool(a["ok"]) for a in attempts)
    exit_kind = "budgetExhausted" if not within else ("converged" if any_ok else "aborted")
    return {"modelMs": model_ms, "peakAttemptMs": peak, "overheadMs": overhead, "serializationTaxMs": serialization_tax, "deadHopMs": dead_hop, "withinBudget": within, "exit": exit_kind, "honesty": {"modelMs": "MEASURED", "peakAttemptMs": "MEASURED", "overheadMs": overhead_label, "serializationTaxMs": "DERIVED", "deadHopMs": "DERIVED"}}

def run_ouroboros(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    attempts = [{"ok": False, "ms": 220}, {"ok": True, "ms": 900}]
    wall = None if mode == 2 else 1300.0
    if mode == 1:
        attempts.extend([{"ok": False, "ms": 400}] * 3)
    tax = loop_tax(attempts, wall, 4)
    digest = djb2(f"{seed}|220|900|1300|4")
    wall_key = "1300" if wall == 1300.0 else ("none" if wall is None else str(wall))
    now = djb2(f"{seed}|220|900|{wall_key}|4")
    honest = tax["modelMs"] == 1120 and tax["peakAttemptMs"] == 900 and tax["overheadMs"] == 180 and tax["serializationTaxMs"] == 220 and tax["deadHopMs"] == 220 and tax["exit"] == "converged" and mode == 0 and now == digest
    return _hold(honest, "Ouroboros HOLDS · loop tax MEASURED/DERIVED · not a joule", "Ouroboros BROKEN", tax=tax, digest=digest, mode=mode)

def run_codex(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    head, dco, unsigned, conjecture = "exact-head", 1, 0, "OPEN"
    digest = djb2(f"{seed}|{head}|dco:{dco}|unsigned:{unsigned}|{conjecture}")
    if mode == 1:
        unsigned = 1
    if mode == 2:
        conjecture = "PROVEN"
    now = djb2(f"{seed}|{head}|dco:{dco}|unsigned:{unsigned}|{conjecture}")
    return _hold(unsigned == 0 and dco == 1 and conjecture == "OPEN" and mode == 0 and now == digest, "CodexInvariant HOLDS · exact-head + DCO · Conjecture 1 OPEN", "CodexInvariant BROKEN", head=head, dco=dco, unsigned=unsigned, conjecture=conjecture, digest=digest, mode=mode)

def run_estate(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    org, hf_write, l2 = "szl-holdings", 0, "HOLD"
    digest = djb2(f"{seed}|{org}|hf:{hf_write}|l2:{l2}|UNAVAILABLE")
    if mode == 1:
        org = "SZLHoldings"
    if mode == 2:
        hf_write = 1
    now = djb2(f"{seed}|{org}|hf:{hf_write}|l2:{l2}|UNAVAILABLE")
    audit = {"github_org": org, "github_org_404": "SZLHoldings", "hf_org": "SZLHOLDINGS", "canonical": "szl-holdings/szl-khipu", "hf_write_from_this_sandbox": hf_write, "l2_abstention": l2, "vision": VISION}
    return _hold(org == "szl-holdings" and hf_write == 0 and l2 == "HOLD" and mode == 0 and now == digest, "EstateAudit HOLDS · org is szl-holdings · HF write 0", "EstateAudit BROKEN", audit=audit, digest=digest, mode=mode)

RUNNERS: dict[str, Callable[..., dict[str, Any]]] = {"draft": run_draft, "quorum": run_quorum, "latent": run_latent, "breath": run_breath, "echo": run_echo, "ash": run_ash, "rite": run_rite, "gaze": run_gaze, "pacha": run_pacha, "tinku": run_tinku, "kuti": run_kuti, "yawar": run_yawar, "wasi": run_wasi, "sami": run_sami, "kancha": run_kancha, "rimay": run_rimay, "nina": run_nina, "suyay": run_suyay, "huklla": run_huklla, "ouroboros": run_ouroboros, "codex": run_codex, "estate": run_estate}
FAIL = {name: {"mode": 1} if "mode" in inspect.signature(fn).parameters else {"tamper": 1} for name, fn in RUNNERS.items()}

def selftest() -> int:
    n = 0
    o = run_ouroboros(11, 0)
    assert o["tax"]["modelMs"] == 1120 and o["tax"]["overheadMs"] == 180
    for name, fn in RUNNERS.items():
        honest, broken = fn(11), fn(11, **FAIL[name])
        assert honest["hold"] == 1 and broken["broken"] == 1 and honest["energy_status"] == "UNAVAILABLE" and honest["proven_trust"] is False, name
        n += 1
    print(f"OK {n}")
    return 0

PAGE = """<!doctype html><meta charset=utf-8><title>SZL KHIPU Ñan lab</title>
<style>body{font:14px/1.4 system-ui;background:#0b0c10;color:#e8e6e3;margin:0;padding:24px}.chip{display:inline-block;margin:0 6px 6px 0;padding:2px 8px;border:1px solid #3a3f4b;border-radius:999px;font:11px monospace}button{margin:0 6px 8px 0;padding:6px 10px;background:#16181d;color:#e8e6e3;border:1px solid #3a3f4b;border-radius:8px}.ok{background:#12351f;color:#7dffb3}.bad{background:#3a1512;color:#ffb4a8}pre{background:#111318;padding:12px;border-radius:8px}</style>
<h1>SZL KHIPU Ñan lab</h1><p>v11 LOCKED · Conjecture 1 OPEN · energy UNAVAILABLE</p>
<div id=chips></div><nav id=nav></nav>
<p><button id=fail>Fail-close</button><button id=undo>Undo</button><button id=mint>Mint</button></p>
<p><span id=badge class=ok>HOLDS</span> <span id=reason></span></p><pre id=out></pre>
<script>
const CUTS=%CUTS%,FAIL=%FAIL%;let cut='estate',mode=0,minted=[];
document.getElementById('chips').innerHTML=['Conjecture 1 OPEN','energy UNAVAILABLE','proven_trust false'].map(x=>`<span class=chip>${x}</span>`).join('');
document.getElementById('nav').innerHTML=CUTS.map(c=>`<button data-c=${c}>${c}</button>`).join('');
async function run(){const r=await fetch('/api/'+cut,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({seed:11,...(mode?FAIL[cut]:{})})});const y=await r.json();const hold=y.hold===1;document.getElementById('badge').className=hold?'ok':'bad';document.getElementById('badge').textContent=cut.toUpperCase()+(hold?' HOLDS':' BROKEN');document.getElementById('reason').textContent=y.reason;document.getElementById('out').textContent=JSON.stringify({cut,mode,minted:minted.length,...y},null,2);return y;}
document.getElementById('nav').onclick=e=>{const b=e.target.closest('button');if(!b)return;cut=b.dataset.c;mode=0;run()};
document.getElementById('fail').onclick=()=>{mode=1;run()};
document.getElementById('undo').onclick=()=>{mode=0;run()};
document.getElementById('mint').onclick=async()=>{const y=await run();if(y.hold!==1){document.getElementById('reason').textContent='MINT BLOCKED';return}minted.push({cut,digest:y.digest});run()};
run();
</script>
"""

class H(BaseHTTPRequestHandler):
    def log_message(self, *_a: Any) -> None:
        return
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._send(200, PAGE.replace("%CUTS%", json.dumps(list(RUNNERS))).replace("%FAIL%", json.dumps(FAIL)).encode(), "text/html; charset=utf-8")
        if path == "/api/health":
            return self._send(200, json.dumps({**DOCTRINE, "cuts": list(RUNNERS), "vision": VISION}).encode(), "application/json")
        self._send(404, b'{"error":"nope"}', "application/json")
    def do_POST(self) -> None:
        path = urlparse(self.path).path
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            body = json.loads(raw.decode() or "{}")
        except json.JSONDecodeError:
            body = {}
        name = path.rsplit("/", 1)[-1]
        if name == "djb2":
            s = str(body.get("s", ""))
            return self._send(200, json.dumps({"algo": "djb2", "digest": djb2(s), "energy_status": "UNAVAILABLE", "proven_trust": False}).encode(), "application/json")
        fn = RUNNERS.get(name)
        if not fn:
            return self._send(404, b'{"error":"nope"}', "application/json")
        seed = int(body.get("seed", 11) or 11)
        kwargs = {k: int(body[k]) for k in ("mode", "tamper") if k in body and k in inspect.signature(fn).parameters}
        self._send(200, json.dumps(fn(seed, **kwargs)).encode(), "application/json")

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--serve", type=int, nargs="?", const=8765)
    p.add_argument("--cut", default="estate")
    p.add_argument("--mode", type=int, default=0)
    p.add_argument("--tamper", type=int, default=0)
    a = p.parse_args()
    if a.selftest:
        return selftest()
    if a.serve:
        print(f"SZL KHIPU lab http://127.0.0.1:{a.serve}/ cuts={len(RUNNERS)} energy=UNAVAILABLE")
        ThreadingHTTPServer(("0.0.0.0", a.serve), H).serve_forever()
        return 0
    kwargs = {}
    if a.mode:
        kwargs["mode"] = a.mode
    if a.tamper:
        kwargs["tamper"] = a.tamper
    print(json.dumps(RUNNERS[a.cut](11, **kwargs), indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
