# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Stdlib holographic frontend + JSON kernel backend.

One process. Python serves the UI and runs the kernels. No Gradio, no Flask.
Never paints proven_trust true. Never fabricates a joule. Λ stays Conjecture 1 OPEN.

    python -m szl_khipu.http_app --host 0.0.0.0 --port 7860
    szl-khipu serve
"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import numpy as np

from szl_khipu import (
    YUYAY_AXES,
    YUYAY_FLOORS,
    UnifiedReceiptChain,
    evaluate_anatomy,
    evaluate_greenlight,
    evaluate_lambda,
    run_tile_grid,
    yarqa_attn,
)
from szl_khipu.doctrine import DOCTRINE, proven_trust

SOURCE = "szl-holdings/szl-khipu"
CHAIN = UnifiedReceiptChain()
PAGE_PATH = Path(__file__).with_name("page.html")


def _page() -> str:
    return (
        PAGE_PATH.read_text(encoding="utf-8")
        .replace("__AXES__", json.dumps(list(YUYAY_AXES)))
        .replace("__FLOORS__", json.dumps([float(x) for x in YUYAY_FLOORS]))
    )


def _stamp(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    out.setdefault("proven_trust", False)
    out.setdefault("energy_status", "UNAVAILABLE")
    out.setdefault("energy_j", None)
    out.setdefault("conjecture_1", "OPEN")
    out.setdefault("doctrine", DOCTRINE["version"])
    out.setdefault("source", SOURCE)
    if proven_trust is True:
        raise RuntimeError("refusing proven_trust true")
    return out


def api_lambda(body: dict[str, Any]) -> dict[str, Any]:
    axes = body.get("axes") or list(YUYAY_FLOORS)
    axes = [float(x) for x in axes]
    if body.get("zero") is not None:
        i = int(body["zero"])
        if 0 <= i < len(axes):
            axes[i] = 0.0
    ev = evaluate_lambda(axes)
    CHAIN.emit("lambda", "evaluate", {"value": ev["value"], "blocked": ev["blocked"]})
    return _stamp(
        {
            "value": ev["value"],
            "blocked": bool(ev["blocked"]),
            "reason": ev["reason"],
            "axioms": ev["axioms"],
            "advisory": True,
        }
    )


def api_anatomy(body: dict[str, Any]) -> dict[str, Any]:
    ev = evaluate_anatomy(
        seed=int(body.get("seed", 11)),
        zero_heart=bool(body.get("zero_heart")),
        leak_canal=bool(body.get("leak_canal")),
        tamper_chain=bool(body.get("tamper_chain")),
        fabricate_joule=bool(body.get("fabricate_joule")),
        break_skeleton=bool(body.get("break_skeleton")),
        willay_fire=bool(body.get("willay_fire")),
    )
    CHAIN.emit("anatomy", "evaluate", {"blocked": ev.get("blocked"), "live_count": ev.get("live_count")})
    return _stamp(dict(ev))


def _flag(body: dict[str, Any], *keys: str) -> int:
    for k in keys:
        if k not in body:
            continue
        v = body[k]
        if isinstance(v, bool):
            return 1 if v else 0
        if isinstance(v, (int, float)):
            return 1 if v == 1 else 0
        if str(v).lower() in ("1", "true", "yes"):
            return 1
        return 0
    return 0


def api_greenlight(body: dict[str, Any]) -> dict[str, Any]:
    ev = evaluate_greenlight(
        paint_sorry=_flag(body, "paint_sorry", "paintSorry"),
        claim_proven=_flag(body, "claim_proven", "claimProven"),
        stamp_joule=_flag(body, "stamp_joule", "stampJoule"),
    )
    CHAIN.emit("greenlight", "evaluate", {"blocked": ev.get("blocked"), "greenlit": ev.get("greenlit")})
    return _stamp(dict(ev))


def api_yarqa(body: dict[str, Any]) -> dict[str, Any]:
    rng = np.random.default_rng(int(body.get("seed", 7)))
    seq = int(body.get("seq", 12))
    dim = int(body.get("dim", 4))
    n_canals = int(body.get("n_canals", 3))
    q = k = v = rng.standard_normal((seq, dim))
    out, _probs, leaked = yarqa_attn(q, k, v, n_canals=n_canals)
    CHAIN.emit("yarqa", "attn", {"leaked": float(leaked), "n_canals": n_canals})
    return _stamp(
        {
            "n_canals": n_canals,
            "seq": seq,
            "dim": dim,
            "leaked": float(leaked),
            "shape": list(out.shape),
            "cuda": "UNAVAILABLE",
        }
    )


def api_tiledigest(body: dict[str, Any]) -> dict[str, Any]:
    tamper = int(body.get("tamper", 0))
    y = run_tile_grid(8, 4, 4, 4, tamper)
    CHAIN.emit("tiledigest", "run", {"tamper": tamper, "gridBreaks": y.get("gridBreaks")})
    return _stamp(dict(y))


def api_version() -> dict[str, Any]:
    ok, depth, brk = CHAIN.verify()
    return _stamp(
        {
            "name": "szl-khipu",
            "source": SOURCE,
            "chain_ok": bool(ok),
            "chain_depth": int(depth),
            "chain_break": brk,
            "locked_proven": DOCTRINE["lockedProvenCount"],
            "cuda": "UNAVAILABLE",
            "frontend": "python-stdlib",
            "backend": "numpy",
        }
    )


ROUTES = {
    "/api/lambda": api_lambda,
    "/api/anatomy": api_anatomy,
    "/api/greenlight": api_greenlight,
    "/api/yarqa": api_yarqa,
    "/api/tiledigest": api_tiledigest,
}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code: int, payload: Any, content_type: str = "application/json") -> None:
        if isinstance(payload, (dict, list)):
            raw = json.dumps(payload, sort_keys=True).encode("utf-8")
        elif isinstance(payload, str):
            raw = payload.encode("utf-8")
        else:
            raw = bytes(payload)
        self.send_response(code)
        self.send_header("content-type", content_type + ("" if "charset" in content_type else "; charset=utf-8"))
        self.send_header("content-length", str(len(raw)))
        self.send_header("cache-control", "no-store")
        self.send_header("access-control-allow-origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("access-control-allow-origin", "*")
        self.send_header("access-control-allow-methods", "GET,POST,OPTIONS")
        self.send_header("access-control-allow-headers", "content-type")
        self.end_headers()

    def do_HEAD(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in ("/", "/index.html", "/healthz", "/version", "/api/version") or path in ROUTES:
            self.send_response(200)
            ctype = "text/html; charset=utf-8" if path in ("/", "/index.html") else "application/json"
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        self.send_response(404)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send(200, _page(), "text/html")
            return
        if path == "/healthz":
            self._send(200, {"ok": True, "transport": "up", "proven_trust": False})
            return
        if path in ("/version", "/api/version"):
            self._send(200, api_version())
            return
        if path == "/.well-known/szl-source.json":
            self._send(200, api_version())
            return
        if path in ROUTES:
            qs = parse_qs(urlparse(self.path).query)
            body = {k: v[0] if len(v) == 1 else v for k, v in qs.items()}
            if "axes" in body and isinstance(body["axes"], str):
                body["axes"] = [float(x) for x in body["axes"].split(",") if x]
            self._send(200, ROUTES[path](body))
            return
        self._send(404, {"error": "not found", "proven_trust": False})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path not in ROUTES:
            self._send(404, {"error": "not found", "proven_trust": False})
            return
        length = int(self.headers.get("content-length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
            if not isinstance(body, dict):
                raise ValueError("body must be an object")
        except (json.JSONDecodeError, ValueError) as exc:
            self._send(400, {"error": str(exc), "proven_trust": False})
            return
        try:
            self._send(200, ROUTES[path](body))
        except Exception as exc:  # noqa: BLE001 — surface kernel fail-closed, never a fake 200
            self._send(400, {"error": str(exc), "blocked": True, "proven_trust": False})


def make_server(host: str = "0.0.0.0", port: int = 7860) -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.allow_reuse_address = True
    return httpd


def serve(host: str = "0.0.0.0", port: int = 7860) -> None:
    httpd = make_server(host, port)
    print(json.dumps({"serve": f"http://{host}:{port}/", "proven_trust": False, "energy_status": "UNAVAILABLE"}))
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="SZL KHIPU Python frontend + backend")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=7860)
    args = p.parse_args(argv)
    serve(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
