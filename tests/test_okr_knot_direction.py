# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Knot-direction test: is a knot's S/Z direction set by its type inside each khipu?"""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "research/okr_readings/knot_direction.py"
SEALED = ROOT / "research/okr_readings/knot_direction_v1.json"


def _load():
    spec = importlib.util.spec_from_file_location("szl_okr_knot_direction_test", FILE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MajorityRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kd = _load()

    def test_only_knots_with_a_recorded_direction_are_kept(self):
        cords = [[("S", None, "Z"), ("L", 4, "S")], [("E", None, "U")], []]
        self.assertEqual(self.kd.directed_knots(cords), [("S", None, "Z"), ("L", 4, "S")])

    def test_majority_accuracy_by_khipu_and_by_type(self):
        knots = [("S", None, "Z")] * 6 + [("L", 3, "S")] * 3 + [("L", 4, "Z")]
        self.assertEqual(self.kd.majority_hits(knots, lambda k: None), 7)
        self.assertEqual(self.kd.majority_hits(knots, lambda k: k[0]), 9)
        self.assertEqual(self.kd.majority_hits(knots, lambda k: (k[0], k[1])), 10)

    def test_type_that_fixes_direction_removes_all_the_khipu_bits(self):
        knots = [("S", None, "Z")] * 20 + [("L", 3, "S")] * 20
        prior = {"S": 0.5, "Z": 0.5}
        base = self.kd.bits(knots, lambda k: None, prior)
        with_type = self.kd.bits(knots, lambda k: k[0], prior)
        self.assertGreater(base / 40, 0.9)
        self.assertLess(with_type / 40, 0.15)


class KnotDirectionCorpus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kd = _load()
        cls.sealed = json.loads(SEALED.read_text(encoding="utf-8"))
        cls.observed = cls.kd.audit(trials=0)

    def test_scope(self):
        r = self.sealed
        self.assertEqual(r["schema"], self.kd.SCHEMA)
        self.assertEqual(r["status"], "POST_HOC_EXPLORATORY_INFORMATION_TEST")
        for flag in ("preregistered", "historical_khipu_decipherment", "meaning_assigned_to_any_feature",
                     "signature_verified"):
            self.assertIs(r[flag], False, flag)
        self.assertEqual(r["input_knots_sha256"], self.kd.knots_digest())

    def test_observed_values_match_recomputation(self):
        for key in ("khipus", "knots", "bits_per_knot_corpus", "bits_per_knot_khipu",
                    "khipus_with_both_directions", "majority_accuracy"):
            self.assertEqual(self.sealed[key], self.observed[key], key)
        for context, row in self.sealed["contexts"].items():
            self.assertEqual(row["gain_bits_per_knot"],
                             self.observed["contexts"][context]["gain_bits_per_knot"], context)

    def test_knot_type_explains_most_of_the_within_khipu_variation(self):
        r = self.sealed
        self.assertEqual(r["contexts"]["type"]["verdict"], "ABOVE_SHUFFLE_NULL_NET_SAVING")
        self.assertGreater(r["contexts"]["type"]["gain_bits_per_knot"], 0.5 * r["bits_per_knot_khipu"])
        acc = r["majority_accuracy"]
        self.assertLess(acc["khipu"], acc["type"])
        self.assertLessEqual(acc["type"], acc["type_and_turns"])

    def test_sealed_digest(self):
        self.assertEqual(self.sealed["report_sha256"], self.kd.digest(self.sealed))


if __name__ == "__main__":
    unittest.main()
