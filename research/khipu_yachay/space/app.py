"""SZL Khipu-Yachay Space: offline-first, read-only modern demonstration.

No secrets, models fetched at runtime, archaeological image scraping, server
jobs, uploads, user tracking, persistent writes, or model promotion endpoints.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit, parse_qs

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.core import answer, evaluate_cords, load_model, canonical, sha256

MODEL_FILE = ROOT / "model" / "yachay_nb_v0.json"
RECEIPT_FILE = ROOT / "model" / "training_receipt.json"
SOURCES_FILE = ROOT / "data" / "sources.jsonl"
IDS_FILE = ROOT / "data" / "okr_kh_index.jsonl"


def load_state(root: Path = ROOT) -> dict:
    model_path = root / "model" / "yachay_nb_v0.json"
    receipt_path = root / "model" / "training_receipt.json"
    model = load_model(model_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if sha256(model_path.read_bytes()) != receipt["data"]["model/yachay_nb_v0.json"]["sha256"]:
        raise ValueError("MODEL_SOURCE_BINDING_FAILED")
    if receipt.get("external_data_training") is not False:
        raise ValueError("TRAINING_DATA_CLASS_MISMATCH")
    source_rows = [json.loads(line) for line in (root / "data/sources.jsonl").read_text(encoding="utf-8").splitlines() if line]
    ids = [json.loads(line)["kh_id"] for line in (root / "data/okr_kh_index.jsonl").read_text(encoding="utf-8").splitlines() if line]
    if len(set(ids)) != 702 or ids != [f"KH{i:04d}" for i in range(1, 703)]:
        raise ValueError("KH_IDENTIFIERS_NOT_VERIFIED")
    sources = {x["source_id"]: x for x in source_rows}
    if len(sources) != len(source_rows):
        raise ValueError("DUPLICATE_SOURCE_ID")
    return {"model": model, "receipt": receipt, "sources": sources,
            "kh_ids": frozenset(ids), "model_sha256": sha256(model_path.read_bytes())}


def strict_pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("DUPLICATE_FIELD")
        obj[key] = value
    return obj


def analyze(body: dict, state: dict) -> dict:
    if type(body) is not dict or set(body) != {"cords", "declared_total", "question", "kh_id"}:
        raise ValueError("EXACT_INPUT_SCHEMA")
    if not isinstance(body["question"], str) or len(body["question"]) > 500:
        raise ValueError("QUESTION_LENGTH")
    kid = body["kh_id"]
    if kid is not None and (type(kid) is not str or not re.fullmatch(r"KH[0-9]{4}", kid)):
        raise ValueError("INVALID_KH_ID")
    arithmetic = evaluate_cords(body["cords"], body["declared_total"])
    routed = answer(body["question"], state["model"], state["sources"])
    reference = None
    if kid is not None:
        if kid not in state["kh_ids"]:
            reference = {"status": "UNAVAILABLE_IN_PINNED_REGISTRY", "kh_id": kid}
        else:
            reference = {"status": "ARCHIVAL_IDENTIFIER_ONLY", "kh_id": kid,
                         "source_id": "OKR_2_1", "source_url": state["sources"]["OKR_2_1"]["url"],
                         "numerical_cord_values_loaded": False}
    result = {"schema": "szl.khipu-yachay.interactive/v0", "state": "RESEARCH_ONLY",
              "arithmetic": arithmetic, "route": routed, "reference": reference,
              "model_sha256": state["model_sha256"],
              "model_training_class": "SYNTHETIC_NAIVE_BAYES_INTENT_ROUTER",
              "arithmetic_authority": "DETERMINISTIC_COMPLETE_INPUT_ONLY",
              "archaeological_decipherment": "NOT_CLAIMED",
              "historical_training": "NOT_PERFORMED",
              "rights_clearance_for_other_assets": "NOT_ESTABLISHED",
              "production_qualified": False}
    result["response_sha256"] = sha256(canonical(result))
    return result


class Handler(BaseHTTPRequestHandler):
    state = None
    server_version = "SZLKhipuYachay/0.1"
    sys_version = ""

    def _send(self, code: int, content: bytes, mime="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; connect-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(content)

    def _err(self, code, reason):
        self._send(code, canonical({"schema": "szl.khipu-yachay.error/v0", "state": "UNAVAILABLE", "reason": reason}))

    def do_GET(self):
        page = urlsplit(self.path)
        if page.path == "/":
            raw = (ROOT / "space/index.html").read_bytes()
            self._send(200, raw, "text/html; charset=utf-8")
        elif page.path in {"/assets/app.js", "/assets/style.css"}:
            name = page.path.rsplit("/", 1)[1]
            mime = "text/javascript; charset=utf-8" if name.endswith(".js") else "text/css; charset=utf-8"
            self._send(200, (ROOT / "space" / name).read_bytes(), mime)
        elif page.path == "/api/healthz":
            self._send(200, canonical({"state": "RESEARCH_PREVIEW", "model_loaded": True,
                                       "real_weights_trained": True, "historical_training": False,
                                       "production_qualified": False, "archival_ids": len(self.state["kh_ids"])}))
        elif page.path == "/api/sources":
            queries = parse_qs(page.query, keep_blank_values=True)
            if set(queries) - {"q"} or any(len(v) != 1 for v in queries.values()):
                return self._err(422, "INVALID_QUERY")
            q = queries.get("q", [""])[0].lower()
            if len(q) > 80:
                return self._err(422, "QUERY_TOO_LONG")
            matching = [dict(x) for x in self.state["sources"].values()
                        if q in x["title"].lower() or q in x["source_id"].lower()]
            self._send(200, canonical({"state": "SOURCE_REGISTRY_ONLY", "count": len(matching),
                                       "sources": matching[:20]}))
        else:
            self._err(404, "ROUTE_NOT_FOUND")

    def do_POST(self):
        if self.path != "/api/analyze":
            return self._err(404, "ROUTE_NOT_FOUND")
        if len(self.headers.get_all("Content-Length", [])) != 1 or self.headers.get("Transfer-Encoding") is not None:
            return self._err(400, "AMBIGUOUS_BODY_FRAMING")
        size = self.headers.get("Content-Length", "")
        if not size.isascii() or not re.fullmatch(r"[0-9]{1,5}", size):
            return self._err(411, "CONTENT_LENGTH_REQUIRED")
        size = int(size)
        if not 0 < size <= 4096:
            return self._err(413, "REQUEST_TOO_LARGE")
        try:
            payload = json.loads(self.rfile.read(size).decode("utf-8"), object_pairs_hook=strict_pairs,
                                 parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NONFINITE_JSON")))
            result = analyze(payload, self.state)
        except (ValueError, UnicodeError, TypeError):
            return self._err(422, "INVALID_INPUT")
        self._send(200, canonical(result))

    def log_message(self, format, *args):
        # Avoid collecting user questions, origins and private network identifiers.
        return


def make_server(host="127.0.0.1", port=0):
    state = load_state()
    class BoundHandler(Handler):
        pass
    BoundHandler.state = state
    return ThreadingHTTPServer((host, port), BoundHandler)


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "7860"))
    server = make_server(host, port)
    print("SZL Khipu-Yachay research preview; no model download, no training, no production approval", flush=True)
    server.serve_forever(poll_interval=0.2)
