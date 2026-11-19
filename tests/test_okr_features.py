# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Derived OKR cord features (spin, fibre, knot direction): codes, alignment, rebuild."""
from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "research/okr_readings/build_features.py"


def _load():
    spec = importlib.util.spec_from_file_location("szl_okr_features_test", FILE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FeatureCodes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bf = _load()

    def test_spin_keeps_s_and_z_and_folds_everything_else_to_unrecorded(self):
        self.assertEqual([self.bf.spin_code(x) for x in ("S", "Z", "U", "", None, "s")],
                         ["S", "Z", "U", "U", "U", "U"])

    def test_knot_direction_signature(self):
        sig = self.bf.knot_direction_signature
        self.assertEqual(sig([]), "-")
        self.assertEqual(sig(["S", "S"]), "S")
        self.assertEqual(sig(["Z"]), "Z")
        self.assertEqual(sig(["S", "Z"]), "M")
        self.assertEqual(sig(["U", "", None]), "U")
        self.assertEqual(sig(["Z", "U"]), "Z")

    def test_fibre_codes_are_one_character_and_reversible(self):
        table = self.bf.FIBRE_CODES
        self.assertEqual(len(set(table.values())), len(table))
        self.assertTrue(all(len(v) == 1 for v in table.values()))
        self.assertEqual(self.bf.fibre_code("CN"), table["CN"])
        self.assertEqual(self.bf.fibre_code(""), "U")
        self.assertEqual(self.bf.fibre_code(None), "U")

    def test_unknown_fibre_code_is_refused_not_guessed(self):
        with self.assertRaises(self.bf.Hold):
            self.bf.fibre_code("ZZ")


class ShippedFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bf = _load()
        cls.features = cls.bf.load_features()

    def test_pins(self):
        f = self.features
        self.assertEqual(f["schema"], self.bf.SCHEMA)
        self.assertEqual(f["source"]["db_sha256"],
                         "607913034a0f478c5c792025d0c3cab8a9a8f05223ed6bc9c2990122a8c1c4db")
        self.assertEqual(f["corpus_sha256"],
                         "6ef204b641826b37c320509952ed4181e93865af20f1cdfefd7516a49cf8ad0d")

    def test_one_code_per_corpus_cord_in_corpus_order(self):
        corpus = self.bf.engine().load_corpus()
        self.assertEqual(len(self.features["khipus"]), len(corpus["khipus"]))
        for khipu in corpus["khipus"]:
            row = self.features["khipus"][khipu["okr_num"]]
            n = len(khipu["cords"])
            self.assertEqual((len(row["spin"]), len(row["fibre"]), len(row["knot_dir"])), (n, n, n))
            self.assertEqual(row["cord_ids_sha256"], self.bf.cord_ids_digest(khipu["cords"]))

    def test_corpus_totals(self):
        t = self.features["totals"]
        self.assertEqual(t["cords"], 54403)
        self.assertEqual(t["spin"], {"S": 41569, "U": 9432, "Z": 3402})
        self.assertEqual(t["fibre"]["CN"], 28895)
        self.assertEqual(sum(t["knot_dir"].values()), 54403)

    def test_tampered_file_is_refused(self):
        with self.assertRaises(self.bf.Hold):
            self.bf.load_features(expected_sha256="0" * 64)

    @unittest.skipUnless(os.environ.get("SZL_OKR_DB"), "pinned OKR database not present")
    def test_rebuild_from_pinned_database_matches_shipped_file(self):
        rebuilt = self.bf.build(Path(os.environ["SZL_OKR_DB"]))
        self.assertEqual(self.bf.encode(rebuilt), self.bf.SHIPPED.read_bytes())


if __name__ == "__main__":
    unittest.main()


class KnotRecords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bf = _load()
        cls.knots = cls.bf.load_knots()

    def test_knot_code_round_trip(self):
        for kind, turns, direction in (("S", None, "S"), ("L", 4, "Z"), ("E", None, "U"),
                                       ("SP", None, "S"), ("LL", 12, "Z"), ("?", None, "U")):
            code = self.bf.knot_code(kind, turns, direction)
            self.assertEqual(self.bf.parse_knot(code), (kind, turns, direction), code)

    def test_direction_outside_s_and_z_is_unrecorded(self):
        self.assertEqual(self.bf.knot_code("S", None, "null")[-1], "U")
        self.assertEqual(self.bf.knot_code("S", None, None)[-1], "U")

    def test_cord_knots_split_per_cord_in_corpus_order(self):
        corpus = self.bf.engine().load_corpus()
        total = 0
        for khipu in corpus["khipus"]:
            per_cord = self.bf.cord_knots(self.knots["khipus"][khipu["okr_num"]])
            self.assertEqual(len(per_cord), len(khipu["cords"]), khipu["okr_num"])
            self.assertEqual([len(c) for c in per_cord], [len(c["knots"]) for c in khipu["cords"]],
                             khipu["okr_num"])
            total += sum(len(c) for c in per_cord)
        self.assertEqual(total, self.knots["totals"]["knots"])

    def test_a_khipu_with_no_cords_and_one_with_a_single_bare_cord_stay_distinct(self):
        self.assertEqual(self.bf.cord_knots({"knots": "", "cords": 0}), [])
        self.assertEqual(self.bf.cord_knots({"knots": "", "cords": 1}), [[]])
        with self.assertRaises(self.bf.Hold):
            self.bf.cord_knots({"knots": "SZ|SZ", "cords": 3})

    def test_pins_and_totals(self):
        k = self.knots
        self.assertEqual(k["schema"], self.bf.KNOTS_SCHEMA)
        self.assertEqual(k["source"]["db_sha256"],
                         "607913034a0f478c5c792025d0c3cab8a9a8f05223ed6bc9c2990122a8c1c4db")
        # 526 of the database's 110,677 knot rows sit on cords the corpus does not carry.
        self.assertEqual(k["totals"]["knots"], 110151)
        self.assertEqual(k["totals"]["direction"], {"S": 31701, "U": 12566, "Z": 65884})
        self.assertEqual(len(k["khipus"]), 619)
        self.assertIn("museum_num", k["khipus"]["KH0305"])

    @unittest.skipUnless(os.environ.get("SZL_OKR_DB"), "pinned OKR database not present")
    def test_knot_rebuild_from_pinned_database_matches_shipped_file(self):
        rebuilt = self.bf.build_knots(Path(os.environ["SZL_OKR_DB"]))
        self.assertEqual(self.bf.encode(rebuilt), self.bf.KNOTS_SHIPPED.read_bytes())
