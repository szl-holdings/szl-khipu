# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Deterministic body-deadline regressions; no sockets, sleeps or package imports."""

from __future__ import annotations

import importlib.util
import io
import unittest
import unittest.mock
from pathlib import Path
from types import SimpleNamespace


_PATH = Path(__file__).resolve().parents[1] / "szl_khipu" / "http_body.py"
_SPEC = importlib.util.spec_from_file_location("khipu_body_deadline_regression", _PATH)
assert _SPEC and _SPEC.loader
http_body = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(http_body)


class _Clock:
    def __init__(self, now=0.0):
        self.now = now

    def monotonic(self):
        return self.now


class _Reader:
    """Advance the fake clock when a read returns or raises."""

    def __init__(self, clock, deliveries, method):
        self.clock = clock
        self.deliveries = iter(deliveries)
        self.requests = []
        setattr(self, method, self._read)

    def _read(self, n):
        self.requests.append(n)
        self.clock.now, result = next(self.deliveries)
        if isinstance(result, Exception):
            raise result
        return result


class BodyDeadlineTests(unittest.TestCase):
    def assertRejected(self, status, call, reason):
        with self.assertRaises(http_body.RequestRejected) as caught:
            call()
        self.assertEqual(caught.exception.status, status)
        self.assertEqual(caught.exception.reason, reason)
        self.assertEqual(caught.exception.payload(), {
            "error": reason, "status": status, "blocked": True, "proven_trust": False,
        })

    def test_final_read_after_deadline_is_rejected(self):
        for method in ("read1", "read"):
            for deliveries in (((11.0, b"{}"),), ((9.0, b"{"), (11.0, b"}"))):
                with self.subTest(method=method, deliveries=deliveries):
                    clock = _Clock()
                    reader = _Reader(clock, deliveries, method)
                    with unittest.mock.patch.object(http_body, "time", clock):
                        self.assertRejected(408, lambda: http_body.read_exact(reader, 2),
                                            "request body was not received in time")
                    self.assertEqual(len(reader.requests), len(deliveries))

    def test_complete_body_before_or_at_deadline_is_unchanged(self):
        for method in ("read1", "read"):
            for finish in (9.0, 10.0):
                with self.subTest(method=method, finish=finish):
                    clock = _Clock()
                    reader = _Reader(clock, ((1.0, b"{"), (finish, b"}")), method)
                    with unittest.mock.patch.object(http_body, "time", clock):
                        self.assertEqual(http_body.read_exact(reader, 2), b"{}")
                    self.assertEqual(reader.requests, [2, 1])

    def test_custom_budget_is_relative_to_start_and_never_resets(self):
        for finish in (102.0, 102.1):
            with self.subTest(finish=finish):
                clock = _Clock(100.0)
                reader = _Reader(clock, ((101.0, b"{"), (finish, b"}")), "read")
                with unittest.mock.patch.object(http_body, "time", clock):
                    call = lambda: http_body.read_exact(reader, 2, deadline_s=2.0)
                    if finish == 102.0:
                        self.assertEqual(call(), b"{}")
                    else:
                        self.assertRejected(408, call, "request body was not received in time")

    def test_late_nonfinal_chunk_stops_before_another_read(self):
        clock = _Clock()
        reader = _Reader(clock, ((11.0, b"{"), (12.0, b"}")), "read1")
        with unittest.mock.patch.object(http_body, "time", clock):
            self.assertRejected(408, lambda: http_body.read_exact(reader, 2),
                                "request body was not received in time")
        self.assertEqual(reader.requests, [2])

    def test_already_expired_budget_does_not_read(self):
        clock = _Clock()
        reader = _Reader(clock, (), "read")
        with unittest.mock.patch.object(http_body, "time", clock):
            self.assertRejected(408, lambda: http_body.read_exact(reader, 2, deadline_s=-1.0),
                                "request body was not received in time")
        self.assertEqual(reader.requests, [])

    def test_zero_length_does_not_read_or_check_the_clock(self):
        with unittest.mock.patch.object(http_body, "time", object()):
            self.assertEqual(http_body.read_exact(object(), 0), b"")

    def test_eof_and_io_error_semantics_are_preserved(self):
        for method in ("read1", "read"):
            for finish in (1.0, 11.0):
                for result, status, reason in (
                    (b"", 400, "truncated request body: received 1 of 2 bytes"),
                    (OSError("failed"), 400, "request body could not be read"),
                    (TimeoutError("timed out"), 408, "request body was not received in time"),
                ):
                    with self.subTest(method=method, finish=finish, result=result):
                        clock = _Clock()
                        reader = _Reader(clock, ((0.5, b"{"), (finish, result)), method)
                        with unittest.mock.patch.object(http_body, "time", clock):
                            self.assertRejected(status, lambda: http_body.read_exact(reader, 2), reason)

    def test_read1_is_preferred_and_read_size_remains_bounded(self):
        data = b"x" * (http_body._CHUNK + 1)
        preferred = SimpleNamespace(read1=unittest.mock.Mock(side_effect=[data[:-1], data[-1:]]),
                                    read=unittest.mock.Mock(side_effect=AssertionError("fallback")))
        with unittest.mock.patch.object(http_body, "time", _Clock()):
            self.assertEqual(http_body.read_exact(preferred, len(data)), data)
        self.assertEqual(preferred.read1.call_args_list,
                         [unittest.mock.call(http_body._CHUNK), unittest.mock.call(1)])
        preferred.read.assert_not_called()

    def test_late_json_body_is_rejected_before_parsing(self):
        for raw in (b"{}", b"xx"):
            with self.subTest(raw=raw):
                clock = _Clock()
                reader = _Reader(clock, ((11.0, raw),), "read1")
                with unittest.mock.patch.object(http_body, "time", clock):
                    status, payload = http_body.guarded(lambda: http_body.read_json_object(
                        {"Content-Length": "2"}, reader))
                self.assertEqual(status, 408)
                self.assertEqual(payload, {"error": "request body was not received in time",
                                          "status": 408, "blocked": True, "proven_trust": False})

    def test_valid_json_and_empty_body_contracts_are_unchanged(self):
        for raw, expected in ((b"", {}), (b"{}", {}), (b'{"x":1}', {"x": 1})):
            with self.subTest(raw=raw):
                self.assertEqual(http_body.read_json_object(
                    {"Content-Length": str(len(raw))}, io.BytesIO(raw)), expected)


if __name__ == "__main__":
    unittest.main()
