#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""SZL KHIPU hologram — stdlib HTTP on 7860. No Gradio. No npm.

Imports szl_khipu when the package is on PYTHONPATH / next to this file.
Otherwise kernels report honest UNAVAILABLE and Λ falls back to a stdlib WGM.
Uniqueness of Λ is Conjecture 1 — never a theorem.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import sys
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
if (ROOT / "szl_khipu").is_dir():
    sys.path.insert(0, str(ROOT))
elif (ROOT.parent / "szl_khipu").is_dir():
    sys.path.insert(0, str(ROOT.parent))

HTML = ROOT / "index.html"
BUILD_INFO = ROOT / "szl_khipu" / "build-info.json"
PROVENANCE = ROOT / "szl_khipu" / "hf-deployment-provenance.json"
SOURCE_REPOSITORY = "szl-holdings/szl-khipu"
HF_REPOSITORY = "SZLHOLDINGS/szl-khipu"
WORKFLOW_NAME = "publish-hf"
ARTIFACT_NAME = "szl-khipu-hf-provenance"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _canonical_json(payload: dict) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _url_bytes(url: str, *, limit: int = 8 * 1024 * 1024) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "szl-khipu-source-verifier/2",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        content = response.read(limit + 1)
    if len(content) > limit:
        raise ValueError("evidence response exceeds the bounded size")
    return content


def _url_json(url: str) -> dict:
    payload = json.loads(_url_bytes(url, limit=2 * 1024 * 1024).decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("evidence response must be a JSON object")
    return payload


def _running_hf_revision(expected: str, hf_repository: str) -> str | None:
    if "SPACE_COMMIT" in os.environ:
        revision = str(os.environ.get("SPACE_COMMIT") or "").lower()
        return revision if SHA40.fullmatch(revision) and revision == expected else None
    try:
        payload = _url_json(f"https://huggingface.co/api/spaces/{hf_repository}")
    except Exception:
        return None
    revision = str(payload.get("sha") or "").lower()
    runtime = payload.get("runtime")
    stage = str(runtime.get("stage") or "") if isinstance(runtime, dict) else ""
    return revision if revision == expected and stage == "RUNNING" else None


def _payload_records(root: Path) -> list[dict]:
    excluded = set()
    for evidence in (BUILD_INFO, PROVENANCE):
        try:
            excluded.add(evidence.relative_to(root).as_posix())
        except ValueError:
            pass
    records = []
    for path in sorted((item for item in root.rglob("*") if item.is_file())):
        relative = path.relative_to(root)
        if relative.as_posix() in excluded:
            continue
        if any(part in {".git", "__pycache__"} for part in relative.parts):
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        content = path.read_bytes()
        records.append(
            {
                "path": relative.as_posix(),
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
            }
        )
    return records


def _validated_manifest(metadata: dict, manifest_bytes: bytes) -> dict:
    if hashlib.sha256(manifest_bytes).hexdigest() != metadata["manifest_sha256"]:
        raise ValueError("deployment manifest digest mismatch")
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema") != "szl.hf-deployment-tree/v2":
        raise ValueError("invalid deployment manifest schema")
    for field in (
        "source_repository",
        "source_commit",
        "hf_repository",
        "workflow_name",
        "workflow_run_id",
        "workflow_run_attempt",
        "artifact_name",
        "tree_sha256",
    ):
        if manifest.get(field) != metadata.get(field):
            raise ValueError(f"deployment manifest {field} mismatch")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("deployment manifest has no files")
    normalized = []
    seen = set()
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "sha256", "size"}:
            raise ValueError("invalid deployment manifest file record")
        relative = str(item.get("path") or "")
        parts = relative.split("/")
        if not relative or relative.startswith("/") or "\\" in relative or ".." in parts:
            raise ValueError("unsafe deployment manifest path")
        digest = str(item.get("sha256") or "").lower()
        size = item.get("size")
        if relative in seen or not SHA256.fullmatch(digest):
            raise ValueError("invalid or duplicate deployment manifest file")
        if not isinstance(size, int) or size < 0:
            raise ValueError("invalid deployment manifest file size")
        seen.add(relative)
        normalized.append({"path": relative, "sha256": digest, "size": size})
    if normalized != sorted(normalized, key=lambda item: item["path"]):
        raise ValueError("deployment manifest files are not canonical")
    core = {key: value for key, value in manifest.items() if key != "tree_sha256"}
    tree_sha256 = hashlib.sha256(_canonical_json(core)).hexdigest()
    if tree_sha256 != metadata["tree_sha256"]:
        raise ValueError("deployment tree digest mismatch")
    if _payload_records(ROOT) != normalized:
        raise ValueError("running deployment files do not match the attested tree")
    return manifest


def _github_evidence(metadata: dict, manifest_bytes: bytes) -> tuple[dict, str]:
    run_id = metadata["workflow_run_id"]
    base = f"https://api.github.com/repos/{SOURCE_REPOSITORY}"
    run = _url_json(f"{base}/actions/runs/{run_id}")
    repository = run.get("repository")
    if (
        run.get("id") != run_id
        or str(run.get("head_sha") or "").lower() != metadata["source_commit"]
        or run.get("head_branch") != "main"
        or run.get("event") not in {"push", "workflow_dispatch"}
        or run.get("name") != WORKFLOW_NAME
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
        or not isinstance(repository, dict)
        or repository.get("full_name") != SOURCE_REPOSITORY
    ):
        raise ValueError("GitHub workflow run is not an exact successful source run")

    listing = _url_json(
        f"{base}/actions/runs/{run_id}/artifacts?name={ARTIFACT_NAME}&per_page=100"
    )
    artifacts = listing.get("artifacts")
    matches = [
        item
        for item in artifacts or []
        if isinstance(item, dict) and item.get("name") == ARTIFACT_NAME
    ]
    if len(matches) != 1:
        raise ValueError("exact GitHub deployment artifact unavailable")
    artifact = matches[0]
    workflow_run = artifact.get("workflow_run")
    digest = str(artifact.get("digest") or "").lower()
    artifact_id = artifact.get("id")
    if (
        artifact.get("expired") is not False
        or not isinstance(artifact_id, int)
        or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest)
        or not isinstance(workflow_run, dict)
        or workflow_run.get("id") != run_id
        or str(workflow_run.get("head_sha") or "").lower() != metadata["source_commit"]
    ):
        raise ValueError("GitHub deployment artifact metadata is invalid")

    archive_bytes = _url_bytes(f"{base}/actions/artifacts/{artifact_id}/zip")
    if hashlib.sha256(archive_bytes).hexdigest() != digest.removeprefix("sha256:"):
        raise ValueError("GitHub deployment artifact digest mismatch")
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        names = sorted(name for name in archive.namelist() if not name.endswith("/"))
        if names != ["hf-deployment-provenance.json", "hf-deployment-receipt.json"]:
            raise ValueError("GitHub deployment artifact has an unexpected file set")
        archived_manifest = archive.read("hf-deployment-provenance.json")
        receipt_bytes = archive.read("hf-deployment-receipt.json")
    if archived_manifest != manifest_bytes:
        raise ValueError("GitHub artifact does not attest the running deployment manifest")
    receipt = json.loads(receipt_bytes.decode("utf-8"))
    if not isinstance(receipt, dict) or receipt.get("schema") != "szl.hf-deployment-receipt/v2":
        raise ValueError("invalid GitHub deployment receipt")
    for field in (
        "source_repository",
        "source_commit",
        "hf_repository",
        "workflow_name",
        "workflow_run_id",
        "workflow_run_attempt",
        "artifact_name",
        "manifest_sha256",
        "tree_sha256",
    ):
        if receipt.get(field) != metadata.get(field):
            raise ValueError(f"GitHub deployment receipt {field} mismatch")
    hf_revision = str(receipt.get("hf_revision") or "").lower()
    if not SHA40.fullmatch(hf_revision):
        raise ValueError("GitHub deployment receipt has no immutable HF revision")
    receipt["hf_revision"] = hf_revision
    return receipt, digest.removeprefix("sha256:")


def _source_document(schema: str) -> tuple[dict, str | None]:
    try:
        metadata = json.loads(BUILD_INFO.read_text(encoding="utf-8"))
        if not isinstance(metadata, dict) or metadata.get("schema") != "szl.hf-build-info/v2":
            raise ValueError("invalid build metadata schema")
        if metadata.get("source_repository") != SOURCE_REPOSITORY:
            raise ValueError("invalid source repository")
        if metadata.get("hf_repository") != HF_REPOSITORY:
            raise ValueError("invalid Hugging Face repository")
        if metadata.get("workflow_name") != WORKFLOW_NAME:
            raise ValueError("invalid deployment workflow")
        if metadata.get("artifact_name") != ARTIFACT_NAME:
            raise ValueError("invalid deployment artifact name")
        for key in ("source_commit", "manifest_sha256", "tree_sha256"):
            pattern = SHA40 if key == "source_commit" else SHA256
            value = str(metadata.get(key) or "").lower()
            if not pattern.fullmatch(value):
                raise ValueError(f"invalid {key}")
            metadata[key] = value
        for key in ("workflow_run_id", "workflow_run_attempt"):
            value = metadata.get(key)
            if not isinstance(value, int) or value <= 0:
                raise ValueError(f"invalid {key}")
        manifest_bytes = PROVENANCE.read_bytes()
        _validated_manifest(metadata, manifest_bytes)
        receipt, artifact_sha256 = _github_evidence(metadata, manifest_bytes)
        hf_revision = _running_hf_revision(receipt["hf_revision"], HF_REPOSITORY)
        if hf_revision is None:
            raise ValueError("running Hugging Face revision does not match the deployment receipt")
    except Exception as exc:
        return {"schema": schema, "state": "UNKNOWN"}, str(exc)
    return {
        "schema": schema,
        "state": "SOURCE_BOUND_DEPLOYMENT",
        "source": {
            "repository": SOURCE_REPOSITORY,
            "commit": metadata["source_commit"],
        },
        "deployment": {
            "hf_repository": HF_REPOSITORY,
            "hf_revision": hf_revision,
            "workflow_run": metadata["workflow_run_id"],
            "workflow_run_attempt": metadata["workflow_run_attempt"],
            "workflow_name": WORKFLOW_NAME,
            "artifact_name": ARTIFACT_NAME,
            "artifact_sha256": artifact_sha256,
            "manifest_sha256": metadata["manifest_sha256"],
            "runtime_tree_sha256": metadata["tree_sha256"],
        },
    }, None

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
        if path in ("/api/build-info", "/.well-known/szl-source.json"):
            schema = (
                "szl.build-info/v1"
                if path == "/api/build-info"
                else "szl.deployment-source/v1"
            )
            _payload, error = _source_document(schema)
            self.send_response(503 if error else 200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
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
        if path in ("/api/build-info", "/.well-known/szl-source.json"):
            schema = (
                "szl.build-info/v1"
                if path == "/api/build-info"
                else "szl.deployment-source/v1"
            )
            payload, error = _source_document(schema)
            if error:
                payload["error"] = error
                self._json(503, payload)
            else:
                self._json(200, payload)
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
