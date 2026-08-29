#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""SZL KHIPU hologram — stdlib HTTP on 7860. No Gradio. No npm.

Imports szl_khipu when the package is on PYTHONPATH / next to this file.
Otherwise kernels report honest UNAVAILABLE and Λ falls back to a stdlib WGM.
Uniqueness of Λ is Conjecture 1 — never a theorem.
"""
from __future__ import annotations

import json
import math
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
if (ROOT / "szl_khipu").is_dir():
    sys.path.insert(0, str(ROOT))
elif (ROOT.parent / "szl_khipu").is_dir():
    sys.path.insert(0, str(ROOT.parent))

HTML = ROOT / "index.html"

try:
    from energy import probe as _energy_probe
except ImportError:
    def _energy_probe(*, sample_s: float = 0.0):
        return {
            "channel": "LIVE",
            "honesty": "UNAVAILABLE",
            "source": None,
            "energy_j": None,
            "note": "No RAPL, no NVML. Channel is live. Never a fabricated joule.",
        }

KERNEL = "UNAVAILABLE"
_evaluate_lambda = None
_yarqa_attn = None
_evaluate_anatomy = None
_evaluate_greenlight = None
_api_extra: dict = {}
YUYAY_FLOORS: tuple[float, ...] = (0.95, 0.95) + (0.90,) * 11

try:
    from szl_khipu import (  # type: ignore
        YUYAY_FLOORS as _FLOORS,
        evaluate_anatomy as _ea,
        evaluate_greenlight as _eg,
        evaluate_lambda as _el,
        yarqa_attn as _ya,
    )
    from szl_khipu.http_app import (  # type: ignore
        api_bench,
        api_infer,
        api_prefix,
        api_route,
    )

    YUYAY_FLOORS = tuple(float(x) for x in _FLOORS)
    _evaluate_lambda = _el
    _yarqa_attn = _ya
    _evaluate_anatomy = _ea
    _evaluate_greenlight = _eg
    _api_extra = {
        "/api/prefix": api_prefix,
        "/api/route": api_route,
        "/api/bench": api_bench,
        "/api/infer": api_infer,
    }
    KERNEL = "LIVE"
except Exception:
    KERNEL = "UNAVAILABLE"


def _stdlib_wgm(axes: list[float]) -> float:
    if not axes:
        raise ValueError("axes empty")
    if any(x < 0 for x in axes):
        raise ValueError("axes must be >= 0")
    if any(x == 0 for x in axes):
        return 0.0
    w = 1.0 / len(axes)
    return math.exp(sum(w * math.log(x) for x in axes))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        return

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, payload: dict) -> None:
        self._send(code, json.dumps(payload).encode(), "application/json")

    def do_HEAD(self) -> None:  # noqa: N802
        """HF probes HEAD. BaseHTTP 501s otherwise."""
        path = urlparse(self.path).path
        ok = path in (
            "/",
            "/index.html",
            "/health",
            "/healthz",
            "/readyz",
            "/version",
            "/api/version",
            "/api/lambda",
            "/api/energy",
            "/api/greenlight",
            "/api/anatomy",
            "/api/yarqa",
            "/api/prefix",
            "/api/route",
            "/api/bench",
            "/api/infer",
        )
        if not ok:
            self.send_response(404)
            self.end_headers()
            return
        ctype = "text/html; charset=utf-8" if path in ("/", "/index.html") else "application/json"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            body = HTML.read_bytes() if HTML.is_file() else b"<h1>SZL KHIPU</h1>"
            self._send(200, body, "text/html; charset=utf-8")
            return
        if path in ("/health", "/healthz", "/readyz"):
            energy = _energy_probe()
            self._json(
                200,
                {
                    "ok": True,
                    "space": "szl-khipu",
                    "kernel": KERNEL,
                    "uniqueness": "Conjecture 1",
                    "energy": energy,
                    "proven_trust": False,
                    "cuda": "UNAVAILABLE",
                },
            )
            return
        if path == "/api/energy":
            self._json(200, _energy_probe())
            return
        if path in ("/version", "/api/version"):
            self._json(
                200,
                {
                    "name": "szl-khipu",
                    "kernel": KERNEL,
                    "uniqueness": "Conjecture 1",
                    "energy": "UNAVAILABLE",
                    "proven_trust": False,
                    "source": "szl-holdings/szl-khipu",
                },
            )
            return
        if path == "/api/lambda":
            self._lambda({})
            return
        if path == "/api/greenlight":
            self._greenlight({})
            return
        if path == "/api/anatomy":
            self._anatomy({})
            return
        if path == "/api/yarqa":
            self._yarqa({})
            return
        if path in _api_extra:
            self._json(200, _api_extra[path]({}))
            return
        self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            data = json.loads(raw.decode())
        except Exception:
            data = {}
        if path == "/api/lambda":
            self._lambda(data)
            return
        if path == "/api/yarqa":
            self._yarqa(data)
            return
        if path == "/api/anatomy":
            self._anatomy(data)
            return
        if path == "/api/greenlight":
            self._greenlight(data)
            return
        if path in _api_extra:
            self._json(200, _api_extra[path](data if isinstance(data, dict) else {}))
            return
        self._send(404, b"not found", "text/plain")

    def _lambda(self, data: dict) -> None:
        axes = [float(x) for x in (data.get("axes") or list(YUYAY_FLOORS))]
        try:
            if _evaluate_lambda is not None:
                ev = _evaluate_lambda(axes)
                value = float(ev["value"])
                blocked = bool(ev["blocked"])
                reason = str(ev["reason"])
            else:
                value = _stdlib_wgm(axes)
                blocked = value == 0.0 or (len(axes) >= 2 and (axes[0] < 0.95 or axes[1] < 0.95))
                reason = "stdlib WGM fallback — szl_khipu UNAVAILABLE"
            self._json(
                200,
                {
                    "lambda": value,
                    "blocked": blocked,
                    "decision": "BLOCKED" if blocked else "ADMITTED",
                    "reason": reason,
                    "uniqueness": "Conjecture 1",
                    "kernel": KERNEL,
                    "proven_trust": False,
                    "energy": "UNAVAILABLE",
                },
            )
        except Exception as exc:
            self._json(400, {"error": str(exc), "kernel": KERNEL, "honesty": "MEASURED"})

    def _yarqa(self, data: dict) -> None:
        n = int(data.get("n_canals") or 3)
        if _yarqa_attn is None:
            self._json(
                200,
                {
                    "leaked": None,
                    "n_canals": n,
                    "kernel": "UNAVAILABLE",
                    "reason": "szl_khipu UNAVAILABLE — not a CUDA stand-in",
                    "cuda": "UNAVAILABLE",
                },
            )
            return
        try:
            import numpy as np

            rng = np.random.default_rng(7)
            seq, dim = 12, 4
            q = rng.standard_normal((seq, dim))
            k = rng.standard_normal((seq, dim))
            v = rng.standard_normal((seq, dim))
            _out, _probs, leaked = _yarqa_attn(q, k, v, n)
            leak = float(leaked)
            self._json(
                200,
                {
                    "leaked": leak,
                    "n_canals": n,
                    "ok": leak <= 1e-9,
                    "kernel": KERNEL,
                    "cuda": "UNAVAILABLE",
                    "uniqueness": "Conjecture 1",
                },
            )
        except Exception as exc:
            self._json(400, {"error": str(exc), "kernel": KERNEL})

    def _anatomy(self, data: dict) -> None:
        if _evaluate_anatomy is None:
            self._json(
                200,
                {
                    "live_count": None,
                    "blocked": True,
                    "kernel": "UNAVAILABLE",
                    "reason": "szl_khipu UNAVAILABLE — organs not fabricated",
                    "energy": "UNAVAILABLE",
                    "proven_trust": False,
                },
            )
            return
        try:
            ev = _evaluate_anatomy(
                zero_heart=bool(data.get("zero_heart")),
                leak_canal=bool(data.get("leak_canal")),
                tamper_chain=bool(data.get("tamper_chain")),
                fabricate_joule=bool(data.get("fabricate_joule")),
                break_skeleton=bool(data.get("break_skeleton")),
                willay_fire=bool(data.get("willay_fire")),
                seed=11,
            )
            self._json(
                200,
                {
                    "live_count": int(ev["live_count"]),
                    "blocked": bool(ev["blocked"]),
                    "reason": str(ev["reason"]),
                    "organs": list(ev.get("organs") or []),
                    "kernel": KERNEL,
                    "energy": "UNAVAILABLE",
                    "proven_trust": False,
                    "uniqueness": "Conjecture 1",
                },
            )
        except Exception as exc:
            self._json(400, {"error": str(exc), "kernel": KERNEL})

    def _greenlight(self, data: dict) -> None:
        def _flag(*keys: str) -> int:
            for k in keys:
                if k not in data:
                    continue
                v = data[k]
                if isinstance(v, bool):
                    return 1 if v else 0
                if isinstance(v, (int, float)):
                    return 1 if v == 1 else 0
                if str(v).lower() in ("1", "true", "yes"):
                    return 1
                return 0
            return 0

        paint = _flag("paint_sorry", "paintSorry")
        claim = _flag("claim_proven", "claimProven")
        joule = _flag("stamp_joule", "stampJoule")
        if _evaluate_greenlight is not None:
            try:
                ev = _evaluate_greenlight(paint_sorry=paint, claim_proven=claim, stamp_joule=joule)
                self._json(
                    200,
                    {
                        "painted": int(ev["painted"]),
                        "blocked": bool(ev["blocked"]),
                        "greenlit": int(ev["greenlit"]),
                        "reason": str(ev["reason"]),
                        "checks": ev.get("checks"),
                        "kernel": KERNEL,
                        "energy": "UNAVAILABLE",
                        "proven_trust": False,
                        "uniqueness": "Conjecture 1",
                    },
                )
                return
            except Exception as exc:
                self._json(400, {"error": str(exc), "kernel": KERNEL, "proven_trust": False})
                return
        checks = [
            {"id": "sorry", "ok": paint != 1, "detail": "BLOCKED · a sorry cannot be painted green" if paint == 1 else "sorry stays sorry · locked-8 is 8, not 21"},
            {"id": "conjecture1", "ok": claim != 1, "detail": "BLOCKED · proven_trust cannot be true while Λ is Conjecture 1" if claim == 1 else "proven_trust locked false · uniqueness OPEN"},
            {"id": "energy", "ok": joule != 1, "detail": "BLOCKED · fabricated joule · energy UNAVAILABLE" if joule == 1 else "energy UNAVAILABLE · never a fabricated joule"},
        ]
        painted = sum(1 for c in checks if not c["ok"])
        blocked = painted > 0
        self._json(
            200,
            {
                "painted": painted,
                "blocked": blocked,
                "greenlit": 0 if blocked else 1,
                "reason": next((c["detail"] for c in checks if not c["ok"]), "GREEN-LIGHT · LIVE bound · proven_trust false · energy UNAVAILABLE") if blocked else "GREEN-LIGHT · LIVE bound · proven_trust false · energy UNAVAILABLE",
                "checks": checks,
                "kernel": KERNEL,
                "energy": "UNAVAILABLE",
                "proven_trust": False,
                "uniqueness": "Conjecture 1",
            },
        )


def main() -> None:
    port = int(os.environ.get("PORT", "7860"))
    httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"szl-khipu hologram listening 0.0.0.0:{port} kernel={KERNEL}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
