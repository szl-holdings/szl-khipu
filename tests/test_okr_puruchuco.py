# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Puruchuco accounting-hierarchy check against figures reported by the Khipu Field Guide."""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "research/okr_readings/puruchuco.py"
SEALED = ROOT / "research/okr_readings/puruchuco_v1.json"


def _load():
    spec = importlib.util.spec_from_file_location("szl_okr_puruchuco_test", FILE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cord(value, status="known"):
    return {"value": value, "value_status": status, "level": 1, "parent_kind": "primary"}


class WindowArithmetic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pu = _load()

    def test_span_sum_uses_one_based_inclusive_cord_numbers(self):
        cords = [cord(v) for v in (5, 7, 11, 13)]
        self.assertEqual(self.pu.span_sum(cords, 2, 3), {"sum": 18, "unreadable": 0})

    def test_unreadable_cords_are_counted_not_summed(self):
        cords = [cord(5), cord(None, "unknown"), cord(0, "knotless")]
        self.assertEqual(self.pu.span_sum(cords, 1, 3), {"sum": 5, "unreadable": 1})

    def test_span_outside_the_khipu_is_refused(self):
        with self.assertRaises(self.pu.Hold):
            self.pu.span_sum([cord(1)], 1, 2)

    def test_window_sums_cover_every_start(self):
        cords = [cord(v) for v in (1, 2, 3, 4)]
        self.assertEqual(self.pu.window_sums(cords, 2), [3, 5, 7])


class PendantOrder(unittest.TestCase):
    def test_pendants_follow_ordinal_not_stored_order(self):
        module = _load()
        cords = [{"id": 10, "ordinal": 1, "parent": 1, "level": 1, "parent_kind": "primary"},
                 {"id": 11, "ordinal": 3, "parent": 1, "level": 1, "parent_kind": "primary"},
                 {"id": 12, "ordinal": 2, "parent": 1, "level": 1, "parent_kind": "primary"},
                 {"id": 13, "ordinal": 1, "parent": 10, "level": 2, "parent_kind": "cord"}]
        self.assertEqual([c["id"] for c in module.pendants({"cords": cords})], [10, 12, 11])


class PuruchucoCorpus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pu = _load()
        cls.report = cls.pu.audit()

    def test_claim_scope(self):
        r = self.report
        self.assertEqual(r["schema"], self.pu.SCHEMA)
        self.assertEqual(r["status"], "POST_HOC_REPLICATION_OF_REPORTED_FIGURES")
        for flag in ("preregistered", "historical_khipu_decipherment", "new_reading_claimed",
                     "source_paper_read", "signature_verified"):
            self.assertIs(r[flag], False, flag)

    def test_wrong_corpus_is_refused(self):
        with self.assertRaises(self.pu.Hold):
            self.pu.audit(corpus={"sha256": "0" * 64, "khipus": []})

    def test_hierarchy_khipus_present_except_cm009(self):
        present = {k["investigator_num"]: k["okr_num"] for k in self.report["khipus"]}
        self.assertEqual(present, {"UR063": "KH0300", "UR064": "KH0301", "UR066": "KH0303",
                                   "UR067": "KH0304", "UR068": "KH0305", "UR073": "KH0310"})
        self.assertEqual(self.report["not_in_corpus"], ["CM009"])

    def test_reported_sums_are_reproduced(self):
        m = self.report["measured"]
        self.assertEqual(m["ur063_pendant_total"], {"sum": 1439, "unreadable": 6})
        self.assertEqual(m["ur068_cords_34_53"], {"sum": 1447, "unreadable": 0})
        self.assertEqual(m["gap"], 8)

    def test_specificity_checks(self):
        s = self.report["specificity"]
        self.assertEqual(s["label"], "OURS_EXPLORATORY_NOT_IN_SOURCE")
        self.assertEqual(s["other_khipus_in_corpus"], 618)
        self.assertEqual(s["other_khipus_with_total_within_gap_of_1447"], 0)
        self.assertEqual(s["ur068_twenty_cord_windows"], 54)
        self.assertEqual(s["ur068_windows_within_gap_of_1439"], 15)
        self.assertEqual(s["largest_single_cord_in_span"], 1236)

    def test_claim_statuses(self):
        s = {c["id"]: c["status"] for c in self.report["claims"]}
        self.assertEqual(s["ur063_total_1439"], "REPLICATED")
        self.assertEqual(s["ur068_cords_34_53_total_1447"], "REPLICATED")
        self.assertEqual(s["hierarchy_sums_move_upward"], "NOT_TESTED")
        self.assertEqual(s["cm009"], "NOT_TESTABLE")

    def test_sealed_report_matches_recomputation(self):
        sealed = json.loads(SEALED.read_text(encoding="utf-8"))
        self.assertEqual(sealed, json.loads(json.dumps(self.report)))
        self.assertEqual(sealed["report_sha256"], self.pu.digest(sealed))


if __name__ == "__main__":
    unittest.main()
