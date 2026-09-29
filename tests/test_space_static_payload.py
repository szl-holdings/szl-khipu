from __future__ import annotations

import hashlib
import importlib.util
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SERVER = _load("khipu_static_server", ROOT / "space" / "server.py")
PUBLISH = _load("khipu_static_publisher", ROOT / "scripts" / "publish_hf.py")
ASSETS = {
    "szl-holo-v2.css": (b"body { color: white; }\n", "text/css; charset=utf-8"),
    "szl-holo-v2.js": (b"const ready = true;\n", "text/javascript; charset=utf-8"),
}
# SZL Kanchay is vendored once in the package (szl_khipu/kanchay/), which the Space
# payload already carries; the server maps fixed /kanchay/ paths onto those files.
KANCHAY_ASSETS = {
    "/kanchay/kanchay.css": ("szl_khipu/kanchay/kanchay.css", "text/css; charset=utf-8"),
    "/kanchay/kanchay-components.css": (
        "szl_khipu/kanchay/kanchay-components.css",
        "text/css; charset=utf-8",
    ),
    "/kanchay/fonts/SpaceGrotesk-latin.woff2": (
        "szl_khipu/kanchay/fonts/SpaceGrotesk-latin.woff2",
        "font/woff2",
    ),
    "/kanchay/fonts/Inter-latin.woff2": ("szl_khipu/kanchay/fonts/Inter-latin.woff2", "font/woff2"),
    "/kanchay/fonts/JetBrainsMono-latin.woff2": (
        "szl_khipu/kanchay/fonts/JetBrainsMono-latin.woff2",
        "font/woff2",
    ),
}
KANCHAY_STYLESHEETS = ("./kanchay/kanchay.css", "./kanchay/kanchay-components.css")


def _kanchay_fixture(root: Path) -> dict[str, bytes]:
    """Write distinct stand-in bytes at each vendored payload path under root."""
    bodies = {}
    for served, (relative, _content_type) in KANCHAY_ASSETS.items():
        body = f"kanchay fixture {served}\n".encode()
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        bodies[served] = body
    return bodies


class CapturedHandler(SERVER.Handler):
    """Exercise request handling without a socket or provider request."""

    def __init__(self, method: str, path: str):
        self.command = method
        self.path = path
        self.wfile = io.BytesIO()
        self.status = None
        self.headers_sent = {}

    def send_response(self, code, message=None):
        self.status = code

    def send_header(self, name, value):
        self.headers_sent[name] = value

    def end_headers(self):
        pass


class StaticPayloadTests(unittest.TestCase):
    def test_get_and_head_serve_exact_assets_with_matching_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, (body, content_type) in ASSETS.items():
                (root / name).write_bytes(body)
                for suffix in ("", "?v=reviewed"):
                    for method in ("GET", "HEAD"):
                        with self.subTest(name=name, method=method, suffix=suffix):
                            handler = CapturedHandler(method, f"/{name}{suffix}")
                            with (
                                mock.patch.object(SERVER, "ROOT", root),
                                mock.patch.object(SERVER, "_url_json") as provider,
                            ):
                                getattr(handler, f"do_{method}")()
                            self.assertEqual(handler.status, 200)
                            self.assertEqual(handler.headers_sent["Content-Type"], content_type)
                            self.assertEqual(handler.headers_sent["Content-Length"], str(len(body)))
                            self.assertEqual(handler.headers_sent["Cache-Control"], "no-store")
                            self.assertEqual(handler.wfile.getvalue(), body if method == "GET" else b"")
                            provider.assert_not_called()

    def test_kanchay_assets_serve_from_the_payload_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bodies = _kanchay_fixture(root)
            for served, (_relative, content_type) in KANCHAY_ASSETS.items():
                for method in ("GET", "HEAD"):
                    with self.subTest(path=served, method=method):
                        handler = CapturedHandler(method, served)
                        with mock.patch.object(SERVER, "ROOT", root):
                            getattr(handler, f"do_{method}")()
                        self.assertEqual(handler.status, 200)
                        self.assertEqual(handler.headers_sent["Content-Type"], content_type)
                        self.assertEqual(handler.headers_sent["Content-Length"], str(len(bodies[served])))
                        self.assertEqual(handler.headers_sent["Cache-Control"], "no-store")
                        expected = bodies[served] if method == "GET" else b""
                        self.assertEqual(handler.wfile.getvalue(), expected)

    def test_local_repository_run_finds_the_package_one_level_up(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "space").mkdir()
            bodies = _kanchay_fixture(repository)
            handler = CapturedHandler("GET", "/kanchay/kanchay.css")
            with mock.patch.object(SERVER, "ROOT", repository / "space"):
                handler.do_GET()
            self.assertEqual(handler.status, 200)
            self.assertEqual(handler.wfile.getvalue(), bodies["/kanchay/kanchay.css"])

    def test_unknown_and_missing_assets_remain_not_found(self):
        with tempfile.TemporaryDirectory() as directory:
            for path in (
                "/missing.css",
                "/szl-holo-v2.css",
                "/szl-holo-v2.js",
                *KANCHAY_ASSETS,
                "/kanchay/SOURCE.json",
                "/kanchay/fonts/Syncopate-400.woff2",
                "/szl_khipu/kanchay/kanchay.css",
                "/kanchay/../server.py",
            ):
                for method in ("GET", "HEAD"):
                    with self.subTest(path=path, method=method):
                        handler = CapturedHandler(method, path)
                        with mock.patch.object(SERVER, "ROOT", Path(directory)):
                            getattr(handler, f"do_{method}")()
                        self.assertEqual(handler.status, 404)
                        if method == "HEAD":
                            self.assertEqual(handler.wfile.getvalue(), b"")

    def test_staging_and_manifest_include_both_referenced_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            space = source / "space"
            space.mkdir(parents=True)
            for name in ("Dockerfile", "README.md", *PUBLISH.RUNTIME_ROOT_FILES):
                (space / name).write_bytes(ASSETS.get(name, (b"fixture\n", ""))[0])
            kanchay = _kanchay_fixture(source)
            staging = root / "staging"
            staging.mkdir()
            with (
                mock.patch.object(PUBLISH, "ROOT", source),
                mock.patch.object(PUBLISH.tempfile, "mkdtemp", return_value=str(staging)),
                mock.patch.dict(os.environ, {
                    "GITHUB_SHA": "a" * 40,
                    "GITHUB_RUN_ID": "123",
                    "GITHUB_RUN_ATTEMPT": "1",
                }, clear=True),
            ):
                self.assertEqual(PUBLISH._stage_space(), staging)
                records = {item["path"]: item for item in PUBLISH._deployment_manifest(staging)["files"]}
            for name, (body, _content_type) in ASSETS.items():
                self.assertEqual((staging / name).read_bytes(), body)
                self.assertEqual(records[name]["sha256"], hashlib.sha256(body).hexdigest())
            for served, (relative, _content_type) in KANCHAY_ASSETS.items():
                self.assertEqual((staging / relative).read_bytes(), kanchay[served])
                self.assertEqual(records[relative]["sha256"], hashlib.sha256(kanchay[served]).hexdigest())

    def test_missing_required_source_fails_before_creating_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            with (
                mock.patch.object(PUBLISH, "ROOT", Path(directory)),
                mock.patch.object(PUBLISH.tempfile, "mkdtemp") as create,
            ):
                with self.assertRaisesRegex(RuntimeError, "required Space source files"):
                    PUBLISH._stage_space()
                create.assert_not_called()

    def test_html_container_and_manifest_share_exact_asset_names(self):
        html = (ROOT / "space" / "index.html").read_text(encoding="utf-8")
        dockerfile = (ROOT / "space" / "Dockerfile").read_text(encoding="utf-8")
        self.assertEqual(
            set(SERVER.STATIC_ASSETS),
            {f"/{name}" for name in ASSETS} | set(KANCHAY_ASSETS),
        )
        for name in ASSETS:
            self.assertIn(f'"./{name}"', html)
            self.assertIn(f"COPY --chown=appuser:appuser {name} ./{name}", dockerfile.splitlines())
            self.assertIn(name, PUBLISH.RUNTIME_ROOT_FILES)
        # Kanchay rides in the package directory the container and manifest already carry.
        self.assertIn("COPY --chown=appuser:appuser szl_khipu ./szl_khipu", dockerfile.splitlines())
        self.assertIn("szl_khipu", PUBLISH.RUNTIME_ROOT_DIRECTORIES)
        tokens = (ROOT / "szl_khipu" / "kanchay" / "kanchay.css").read_text(encoding="utf-8")
        for served, (relative, content_type) in KANCHAY_ASSETS.items():
            self.assertEqual(SERVER.STATIC_ASSETS[served], (relative, content_type))
            self.assertTrue((ROOT / relative).is_file(), relative)
            if content_type == "font/woff2":
                self.assertIn(f"url('./fonts/{Path(relative).name}')", tokens)
        # Tokens load before the components, and both before the Space's own stylesheet.
        positions = [html.index(f'"{href}"') for href in (*KANCHAY_STYLESHEETS, "./szl-holo-v2.css")]
        self.assertEqual(positions, sorted(positions))


if __name__ == "__main__":
    unittest.main()
