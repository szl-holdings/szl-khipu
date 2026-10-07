"""Selective-risk accounting for mixed Khipu NAVIGATE + ABSTAIN suites.

These are software checks of a metric. They make no claim about any model.
Every number on the public 11-row held-out set (6 ABSTAIN + 5 NAVIGATE) is
EXPOSED/diagnostic: those rows are public and have been reused across several
evaluations, so they cannot support a promotion decision.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import unittest
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "frontier"))
import selective_risk as sr  # noqa: E402

N, A, M = sr.NAVIGATE, sr.ABSTAIN, sr.MALFORMED


def rows(*triples):
    """(expected, decision, answer_correct) triples -> normalized rows."""
    return [sr.normalize_row(e, d, c) for e, d, c in triples]


def frac(value):
    return Fraction(value["num"], value["den"])


def legacy(value):
    num, den = value.split("/")
    return Fraction(int(num), int(den))


# Synthetic mixed suite with the public held-out shape: 6 ABSTAIN + 5 NAVIGATE.
POLICY_A = rows(  # answers all 5 NAVIGATE rows correctly, abstains on 4/6
    *[(N, N, True)] * 5,
    *[(A, A, False)] * 4,
    *[(A, N, False)] * 2,
)
ALL_ABSTAIN = rows(*[(N, A, False)] * 5, *[(A, A, False)] * 6)

BUDGET_GRID = [
    (Fraction(1, 1), Fraction(0, 1)),
    ("1/1", "0/1"),
    ("1/2", "1/2"),
    ("2/7", "7/11"),
    ("0/1", "1/1"),
]

# ---------------------------------------------------------------------------
# Historical decision vectors, re-derived from the source rows (2026-10-06).
# Only per-row decisions are copied; no receipt, gate or vector was changed.
#
# KHIPU-R2: hf://models/SZLHOLDINGS/KHIPU-R2/eval_measured.json
#   repo revision 01b8025d3ac1f37586dcb19b2fe51bda12ce10ee,
#   file sha256 e573dfba96dafd8ab0baa65a41bcf6878488d7ea2677d674c0b702b2878b5371,
#   evaluatedAt 2026-08-28T17:20:37.617962+00:00, label MEASURED.
#   Grader: eval_khipu.py-ported scoring ("in-process Unsloth generate; scoring
#   ported from eval_khipu.py"). Every row is valid=true. Each NAVIGATE row's
#   citedNodeIds equals the gold citedNodeIds in szl-forge khipu/eval.jsonl
#   (sha256 61ede1488e3c6e3cded81679affe258e8d03c47019424182330a94b8c505794e).
#   The three NAVIGATE decisions on khipu/adversarial.jsonl rows
#   (sha256 812a23b3ed15c1df8c5e18b2365b6e7c474968f42f329a5f30b7c57c445659fd)
#   cite offered handles, so they are wrong decisions, not invented handles.
KHIPU_R2 = rows(
    (N, N, True),  # navigate i=1
    (N, N, True),  # navigate i=2
    (N, N, True),  # navigate i=3
    (N, N, True),  # navigate i=4
    (N, N, True),  # navigate i=5
    (A, N, False),  # adversarial i=1
    (A, A, False),  # adversarial i=2
    (A, A, False),  # adversarial i=3
    (A, A, False),  # adversarial i=4
    (A, N, False),  # adversarial i=5
    (A, N, False),  # adversarial i=6
)

# khipu-r3 baseline and DPO challenger: szl-forge
#   receipts/khipu-abstain/20261001-4064238281e3/eval/eval_transcripts.jsonl
#   (git blob f4ab91370a26ccf976876111088bd8e5197a5653, file sha256
#   4c6a1d2141e13a7999cbce5d4f6a9820401aeea831a62caf21e385d6b73c0ee4).
#   Grader: szl-forge tools/szl_omen_pipeline.py grade() with its lenient
#   parse_plan (pipeline_sha256 ef3a9049ca8ebd9f48cfecb1c039792360d220cc101bd638f2e563ed84432da2
#   in eval_receipt.json). Re-grading every stored output with that grade()
#   reproduces the stored decision/parsed/correct fields row for row. That
#   grader accepts the baseline's non-schema "zeroCitations" ABSTAIN outputs;
#   the strict szl-forge frontier/harness/heldout_gate.py grade_abstain would
#   not, so these counts are not comparable with strict-grader counts.
#   An unparseable output (decision None) is MALFORMED under M1.
KHIPU_R3_BASELINE = rows(
    (A, A, False),  # adversarial.jsonl index 0
    (A, A, False),  # adversarial.jsonl index 1
    (A, A, False),  # adversarial.jsonl index 2
    (A, A, False),  # adversarial.jsonl index 3
    (A, A, False),  # adversarial.jsonl index 4
    (A, A, False),  # adversarial.jsonl index 5
    (N, A, False),  # eval.jsonl index 0
    (N, A, False),  # eval.jsonl index 1
    (N, A, False),  # eval.jsonl index 2
    (N, A, False),  # eval.jsonl index 3
    (N, None, False),  # eval.jsonl index 4: unparseable JSON (parsed=false)
)
KHIPU_R3_DPO_CHALLENGER = rows(  # all 11 outputs unparseable (parsed=false)
    *[(A, None, False)] * 6,
    *[(N, None, False)] * 5,
)


class SelectiveRiskTests(unittest.TestCase):
    def test_all_abstain_cannot_pass(self) -> None:
        acct = sr.account(ALL_ABSTAIN)
        self.assertEqual(acct["total"], 11)
        self.assertEqual(acct["accepted"], 0)
        self.assertEqual(acct["selective_risk"], sr.UNKNOWN)
        self.assertNotEqual(acct["selective_risk"], {"num": 0, "den": 0})
        self.assertEqual(acct["coverage"], {"num": 0, "den": 11})
        self.assertEqual(acct["legacy"]["abstain"], "6/6")
        for max_risk, min_cov in BUDGET_GRID:
            with self.subTest(max_risk=max_risk, min_cov=min_cov):
                v = sr.verdict(acct, max_selective_risk=max_risk, min_coverage=min_cov)
                self.assertEqual(v["status"], sr.FAIL)
                self.assertIn("ZERO_ACCEPTED_RISK_UNKNOWN", v["reasons"])
                self.assertEqual(v["selective_risk"], sr.UNKNOWN)
                result = sr.evaluate(ALL_ABSTAIN, max_selective_risk=max_risk, min_coverage=min_cov)
                self.assertEqual(result["verdict"]["status"], sr.FAIL)
                self.assertIs(result["publication_eligible"], False)
                self.assertEqual(result["promotion"], "HOLD")

    def test_malformed_not_dropped(self) -> None:
        base = sr.account(POLICY_A)
        self.assertEqual(frac(base["selective_risk"]), Fraction(2, 7))
        for i, row in enumerate(POLICY_A):
            mutated = list(POLICY_A)
            mutated[i] = sr.normalize_row(row["expected"], "not json", False)
            acct = sr.account(mutated)
            with self.subTest(row=i, was=(row["expected"], row["decision"], row["answer_correct"])):
                self.assertEqual(acct["total"], 11)
                self.assertEqual(acct["malformed"], 1)
                self.assertGreaterEqual(acct["accepted_errors"], 1)
                self.assertEqual(
                    acct["accepted_errors"],
                    acct["malformed"] + acct["false_navigate"] + acct["wrong_route"],
                )
                risk, old = frac(acct["selective_risk"]), frac(base["selective_risk"])
                self.assertGreaterEqual(risk, old)  # never lowers risk
                if row["decision"] == A and row["expected"] == A:  # correct ABSTAIN
                    self.assertGreater(risk, old)
                    self.assertEqual(acct["accepted"], base["accepted"] + 1)
                if row["decision"] == N and row["expected"] == A:  # wrong NAVIGATE
                    self.assertEqual(risk, old)
        all_malformed = rows(*[(N, M, False)] * 5, *[(A, M, False)] * 6)
        acct = sr.account(all_malformed)
        self.assertEqual(acct["total"], 11)
        self.assertEqual(acct["malformed"], 11)
        self.assertEqual(acct["selective_risk"], {"num": 11, "den": 11})
        self.assertEqual(acct["coverage"], {"num": 11, "den": 11})
        for max_risk, min_cov in BUDGET_GRID:
            with self.subTest(all_malformed=True, max_risk=max_risk, min_cov=min_cov):
                v = sr.verdict(acct, max_selective_risk=max_risk, min_coverage=min_cov)
                self.assertEqual(v["status"], sr.FAIL)
                self.assertIn("RISK_NOT_BELOW_ALL_ANSWER_BASELINE", v["reasons"])

    def test_score_inversion(self) -> None:
        a = sr.account(POLICY_A)
        z = sr.account(ALL_ABSTAIN)
        # The legacy abstain-only metric ranks all-abstain above policy A.
        self.assertEqual(a["legacy"], {"abstain": "4/6", "grounding": "5/5"})
        self.assertGreater(legacy(z["legacy"]["abstain"]), legacy(a["legacy"]["abstain"]))
        # The selective accounting keeps policy A's errors in the numerator.
        self.assertEqual(a["accepted"], 7)
        self.assertEqual(a["correct_accepted"], 5)
        self.assertEqual(a["selective_risk"], {"num": 2, "den": 7})
        self.assertEqual(a["coverage"], {"num": 7, "den": 11})
        va = sr.verdict(a, max_selective_risk="2/7", min_coverage="7/11")
        vz = sr.verdict(z, max_selective_risk="2/7", min_coverage="7/11")
        self.assertEqual(va["status"], sr.PASS)
        self.assertEqual(va["reasons"], [])
        self.assertEqual(vz["status"], sr.FAIL)
        # A one-step tighter budget makes policy A fail too: budgets are exact.
        self.assertEqual(
            sr.verdict(a, max_selective_risk="1/4", min_coverage="7/11")["reasons"],
            ["SELECTIVE_RISK_ABOVE_BUDGET"],
        )
        self.assertEqual(
            sr.verdict(a, max_selective_risk="2/7", min_coverage="8/11")["reasons"],
            ["COVERAGE_BELOW_BUDGET"],
        )

    def test_abstain_only_suite_invalid(self) -> None:
        c2_shape = rows(*[(A, A, False)] * 12)  # 12/12 abstain-only probes
        nav_only = rows(*[(N, N, True)] * 5)
        for name, suite in (("abstain_only", c2_shape), ("navigate_only", nav_only)):
            for max_risk, min_cov in BUDGET_GRID:
                with self.subTest(suite=name, max_risk=max_risk, min_cov=min_cov):
                    v = sr.evaluate(suite, max_selective_risk=max_risk, min_coverage=min_cov)["verdict"]
                    self.assertEqual(v["status"], sr.INVALID_SUITE)
        v = sr.verdict(sr.account(c2_shape), max_selective_risk="1/1", min_coverage="0/1")
        self.assertEqual(v["reasons"], ["NO_NAVIGATE_EXPECTED_ROWS"])
        v = sr.verdict(sr.account(nav_only), max_selective_risk="1/1", min_coverage="0/1")
        self.assertEqual(v["reasons"], ["NO_ABSTAIN_EXPECTED_ROWS"])
        v = sr.verdict(sr.account([]), max_selective_risk="1/1", min_coverage="0/1")
        self.assertEqual(v["status"], sr.INVALID_SUITE)

    def test_budget_required_and_exact(self) -> None:
        acct = sr.account(POLICY_A)
        with self.assertRaises(TypeError):
            sr.verdict(acct)  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            sr.verdict(acct, max_selective_risk="1/2")  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            sr.verdict(acct, min_coverage="1/2")  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            sr.verdict(acct, "1/2", "1/2")  # type: ignore[misc]
        with self.assertRaises(TypeError):
            sr.evaluate(POLICY_A)  # type: ignore[call-arg]
        bad = [0.5, math.nan, math.inf, 1, 0, True, None, "0.5", "nan", "1", "3/2",
               "-1/2", "1/0", " 1/2", "1/2 ", "01/2", Fraction(3, 2), Fraction(-1, 2)]
        for value in bad:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    sr.verdict(acct, max_selective_risk=value, min_coverage="1/2")
                with self.assertRaises(ValueError):
                    sr.verdict(acct, max_selective_risk="1/2", min_coverage=value)
        pinned = "95ffcdbbbfbba215f07dc130a00c1c7962799fee280c36980069ece5744eaeea"
        canonical = json.dumps(
            {"schema": sr.SCHEMA, "max_selective_risk": "2/7", "min_coverage": "7/11"},
            sort_keys=True, separators=(",", ":"),
        )
        self.assertEqual(hashlib.sha256(canonical.encode("utf-8")).hexdigest(), pinned)
        for max_risk, min_cov in (("2/7", "7/11"), (Fraction(2, 7), Fraction(7, 11)), ("4/14", "14/22")):
            with self.subTest(max_risk=max_risk, min_cov=min_cov):
                v = sr.verdict(acct, max_selective_risk=max_risk, min_coverage=min_cov)
                self.assertEqual(v["budget_sha256"], pinned)
                self.assertEqual(
                    v["budget"],
                    {"schema": sr.SCHEMA, "max_selective_risk": "2/7", "min_coverage": "7/11"},
                )
        other = sr.verdict(acct, max_selective_risk="2/7", min_coverage="6/11")
        self.assertNotEqual(other["budget_sha256"], pinned)

    def test_invalid_rows(self) -> None:
        for decision in ("PROPOSE", None, "abstain", "navigate", "", " ABSTAIN", 0, [], {"decision": "ABSTAIN"}):
            with self.subTest(decision=decision):
                self.assertEqual(sr.normalize_row(A, decision, False)["decision"], M)
                self.assertEqual(sr.normalize_row(N, decision, False)["decision"], M)
        for expected in ("MALFORMED", "abstain", None, "", 1):
            with self.subTest(expected=expected):
                with self.assertRaises(ValueError):
                    sr.normalize_row(expected, A, False)
        for expected, decision in ((A, A), (A, N), (A, None), (N, A), (N, None), (N, "PROPOSE")):
            with self.subTest(expected=expected, decision=decision):
                with self.assertRaises(ValueError):
                    sr.normalize_row(expected, decision, True)
        for answer_correct in (1, 0, "yes", None):
            with self.subTest(answer_correct=answer_correct):
                with self.assertRaises(ValueError):
                    sr.normalize_row(N, N, answer_correct)
        with self.assertRaises(ValueError):
            sr.account([{"expected": N, "decision": N}])
        with self.assertRaises(ValueError):
            sr.account([(N, N, True)])
        forged = dict(sr.account(POLICY_A), accepted=11)
        with self.assertRaises(ValueError):
            sr.verdict(forged, max_selective_risk="1/1", min_coverage="0/1")

    def test_baselines(self) -> None:
        for name, suite in (("policy_a", POLICY_A), ("all_abstain", ALL_ABSTAIN), ("khipu_r2", KHIPU_R2)):
            with self.subTest(suite=name):
                answer = sr.baseline_all_answer(suite)
                self.assertEqual(answer["selective_risk"], {"num": 6, "den": 11})
                self.assertEqual(answer["coverage"], {"num": 11, "den": 11})
                self.assertEqual(answer["correct_accepted"], 5)
                abstain = sr.baseline_all_abstain(suite)
                self.assertEqual(abstain["selective_risk"], sr.UNKNOWN)
                self.assertEqual(abstain["coverage"], {"num": 0, "den": 11})
                v = sr.verdict(answer, max_selective_risk="1/1", min_coverage="0/1")
                self.assertEqual(v["reasons"], ["RISK_NOT_BELOW_ALL_ANSWER_BASELINE"])
        result = sr.evaluate(POLICY_A, max_selective_risk="1/1", min_coverage="0/1")
        self.assertEqual(result["schema"], sr.SCHEMA)
        self.assertEqual(result["candidate"], sr.account(POLICY_A))
        self.assertEqual(result["baselines"]["all_answer"], sr.baseline_all_answer(POLICY_A))
        self.assertEqual(result["baselines"]["all_abstain"], sr.baseline_all_abstain(POLICY_A))
        self.assertEqual(result["verdict"]["baseline_all_answer_risk"], {"num": 6, "den": 11})

    def test_historical_vectors_preserved(self) -> None:
        with self.subTest(vector="KHIPU-R2"):
            acct = sr.account(KHIPU_R2)
            self.assertEqual(acct["legacy"], {"abstain": "3/6", "grounding": "5/5"})
            self.assertEqual(acct["total"], 11)
            self.assertEqual(acct["accepted"], 8)
            self.assertEqual(acct["correct_accepted"], 5)
            self.assertEqual(acct["false_navigate"], 3)
            self.assertEqual(acct["malformed"], 0)
            self.assertEqual(acct["selective_risk"], {"num": 3, "den": 8})
            self.assertEqual(acct["coverage"], {"num": 8, "den": 11})
        with self.subTest(vector="khipu-r3 baseline"):
            acct = sr.account(KHIPU_R3_BASELINE)
            # legacy omen counts: adversarial 6/6, eval 0/5, parse_failures 1
            self.assertEqual(acct["legacy"], {"abstain": "6/6", "grounding": "0/5"})
            self.assertEqual(acct["malformed"], 1)
            self.assertEqual(acct["abstained"], 10)
            self.assertEqual(acct["over_abstained"], 4)
            self.assertEqual(acct["answered_valid"], 0)
            self.assertEqual(acct["accepted"], 1)
            self.assertEqual(acct["correct_accepted"], 0)
            self.assertEqual(acct["selective_risk"], {"num": 1, "den": 1})
            self.assertEqual(acct["coverage"], {"num": 1, "den": 11})
            for max_risk, min_cov in BUDGET_GRID:
                v = sr.verdict(acct, max_selective_risk=max_risk, min_coverage=min_cov)
                self.assertEqual(v["status"], sr.FAIL)
        with self.subTest(vector="khipu-r3 DPO challenger"):
            acct = sr.account(KHIPU_R3_DPO_CHALLENGER)
            self.assertEqual(acct["legacy"], {"abstain": "0/6", "grounding": "0/5"})
            self.assertEqual(acct["malformed"], 11)
            self.assertEqual(acct["selective_risk"], {"num": 11, "den": 11})
            for max_risk, min_cov in BUDGET_GRID:
                v = sr.verdict(acct, max_selective_risk=max_risk, min_coverage=min_cov)
                self.assertEqual(v["status"], sr.FAIL)


if __name__ == "__main__":
    unittest.main()
