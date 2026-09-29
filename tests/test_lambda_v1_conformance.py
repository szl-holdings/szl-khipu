# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""szl.lambda/v1 conformance for szl_khipu.lambda_gate.

CI runs ``python -m unittest discover -s tests -v``, so this is a unittest.TestCase
module, not a pytest file.

The vectors are a byte copy of szl-lambda-gate ``spec/lambda_v1_vectors.json``, pinned
in ``tests/fixtures/lambda_v1_vectors.SOURCE`` by commit, git blob id and canonical
SHA-256 (the canonical digest does not change when a checkout rewrites line endings).

Held exactly: every error code, every gate verdict and every gate code.
Held within each vector's ``value_tol``: the value of Λ. khipu computes log Λ with
``np.dot`` and the reference uses ``math.fsum``, so the two can differ in the last ulp.

``wgm`` keeps its total contract: it never raises, and it returns 0.0 (the veto) for
every input v1 rejects. ``evaluate_lambda`` and ``lambda_gate`` report which v1 code
fired. Λ is advisory. Λ uniqueness is Conjecture 1 (open); nothing here uses it.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import struct
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from szl_khipu.doctrine import YUYAY_FLOORS
from szl_khipu.lambda_gate import check_a5, evaluate_lambda, lambda_gate, uniform_weights, wgm

# `szl_khipu.lambda_gate` as an attribute is the re-exported function, not the module.
LG = sys.modules["szl_khipu.lambda_gate"]

FIXTURES = Path(__file__).resolve().parent / "fixtures"
VECTORS_PATH = FIXTURES / "lambda_v1_vectors.json"
SOURCE_PATH = FIXTURES / "lambda_v1_vectors.SOURCE"

FF01_MERGE = "d3443b0539ad9fdbd407a0b0bf0454b416102089"

#: spec/szl.lambda.v1.json error_codes, in precedence order (szl-lambda-gate @ FF01_MERGE).
V1_ERROR_CODES = (
    "LAMBDA_TYPE_INVALID",
    "LAMBDA_EMPTY",
    "LAMBDA_LENGTH_MISMATCH",
    "LAMBDA_NONFINITE_AXIS",
    "LAMBDA_AXIS_OUT_OF_RANGE",
    "LAMBDA_NONFINITE_WEIGHT",
    "LAMBDA_WEIGHT_NONPOSITIVE",
    "LAMBDA_WEIGHT_SUM",
    "LAMBDA_TAU_INVALID",
)
#: spec/szl.lambda.v1.json gate.rules: the (verdict, code) pairs a gate may emit.
GATE_OUTCOMES = frozenset(
    {("GO", None), ("NO_GO", "ZERO_VETO"), ("NO_GO", "BELOW_TAU"), ("ABSTAIN", "NUMERIC_TIE")}
    | {("BLOCK", code) for code in V1_ERROR_CODES}
)


def _decode(value: Any) -> Any:
    """'f64:<16 hex>' -> float; any other JSON value is passed through unchanged."""
    if isinstance(value, str) and value.startswith("f64:"):
        digits = value[4:]
        if len(digits) != 16 or any(c not in "0123456789abcdef" for c in digits):
            raise ValueError(f"not an f64 literal: {value!r}")
        return struct.unpack(">d", bytes.fromhex(digits))[0]
    return value


def _decode_seq(value: Any) -> Any:
    return [_decode(v) for v in value] if isinstance(value, list) else value


def _canonical_sha256(obj: Any) -> str:
    data = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _read_source() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in SOURCE_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"malformed SOURCE line: {line!r}")
        out[key.strip()] = value.strip()
    return out


def _load_vectors() -> dict[str, Any]:
    return json.loads(VECTORS_PATH.read_text(encoding="utf-8"))


class VectorFixtureTests(unittest.TestCase):
    """The fixture is the FF-01 merge's vectors file, byte for byte."""

    def test_source_pins_the_ff01_merge(self) -> None:
        src = _read_source()
        self.assertEqual(src["source_repository"], "szl-holdings/szl-lambda-gate")
        self.assertEqual(src["source_commit"], FF01_MERGE)
        self.assertEqual(src["source_path"], "spec/lambda_v1_vectors.json")

    def test_canonical_digest_matches_source(self) -> None:
        self.assertEqual(_canonical_sha256(_load_vectors()), _read_source()["canonical_sha256"])

    def test_bytes_are_the_source_git_blob(self) -> None:
        # A Windows checkout may rewrite LF to CRLF; the committed blob is LF.
        raw = VECTORS_PATH.read_bytes().replace(b"\r\n", b"\n")
        blob = hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()
        self.assertEqual(blob, _read_source()["git_blob_sha1"])

    def test_canonical_digest_is_line_ending_independent(self) -> None:
        text = VECTORS_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")
        self.assertEqual(
            _canonical_sha256(json.loads(text.replace("\n", "\r\n"))),
            _canonical_sha256(json.loads(text)),
        )

    def test_vectors_are_well_formed(self) -> None:
        doc = _load_vectors()
        self.assertEqual(doc["schema"], "szl.lambda/v1.vectors")
        vectors = doc["vectors"]
        self.assertEqual(len(vectors), int(_read_source()["vectors"]))
        ids = [v["id"] for v in vectors]
        self.assertEqual(len(ids), len(set(ids)))
        for vec in vectors:
            with self.subTest(vec["id"]):
                tol = vec["value_tol"]
                self.assertTrue(isinstance(tol, float) and math.isfinite(tol) and 0 < tol < 1e-6)
                self.assertIsNotNone(vec["weights"], "a None weight vector would hit khipu's default weights")
                expect = vec["expect"]
                self.assertEqual(("error" in expect) + ("value_f64" in expect), 1)
                self.assertIn((expect["verdict"], expect["code"]), GATE_OUTCOMES)

    def test_the_rows_this_slice_fixes_are_present(self) -> None:
        by_id = {v["id"]: v for v in _load_vectors()["vectors"]}
        self.assertEqual(by_id["x_gt_1"]["expect"]["code"], "LAMBDA_AXIS_OUT_OF_RANGE")
        self.assertEqual(by_id["w_zero_weight"]["expect"]["code"], "LAMBDA_WEIGHT_NONPOSITIVE")
        self.assertEqual(by_id["w_unnormalised_2_2"]["expect"]["code"], "LAMBDA_WEIGHT_SUM")
        self.assertEqual(by_id["weight_sum_outside_tol"]["expect"]["code"], "LAMBDA_WEIGHT_SUM")
        self.assertEqual(by_id["weight_sum_within_tol"]["expect"]["verdict"], "NO_GO")
        self.assertEqual(by_id["tie_exact"]["expect"]["code"], "NUMERIC_TIE")


class LambdaV1ConformanceTests(unittest.TestCase):
    """Every vector through wgm, evaluate_lambda and lambda_gate."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.vectors = _load_vectors()["vectors"]

    def _inputs(self, vec: dict[str, Any]) -> tuple[Any, Any, Any]:
        return _decode_seq(vec["axes"]), _decode_seq(vec["weights"]), _decode(vec["tau"])

    def test_evaluate_lambda_matches_every_vector(self) -> None:
        for vec in self.vectors:
            with self.subTest(vec["id"]):
                axes, weights, _tau = self._inputs(vec)
                ev = evaluate_lambda(axes, weights)
                expect = vec["expect"]
                self.assertIn("code", ev)
                self.assertIsInstance(ev["value"], float)
                self.assertTrue(0.0 <= ev["value"] <= 1.0, ev["value"])
                if "error" in expect:
                    self.assertEqual(ev["code"], expect["error"])
                    self.assertTrue(ev["blocked"])
                    self.assertEqual(ev["value"], 0.0)
                    self.assertIn(expect["error"], ev["reason"])
                    self.assertNotIn("advisory pass", ev["reason"])
                    continue
                want = _decode(expect["value_f64"])
                self.assertLessEqual(abs(ev["value"] - want), vec["value_tol"])
                if want == 0.0:
                    self.assertEqual(ev["value"], 0.0)
                    self.assertEqual(ev["code"], "ZERO_VETO")
                    self.assertTrue(ev["blocked"])
                else:
                    self.assertIsNone(ev["code"])
                    self.assertFalse(ev["blocked"])

    def test_lambda_gate_matches_every_vector(self) -> None:
        for vec in self.vectors:
            with self.subTest(vec["id"]):
                axes, weights, tau = self._inputs(vec)
                g = lambda_gate(axes, tau, weights=weights)
                expect = vec["expect"]
                self.assertEqual((g["verdict"], g["code"]), (expect["verdict"], expect["code"]))
                self.assertIs(g["passed"], expect["verdict"] == "GO")
                self.assertIs(g["blocked"], not g["passed"])
                self.assertTrue(0.0 <= g["score"] <= 1.0, g["score"])
                self.assertIs(g["advisory"], True)
                self.assertIs(g["proven_trust"], False)
                if expect["verdict"] != "GO":
                    self.assertNotIn("advisory pass", g["reason"])

    def test_wgm_is_total_on_every_vector(self) -> None:
        for vec in self.vectors:
            with self.subTest(vec["id"]):
                axes, weights, _tau = self._inputs(vec)
                value = wgm(axes, weights)
                self.assertIsInstance(value, float)
                self.assertTrue(0.0 <= value <= 1.0, value)
                if "error" in vec["expect"]:
                    self.assertEqual(value, 0.0)
                else:
                    want = _decode(vec["expect"]["value_f64"])
                    self.assertLessEqual(abs(value - want), vec["value_tol"])


class LambdaV1AcceptanceTests(unittest.TestCase):
    """FF-05 acceptance, one named test per criterion."""

    def test_x_above_one_is_blocked_not_an_advisory_pass(self) -> None:
        # E5: before this slice [1.5, 0.9] gave Λ = 1.1619 and an advisory pass.
        for g in (lambda_gate([1.5, 0.9], threshold=0.5), lambda_gate([1.5, 0.9])):
            self.assertEqual(g["verdict"], "BLOCK")
            self.assertEqual(g["code"], "LAMBDA_AXIS_OUT_OF_RANGE")
            self.assertFalse(g["passed"])
            self.assertTrue(g["blocked"])
            self.assertLessEqual(g["score"], 1.0)
            self.assertNotIn("advisory pass", g["reason"])
        ev = evaluate_lambda([1.5, 0.9])
        self.assertTrue(ev["blocked"])
        self.assertEqual(ev["code"], "LAMBDA_AXIS_OUT_OF_RANGE")
        self.assertEqual(ev["value"], 0.0)
        self.assertEqual(wgm([1.5, 0.9], [0.5, 0.5]), 0.0)

    def test_zero_weight_blocks_instead_of_dropping_the_axis(self) -> None:
        # Before this slice w == 0 silently dropped the axis: wgm([0.5, 0.9], [1, 0]) == 0.5.
        ev = evaluate_lambda([0.5, 0.9], [1.0, 0.0])
        self.assertTrue(ev["blocked"])
        self.assertEqual(ev["code"], "LAMBDA_WEIGHT_NONPOSITIVE")
        g = lambda_gate([0.5, 0.9], 0.4, weights=[1.0, 0.0])
        self.assertEqual((g["verdict"], g["code"]), ("BLOCK", "LAMBDA_WEIGHT_NONPOSITIVE"))
        self.assertEqual(wgm([0.5, 0.9], [1.0, 0.0]), 0.0)

    def test_weight_sum_tolerance_is_1e_12(self) -> None:
        self.assertEqual(LG.WEIGHT_SUM_TOL, 1e-12)
        axes = [0.9, 0.5]
        inside = evaluate_lambda(axes, [0.5 + 4e-13, 0.5])
        self.assertIsNone(inside["code"])
        self.assertFalse(inside["blocked"])
        for w in ([0.5 + 3e-12, 0.5], [0.5 + 5e-10, 0.5]):  # 5e-10 passed the old 1e-9 tolerance
            with self.subTest(w=w):
                ev = evaluate_lambda(axes, w)
                self.assertEqual(ev["code"], "LAMBDA_WEIGHT_SUM")
                self.assertTrue(ev["blocked"])
                self.assertEqual(wgm(axes, w), 0.0)

    def test_wgm_keeps_its_total_zero_veto_contract(self) -> None:
        # tests/test_kernels.py:42,45 pin these two; they must hold unchanged.
        self.assertEqual(wgm([0.5, float("nan"), 0.5], uniform_weights(3)), 0.0)
        self.assertEqual(wgm([0.5, 0.5], [0.3, 0.3]), 0.0)
        self.assertEqual(wgm([0.9, 0.9, 0.0, 0.9], uniform_weights(4)), 0.0)
        garbage: list[Any] = [
            None, 0.9, "0.9", b"0.9", {}, {"a": 0.9}, [None], [True], ["0.9"], [[0.9]],
            [complex(0.9, 0.0)], [float("inf")], [10**400], np.array(["0.9"]), np.array([True]),
        ]
        for bad in garbage:
            with self.subTest(bad=repr(bad)):
                self.assertEqual(wgm(bad, [1.0]), 0.0)
                self.assertEqual(wgm([0.9], bad), 0.0)
                self.assertTrue(evaluate_lambda(bad, [1.0])["blocked"])
                self.assertIn(evaluate_lambda(bad, [1.0])["code"], V1_ERROR_CODES)
        # numpy inputs keep working.
        self.assertLess(abs(wgm(np.full(13, 0.7), uniform_weights(13)) - 0.7), 1e-12)
        self.assertLess(abs(wgm(np.array([0.81, 0.64]), np.array([0.5, 0.5])) - 0.72), 1e-12)

    def test_a5_is_relabelled_not_checked(self) -> None:
        ev = evaluate_lambda(list(YUYAY_FLOORS))
        self.assertEqual([a["id"] for a in ev["axioms"]], ["A1", "A2", "A3", "A4", "A5"])
        a5 = ev["axioms"][4]
        self.assertEqual(a5["state"], "NOT_CHECKED")
        self.assertIn("NOT_CHECKED", a5["detail"])
        self.assertNotEqual(a5["detail"], "permutation-invariant")
        self.assertIs(a5["ok"], True)  # the joint (x, w) reversal it runs cannot block a decision
        self.assertFalse(ev["blocked"])
        self.assertIsNone(ev["code"])
        self.assertIn("by construction", check_a5.__doc__ or "")

    def test_default_threshold_path_is_unchanged(self) -> None:
        g = lambda_gate(list(YUYAY_FLOORS))
        self.assertEqual(g["threshold"], 0.5)
        self.assertEqual((g["verdict"], g["code"]), ("GO", None))
        self.assertTrue(g["passed"])
        self.assertIn("advisory pass", g["reason"])

    def test_gate_below_threshold_is_not_reported_as_a_pass(self) -> None:
        g = lambda_gate(list(YUYAY_FLOORS), threshold=0.95)
        self.assertEqual((g["verdict"], g["code"]), ("NO_GO", "BELOW_TAU"))
        self.assertFalse(g["passed"])
        self.assertNotIn("advisory pass", g["reason"])

    def test_http_and_cli_callers_are_unchanged_and_fail_closed(self) -> None:
        from szl_khipu.cli import main
        from szl_khipu.http_app import api_lambda

        out = api_lambda({"axes": [1.5, 0.9]})
        self.assertLessEqual({"value", "blocked", "reason", "axioms", "advisory"}, set(out))
        self.assertTrue(out["blocked"])
        self.assertEqual(out["value"], 0.0)
        self.assertIn("LAMBDA_AXIS_OUT_OF_RANGE", out["reason"])
        json.dumps(out, allow_nan=False)
        self.assertFalse(api_lambda({})["blocked"])

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["demo-lambda", "--axes", "1.5,0.9"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["blocked"])
        self.assertEqual(payload["value"], 0.0)
        self.assertIn("LAMBDA_AXIS_OUT_OF_RANGE", payload["reason"])


if __name__ == "__main__":
    unittest.main()
