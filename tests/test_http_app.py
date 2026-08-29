# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Python frontend + backend — stdlib HTTP, fail-closed."""

from __future__ import annotations

import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from szl_khipu.doctrine import proven_trust
from szl_khipu.http_app import make_server


class HttpAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.httpd = make_server("127.0.0.1", 0)
        cls.port = int(cls.httpd.server_address[1])
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _get(self, path: str) -> tuple[int, bytes, str]:
        with urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as r:
            return r.status, r.read(), r.headers.get_content_type()

    def _post(self, path: str, body: dict) -> dict:
        req = Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=json.dumps(body).encode("utf-8"),
            headers={"content-type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode("utf-8"))

    def test_index_is_python_frontend(self) -> None:
        code, raw, ctype = self._get("/")
        text = raw.decode("utf-8")
        self.assertEqual(code, 200)
        self.assertEqual(ctype, "text/html")
        self.assertIn("Knot the run", text)
        self.assertIn("Conjecture 1", text)
        self.assertIn("energy unavailable", text.lower())
        self.assertIn("Python FE+BE", text)
        self.assertNotIn("proven_trust=true", text.lower().replace(" ", ""))

    def test_health_and_version(self) -> None:
        _, raw, _ = self._get("/healthz")
        health = json.loads(raw)
        self.assertTrue(health["ok"])
        self.assertFalse(health["proven_trust"])
        _, raw, _ = self._get("/version")
        ver = json.loads(raw)
        self.assertFalse(ver["proven_trust"])
        self.assertEqual(ver["energy_status"], "UNAVAILABLE")
        self.assertEqual(ver["conjecture_1"], "OPEN")
        self.assertEqual(ver["frontend"], "python-stdlib")
        self.assertIs(proven_trust, False)

    def test_lambda_zero_route(self) -> None:
        ok = self._post("/api/lambda", {})
        self.assertFalse(ok["blocked"])
        self.assertFalse(ok["proven_trust"])
        z = self._post("/api/lambda", {"zero": 0})
        self.assertTrue(z["blocked"])
        self.assertEqual(z["value"], 0.0)

    def test_anatomy_fail_closed_and_no_joule(self) -> None:
        live = self._post("/api/anatomy", {})
        self.assertEqual(live["live_count"], 5)
        self.assertFalse(live["blocked"])
        self.assertIsNone(live["energy_j"])
        dead = self._post("/api/anatomy", {"zero_heart": True})
        self.assertTrue(dead["blocked"])
        fake = self._post("/api/anatomy", {"fabricate_joule": True})
        self.assertTrue(fake["blocked"])
        self.assertIsNone(fake["energy_j"])

    def test_yarqa_and_grid(self) -> None:
        y = self._post("/api/yarqa", {"n_canals": 3})
        self.assertLessEqual(y["leaked"], 1e-9)
        self.assertEqual(y["cuda"], "UNAVAILABLE")
        g = self._post("/api/tiledigest", {"tamper": 1})
        self.assertEqual(g["gridBreaks"], 1)

    def test_unknown_is_404(self) -> None:
        with self.assertRaises(HTTPError) as ctx:
            self._get("/nope")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
