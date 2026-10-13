# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""One strict, bounded request-body parser behind every stdlib HTTP surface.

The package app (szl_khipu.http_app), the Space server (space/server.py) and the
Ñan lab (szl_khipu.nan_lab) run against in-process servers on 127.0.0.1 with raw
sockets, so malformed framing reaches the handler exactly as sent.
"""

from __future__ import annotations

import ast
import http.client
import importlib.util
import io
import json
import socket
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from szl_khipu import http_app, http_body
from szl_khipu.doctrine import YUYAY_FLOORS
from szl_khipu.http_body import MAX_BODY_BYTES, RequestRejected
from szl_khipu.nan_lab import H as LabHandler
from szl_khipu.nan_lab import run_draft

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SPACE = _load("khipu_space_server_strict_body", ROOT / "space" / "server.py")


def _headers(*pairs: tuple[str, str]) -> http.client.HTTPMessage:
    message = http.client.HTTPMessage()
    for name, value in pairs:
        message[name] = value  # appends, so repeated headers stay repeated
    return message


class _Trickle:
    """A reader that hands out one byte per call."""

    def __init__(self, data: bytes) -> None:
        self.data = data

    def read1(self, n: int) -> bytes:
        out, self.data = self.data[:1], self.data[1:]
        return out


class _Stalled:
    def read1(self, n: int) -> bytes:
        raise TimeoutError("timed out")


class ParserUnitTests(unittest.TestCase):
    def assertRejected(self, status: int, fn, *args, **kwargs) -> RequestRejected:
        with self.assertRaises(RequestRejected) as ctx:
            fn(*args, **kwargs)
        self.assertEqual(ctx.exception.status, status, ctx.exception.reason)
        payload = ctx.exception.payload()
        self.assertEqual(payload["status"], status)
        self.assertTrue(payload["blocked"])
        self.assertIs(payload["proven_trust"], False)
        self.assertTrue(payload["error"])
        return ctx.exception

    def test_content_length_is_required_and_strict(self) -> None:
        cl = http_body.content_length
        self.assertEqual(cl(_headers(("Content-Length", "0"))), 0)
        self.assertEqual(cl(_headers(("Content-Length", " 17 "))), 17)
        self.assertEqual(cl(_headers(("Content-Length", str(MAX_BODY_BYTES)))), MAX_BODY_BYTES)
        self.assertRejected(411, cl, _headers())
        self.assertRejected(411, cl, _headers(("Transfer-Encoding", "chunked")))
        self.assertRejected(411, cl, _headers(("Transfer-Encoding", "chunked"), ("Content-Length", "2")))
        for bad in ("abc", "1.5", "+5", "-1", "-0", "0x10", "", "5, 5", "1e3", "٣"):
            with self.subTest(value=bad):
                self.assertRejected(400, cl, _headers(("Content-Length", bad)))
        self.assertRejected(400, cl, _headers(("Content-Length", "2"), ("Content-Length", "2")))
        self.assertRejected(413, cl, _headers(("Content-Length", str(MAX_BODY_BYTES + 1))))
        self.assertRejected(413, cl, _headers(("Content-Length", "9" * 5000)))
        self.assertEqual(cl({"Content-Length": "3"}), 3)  # plain mappings work too

    def test_read_is_exact_bounded_and_timed(self) -> None:
        self.assertEqual(http_body.read_exact(io.BytesIO(b"abcdef"), 6), b"abcdef")
        self.assertEqual(http_body.read_exact(io.BytesIO(b"abcdef"), 3), b"abc")
        self.assertEqual(http_body.read_exact(io.BytesIO(b""), 0), b"")
        exc = self.assertRejected(400, http_body.read_exact, io.BytesIO(b"abc"), 10)
        self.assertIn("3 of 10", exc.reason)
        self.assertRejected(408, http_body.read_exact, _Stalled(), 4)
        clock = iter([0.0, 1.0, 2.0, 3.0, 50.0, 60.0])
        with mock.patch.object(http_body.time, "monotonic", side_effect=lambda: next(clock)):
            self.assertRejected(408, http_body.read_exact, _Trickle(b"abcdefgh"), 8, deadline_s=10.0)

    def test_json_must_be_strict_utf8_object(self) -> None:
        parse = http_body.parse_json_object
        self.assertEqual(parse(b""), {})  # Content-Length: 0, the explicit empty body
        self.assertEqual(parse(b"{}"), {})
        self.assertEqual(parse(b' {"a": [1, 2.5, "\xc3\xb1"]} '), {"a": [1, 2.5, "ñ"]})
        for raw in (b'{"a":"\xff"}', b"\xc0\xaf", b'{"a":"\xed\xa0\x80"}'):
            with self.subTest(raw=raw):
                self.assertIn("UTF-8", self.assertRejected(400, parse, raw).reason)
        for raw, kind in ((b"[1]", "array"), (b'"s"', "string"), (b"1", "number"), (b"true", "boolean"), (b"null", "null")):
            with self.subTest(raw=raw):
                self.assertIn(kind, self.assertRejected(400, parse, raw).reason)
        for raw in (
            b"   ",
            b"{",
            b"{}x",
            b"\xef\xbb\xbf{}",
            b'{"a": NaN}',
            b'{"a": Infinity}',
            b'{"a": -Infinity}',
            b'{"a": 1e400}',
            b'{"a": 1, "a": 2}',
            b"[" * 100_000,
        ):
            with self.subTest(raw=raw[:24]):
                self.assertRejected(400, parse, raw)

    def test_fields_never_substitute_the_default_for_invalid_input(self) -> None:
        f = http_body.int_field
        self.assertEqual(f({}, "seed", 11), 11)
        self.assertEqual(f({"seed": 0}, "seed", 11), 0)
        self.assertEqual(f({"seed": "12"}, "seed", 11), 12)
        self.assertEqual(f({"seed": 12.0}, "seed", 11), 12)
        for bad in (None, True, False, 1.5, "x", "", [], {}, "1.0"):
            with self.subTest(value=bad):
                self.assertRejected(400, f, {"seed": bad}, "seed", 11)
        self.assertRejected(400, f, {"n": 0}, "n", 3, minimum=1)
        self.assertRejected(400, f, {"n": 13}, "n", 3, maximum=12)

        r = http_body.real_field
        self.assertEqual(r({}, "x", 0.2), 0.2)
        self.assertEqual(r({"x": "0.5"}, "x", 0.2), 0.5)
        for bad in (None, True, "abc", "nan", "inf", [1], {}, 10**400):
            with self.subTest(value=bad):
                self.assertRejected(400, r, {"x": bad}, "x", 0.2)

        lst = http_body.real_list_field
        self.assertEqual(lst({}, "axes", YUYAY_FLOORS), [float(x) for x in YUYAY_FLOORS])
        self.assertEqual(lst({"axes": [1, 0.5]}, "axes", YUYAY_FLOORS), [1.0, 0.5])
        self.assertEqual(lst({"axes": [1.5]}, "axes", YUYAY_FLOORS), [1.5])  # range is the kernel's call
        for bad in (None, "0.9", "", {}, {"a": 1}, [], ["0.9"], [True], [None], [[0.9]], [10**400], 0.9):
            with self.subTest(value=bad):
                self.assertRejected(400, lst, {"axes": bad}, "axes", YUYAY_FLOORS)

    def test_guarded_maps_every_failure_to_an_explicit_status(self) -> None:
        self.assertEqual(http_body.guarded(lambda: {"ok": 1}), (200, {"ok": 1}))
        def too_big() -> None:
            raise RequestRejected(413, "big")

        code, payload = http_body.guarded(too_big)
        self.assertEqual((code, payload["error"]), (413, "big"))
        code, payload = http_body.guarded(lambda: int("x"))
        self.assertEqual(code, 400)
        self.assertTrue(payload["blocked"])
        self.assertIs(payload["proven_trust"], False)

    def test_parser_is_stdlib_only_and_loads_by_path(self) -> None:
        path = ROOT / "szl_khipu" / "http_body.py"
        imported = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        self.assertLessEqual(imported, {"__future__", "json", "math", "re", "time", "typing"})
        standalone = _load("szl_khipu_http_body_standalone", path)
        body = standalone.read_json_object(_headers(("Content-Length", "8")), io.BytesIO(b'{"a": 1}'))
        self.assertEqual(body, {"a": 1})
        # The Space server uses the package parser itself, not a second copy.
        self.assertIs(SPACE._body, http_body)


class _BodyContract:
    """Framing and JSON rules every handler must enforce identically."""

    handler: type
    route = "/api/lambda"
    server: ThreadingHTTPServer

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), cls.handler)
        cls.port = int(cls.server.server_address[1])
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def raw(
        self,
        headers: list[tuple[str, str]],
        body: bytes = b"",
        *,
        path: str | None = None,
        method: str = "POST",
        half_close: bool = False,
    ) -> tuple[int, dict[str, str], bytes, bytes]:
        """Send exactly these bytes; return (status, headers, body, bytes after the response)."""
        with socket.create_connection(("127.0.0.1", self.port), timeout=10) as sock:
            head = f"{method} {path or self.route} HTTP/1.1\r\nHost: 127.0.0.1\r\n"
            head += "".join(f"{k}: {v}\r\n" for k, v in headers) + "\r\n"
            sock.sendall(head.encode("latin-1") + body)
            if half_close:
                sock.shutdown(socket.SHUT_WR)
            response = http.client.HTTPResponse(sock)
            response.begin()
            data = response.read()
            got = {k.lower(): v for k, v in response.getheaders()}
            trailing = b""
            if got.get("connection", "").lower() == "close" or response.version == 10:
                sock.settimeout(5)
                try:
                    trailing = sock.recv(1)
                except (ConnectionError, TimeoutError):
                    trailing = b"<no clean close>"
            return response.status, got, data, trailing

    def post(self, payload: bytes, *, path: str | None = None) -> tuple[int, dict]:
        status, _headers_, data, _ = self.raw(
            [("Content-Type", "application/json"), ("Content-Length", str(len(payload)))],
            payload,
            path=path,
        )
        return status, json.loads(data)

    def assertRejected(self, status: int, result) -> dict:
        code, got, data, trailing = result
        self.assertEqual(code, status, data)
        payload = json.loads(data)
        self.assertTrue(payload["error"])
        self.assertTrue(payload["blocked"])
        self.assertIs(payload["proven_trust"], False)
        self.assertEqual(got.get("connection", "").lower(), "close")
        self.assertEqual(trailing, b"", "a rejected connection is closed, never reused")
        return payload

    # Requests the handler refuses before reading send headers only: a peer that closes
    # with unread bytes queued may reset the socket and drop the response under test.
    def test_missing_content_length_is_411(self) -> None:
        self.assertRejected(411, self.raw([("Content-Type", "application/json")]))
        self.assertRejected(411, self.raw([("Transfer-Encoding", "chunked")]))
        self.assertRejected(411, self.raw([("Transfer-Encoding", "chunked"), ("Content-Length", "2")]))

    def test_malformed_and_negative_content_length_is_400(self) -> None:
        for value in ("abc", "1.5", "+2", "-1", "-2", "0x2", "2, 2", ""):
            with self.subTest(value=value):
                self.assertRejected(400, self.raw([("Content-Length", value)]))
        self.assertRejected(400, self.raw([("Content-Length", "2"), ("Content-Length", "2")]))

    def test_oversized_content_length_is_413_before_any_read(self) -> None:
        # Only the headers are sent: the 413 must not wait for (or read) the body.
        self.assertRejected(413, self.raw([("Content-Length", str(MAX_BODY_BYTES + 1))]))
        self.assertRejected(413, self.raw([("Content-Length", "9" * 400)]))

    def test_truncated_body_is_400(self) -> None:
        payload = self.assertRejected(400, self.raw([("Content-Length", "40")], b'{"seed": 11', half_close=True))
        self.assertIn("truncated", payload["error"])

    def test_stalled_body_is_408(self) -> None:
        with mock.patch.object(self.handler, "timeout", 0.3):
            payload = self.assertRejected(408, self.raw([("Content-Length", "40")], b'{"seed"'))
        self.assertIn("not received in time", payload["error"])

    def test_invalid_utf8_is_400(self) -> None:
        for raw in (b'{"query": "\xff\xfe"}', b"\xc0\xaf"):
            with self.subTest(raw=raw):
                payload = self.assertRejected(400, self.raw([("Content-Length", str(len(raw)))], raw))
                self.assertIn("UTF-8", payload["error"])

    def test_array_scalar_and_non_strict_json_are_400(self) -> None:
        for raw in (b"[]", b"[1, 2]", b"7", b'"x"', b"true", b"null", b"   ", b"{", b'{"a": NaN}', b'{"a": 1e400}', b'{"a": 1, "a": 1}'):
            with self.subTest(raw=raw):
                self.assertRejected(400, self.raw([("Content-Length", str(len(raw)))], raw))

    def test_explicit_empty_body_keeps_the_demo_default(self) -> None:
        status, _got, data, _ = self.raw([("Content-Length", "0")])
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data), self.post(b"{}")[1])


class PackageAppBody(_BodyContract, unittest.TestCase):
    handler = http_app.Handler

    def test_invalid_axes_and_values_are_400(self) -> None:
        for body in (
            {"axes": "0.9"},
            {"axes": {"a": 1}},
            {"axes": []},
            {"axes": None},
            {"axes": ["0.9"]},
            {"axes": [True, 0.9]},
            {"axes": [[0.9]]},
            {"zero": 13},
            {"zero": -1},
            {"zero": 1.5},
            {"zero": True},
            {"zero": None},
        ):
            with self.subTest(body=body):
                status, payload = self.post(json.dumps(body).encode())
                self.assertEqual(status, 400, payload)
                self.assertTrue(payload["blocked"])
        cases = {
            "/api/yarqa": ({"seq": 0}, {"seq": 1025}, {"dim": 0}, {"dim": 257}, {"n_canals": 0},
                           {"n_canals": 13}, {"seed": -1}, {"seq": 1.5}, {"seq": "big"}),
            "/api/anatomy": ({"seed": "x"}, {"seed": True}),
            "/api/prefix": ({"seed": 1.5},),
            "/api/route": ({"seed": None},),
            "/api/bench": ({"seed": [11]},),
            "/api/tiledigest": ({"tamper": "x"},),
        }
        for path, bodies in cases.items():
            for body in bodies:
                with self.subTest(path=path, body=body):
                    status, payload = self.post(json.dumps(body).encode(), path=path)
                    self.assertEqual(status, 400, payload)
                    self.assertIs(payload["proven_trust"], False)

    def test_infer_rejects_a_malformed_point_before_any_weights_load(self) -> None:
        with mock.patch.object(http_app, "_moons_weights") as weights:
            for value in ("abc", True, [1], None):
                with self.subTest(x=value):
                    status, payload = self.post(json.dumps({"kind": "moons", "x": value}).encode(), path="/api/infer")
                    self.assertEqual(status, 400, payload)
            weights.assert_not_called()

    def test_valid_requests_are_unchanged(self) -> None:
        status, default = self.post(b"{}")
        self.assertEqual(status, 200)
        self.assertFalse(default["blocked"])
        status, floors = self.post(json.dumps({"axes": list(YUYAY_FLOORS)}).encode())
        self.assertEqual((status, floors), (200, default))
        status, zero = self.post(b'{"zero": 0}')
        self.assertEqual((status, zero["blocked"], zero["value"]), (200, True, 0.0))
        # A well-shaped out-of-range vector keeps its szl.lambda/v1 kernel verdict.
        status, out = self.post(b'{"axes": [1.5, 0.9]}')
        self.assertEqual((status, out["blocked"], out["value"]), (200, True, 0.0))
        self.assertIn("LAMBDA_AXIS_OUT_OF_RANGE", out["reason"])
        status, y = self.post(b'{"n_canals": 3, "seq": 12, "dim": 4, "seed": 7}', path="/api/yarqa")
        self.assertEqual((status, y["n_canals"], y["shape"]), (200, 3, [12, 4]))
        self.assertLessEqual(y["leaked"], 1e-9)
        status, keep_alive, data, _ = self.raw([("Content-Length", "2")], b"{}")
        self.assertEqual(status, 200)
        self.assertNotEqual(keep_alive.get("connection", "").lower(), "close")

    def test_get_query_inputs_follow_the_same_rule(self) -> None:
        def get(path: str) -> tuple[int, dict]:
            status, _got, data, _ = self.raw([], method="GET", path=path)
            return status, json.loads(data)

        self.assertEqual(get("/api/lambda")[0], 200)
        status, zero = get("/api/lambda?zero=0")
        self.assertEqual((status, zero["blocked"]), (200, True))
        for path in (
            "/api/lambda?axes=abc",
            "/api/lambda?axes=",
            "/api/lambda?axes=0.9,,0.9",
            "/api/lambda?axes=0.9&axes=0.9",
            "/api/lambda?zero=99",
            "/api/lambda?zero=",
            "/api/prefix?seed=x",
            "/api/yarqa?seq=100000",
        ):
            with self.subTest(path=path):
                status, payload = get(path)
                self.assertEqual(status, 400, payload)
                self.assertTrue(payload["blocked"])

    def test_unknown_post_route_closes_without_reading(self) -> None:
        code, got, _data, trailing = self.raw([("Content-Length", "2")], path="/api/nope")
        self.assertEqual(code, 404)
        self.assertEqual(got.get("connection", "").lower(), "close")
        self.assertEqual(trailing, b"")


class SpaceServerBody(_BodyContract, unittest.TestCase):
    handler = SPACE.Handler

    def test_space_kernel_is_live_under_test(self) -> None:
        self.assertEqual(SPACE.KERNEL, "LIVE")

    def test_invalid_axes_and_values_are_400(self) -> None:
        for body in ({"axes": "0.9"}, {"axes": {"a": 1}}, {"axes": []}, {"axes": None},
                     {"axes": ["0.9"]}, {"axes": [True, 0.9]}, {"axes": [[0.9]]}):
            with self.subTest(body=body):
                status, payload = self.post(json.dumps(body).encode())
                self.assertEqual(status, 400, payload)
                self.assertEqual(payload["kernel"], "LIVE")
        # n_canals 0 used to become the default 3 silently; above 12 the kernel clamped it.
        for body in ({"n_canals": 0}, {"n_canals": 13}, {"n_canals": "x"}, {"n_canals": None}, {"n_canals": 2.5}):
            with self.subTest(body=body):
                status, payload = self.post(json.dumps(body).encode(), path="/api/yarqa")
                self.assertEqual(status, 400, payload)
        for path, body in (("/api/prefix", {"seed": "x"}), ("/api/route", {"seed": True}),
                           ("/api/bench", {"seed": 1.5}), ("/api/infer", {"kind": "moons", "y": "abc"})):
            with self.subTest(path=path, body=body):
                status, payload = self.post(json.dumps(body).encode(), path=path)
                self.assertEqual(status, 400, payload)
                self.assertTrue(payload["blocked"])

    def test_valid_requests_are_unchanged(self) -> None:
        status, default = self.post(b"{}")
        self.assertEqual((status, default["decision"], default["kernel"]), (200, "ADMITTED", "LIVE"))
        status, floors = self.post(json.dumps({"axes": list(YUYAY_FLOORS)}).encode())
        self.assertEqual((status, floors), (200, default))
        status, out = self.post(b'{"axes": [1.5, 0.9]}')
        self.assertEqual((status, out["decision"]), (200, "BLOCKED"))
        self.assertIn("LAMBDA_AXIS_OUT_OF_RANGE", out["reason"])
        status, zero = self.post(json.dumps({"axes": [0.0] + list(YUYAY_FLOORS[1:])}).encode())
        self.assertEqual((status, zero["blocked"], zero["lambda"]), (200, True, 0.0))
        status, y = self.post(b'{"n_canals": 3}', path="/api/yarqa")
        self.assertEqual((status, y["n_canals"], y["ok"]), (200, 3, True))
        status, prefix = self.post(b'{"hijack": 1}', path="/api/prefix")
        self.assertEqual((status, prefix["hold"]), (200, 0))
        status, green = self.post(b'{"paint_sorry": 1}', path="/api/greenlight")
        self.assertEqual((status, green["blocked"]), (200, True))
        for path in ("/api/lambda", "/api/yarqa", "/api/prefix", "/api/greenlight"):
            with self.subTest(get=path):
                status, _got, _data, _ = self.raw([], method="GET", path=path)
                self.assertEqual(status, 200)

    def test_without_a_parser_post_is_503_not_a_default(self) -> None:
        with mock.patch.object(SPACE, "_body", None):
            code, _got, data, _ = self.raw([("Content-Length", "2")], b"{}")
        self.assertEqual(code, 503)
        self.assertIn("UNAVAILABLE", json.loads(data)["error"])

    def test_unknown_post_route_is_404_without_reading(self) -> None:
        code, _got, data, _ = self.raw([("Content-Length", str(MAX_BODY_BYTES + 1))], path="/api/nope")
        self.assertEqual((code, data), (404, b"not found"))


class NanLabBody(_BodyContract, unittest.TestCase):
    handler = LabHandler
    route = "/api/draft"

    def test_invalid_values_are_400_and_seed_zero_is_kept(self) -> None:
        for body in ({"seed": "x"}, {"seed": None}, {"seed": True}, {"tamper": "x"}, {"tamper": 0.5}):
            with self.subTest(body=body):
                status, payload = self.post(json.dumps(body).encode())
                self.assertEqual(status, 400, payload)
        # seed 0 used to become 11 through `or 11`; it is a real seed.
        status, zero = self.post(b'{"seed": 0}')
        self.assertEqual((status, zero), (200, run_draft(0)))
        self.assertNotEqual(zero["digest"], run_draft(11)["digest"])
        status, default = self.post(b"{}")
        self.assertEqual((status, default), (200, run_draft(11)))
        status, broken = self.post(b'{"tamper": 1}')
        self.assertEqual((status, broken["broken"]), (200, 1))
        status, digest = self.post(b'{"s": "khipu"}', path="/api/djb2")
        self.assertEqual((status, digest["algo"]), (200, "djb2"))
        code, _got, _data, _ = self.raw([("Content-Length", "2")], path="/api/nope")
        self.assertEqual(code, 404)


if __name__ == "__main__":
    unittest.main()
