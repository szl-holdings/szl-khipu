# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Santa Valley khipu replication: grouping rules, published arithmetic, sealed report."""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "research/okr_readings/santa_valley.py"
SEALED = ROOT / "research/okr_readings/santa_valley_v1.json"


def _load():
    spec = importlib.util.spec_from_file_location("szl_okr_santa_valley_test", FILE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cords(spec):
    """spec: list of (cluster, colour, n) runs -> pendant cord dicts in order."""
    out = []
    for cluster, colour, n in spec:
        for _ in range(n):
            out.append({"cluster": cluster, "color": colour, "attach": "V",
                        "value": 1, "value_status": "known",
                        "level": 1, "parent_kind": "primary"})
    return out


class BandGroupingRule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sv = _load()

    def sizes(self, spec):
        r = self.sv.band_groups(cords(spec))
        return len(r["groups"]), len(r["extras"]), len(r["singles"]), r["ambiguous"]

    def test_six_same_colour_cords_are_one_group(self):
        self.assertEqual(self.sizes([(1, "W", 6)]), (1, 0, 0, 0))

    def test_twelve_same_colour_cords_are_two_groups(self):
        self.assertEqual(self.sizes([(1, "W", 12)]), (2, 0, 0, 0))

    def test_ten_same_colour_cords_give_one_group_and_four_set_aside(self):
        r = self.sv.band_groups(cords([(1, "B", 10)]))
        self.assertEqual((len(r["groups"]), len(r["extras"])), (1, 4))
        self.assertEqual(len(r["groups"][0]), 6)

    def test_short_runs_that_total_six_form_one_mixed_group(self):
        self.assertEqual(self.sizes([(1, "AB", 3), (1, "MB", 2), (1, "AB", 1)]), (1, 0, 0, 0))

    def test_lone_cord_between_full_bands_is_set_aside(self):
        self.assertEqual(self.sizes([(1, "W", 6), (1, "RL", 1), (1, "KB", 6)]), (2, 1, 0, 0))

    def test_one_cord_cluster_is_a_single_not_a_group_member(self):
        self.assertEqual(self.sizes([(1, "W", 6), (2, "AB", 1), (3, "YB", 6)]), (2, 0, 1, 0))

    def test_cluster_boundary_does_not_join_short_runs(self):
        self.assertEqual(self.sizes([(1, "W", 3), (2, "W", 3)]), (0, 6, 0, 0))

    def test_short_runs_overflowing_six_are_flagged_ambiguous(self):
        groups, extras, singles, ambiguous = self.sizes([(1, "W", 4), (1, "AB", 3)])
        self.assertEqual((groups, extras, singles), (1, 1, 0))
        self.assertEqual(ambiguous, 1)

    def test_positional_rule_ignores_colour(self):
        r = self.sv.positional_groups(cords([(1, "W", 6), (1, "RL", 1), (1, "KB", 6)]))
        self.assertEqual((len(r["groups"]), len(r["extras"])), (2, 1))
        self.assertEqual([c["color"] for c in r["groups"][1]], ["RL"] + ["KB"] * 5)


class PublishedSplitArithmetic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sv = _load()

    def test_twenty_ordered_splits(self):
        rows = self.sv.split_table(self.sv.PACHACAS, verso=70, recto=63)
        self.assertEqual(len(rows), 20)
        self.assertEqual(len({tuple(r["verso"]) for r in rows}), 20)

    def test_split_table_reproduces_published_table_three(self):
        rows = self.sv.split_table(self.sv.PACHACAS, verso=70, recto=63)
        got = sorted((r["verso_total"], r["recto_total"], r["error"], r["p_published_form"]) for r in rows)
        want = sorted(tuple(x) for x in self.sv.PUBLISHED_TABLE_3)
        self.assertEqual(got, want)

    def test_named_alignments(self):
        rows = {tuple(sorted(r["verso"])): r for r in self.sv.split_table(self.sv.PACHACAS, 70, 63)}
        fitz = rows[("Cuyuchin", "Guauyan", "Namus")]
        mu = rows[("Corongo", "Cusca", "Guauyan")]
        self.assertEqual((fitz["verso_total"], fitz["recto_total"], fitz["error"]), (68, 62, 3))
        self.assertEqual((mu["verso_total"], mu["recto_total"], mu["error"]), (71, 59, 5))

    def test_tribute_arithmetic_in_quartillos(self):
        self.assertEqual(self.sv.quartillos(2, 7, 3), 95)
        self.assertEqual(self.sv.as_pesos_reales_quartillos(132 * 95), (391, 7, 0))


class SantaValleyCorpus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sv = _load()
        cls.report = cls.sv.audit()

    def test_source_pins_and_claim_scope(self):
        r = self.report
        self.assertEqual(r["schema"], self.sv.SCHEMA)
        self.assertEqual(r["input_corpus_sha256"],
                         "6ef204b641826b37c320509952ed4181e93865af20f1cdfefd7516a49cf8ad0d")
        self.assertEqual(r["upstream_okr_revision"], "4039ca51f4de661d80d0160596309c983a62a9c7")
        self.assertEqual(r["status"], "POST_HOC_REPLICATION_OF_PUBLISHED_CLAIMS")
        for flag in ("preregistered", "historical_khipu_decipherment", "new_reading_claimed",
                     "independent_research_lab_replication", "signature_verified",
                     "source_paper_fully_read"):
            self.assertIs(r[flag], False, flag)

    def test_wrong_corpus_is_refused(self):
        with self.assertRaises(self.sv.Hold):
            self.sv.audit(corpus={"sha256": "0" * 64, "khipus": []})

    def test_six_khipus_and_pendant_count(self):
        r = self.report
        self.assertEqual([k["okr_num"] for k in r["khipus"]],
                         ["KH0323", "KH0324", "KH0325", "KH0326", "KH0327", "KH0328"])
        self.assertEqual([k["investigator_num"] for k in r["khipus"]],
                         ["UR087", "UR088", "UR089", "UR090", "UR091", "UR092"])
        self.assertEqual(r["totals"]["level1_pendants"], 824)
        self.assertEqual(r["totals"]["one_cord_cluster_pendants"], 20)
        self.assertEqual(r["totals"]["pendants_in_multi_cord_clusters"], 804)

    def test_colour_band_rule_gives_published_group_counts(self):
        band = self.report["rules"]["colour_band"]
        self.assertEqual([k["groups"] for k in band["per_khipu"]], [48, 9, 34, 17, 15, 10])
        self.assertEqual(band["groups"], 133)
        self.assertEqual(band["ambiguous"], 0)
        self.assertEqual([k["set_aside"] for k in band["per_khipu"]], [0, 0, 0, 6, 0, 0])

    def test_identifier_attachments_differ_from_published_by_one_group(self):
        band = self.report["rules"]["colour_band"]
        self.assertEqual(band["identifier_attachment"], {"R": 63, "V": 69, "U": 1})
        kh0326 = band["per_khipu"][3]
        self.assertEqual(kh0326["identifier_sequence"], "VVVVVVVVVVRRRVRRR")
        self.assertEqual(kh0326["published_identifier_sequence"], "VVVVVVVVVVRRRVVRR")
        self.assertEqual(kh0326["identifier_sequence_mismatch_groups"], [15])
        self.assertEqual(band["per_khipu"][5]["identifier_sequence"], "RURRRRRRRR")

    def test_kh0326_begins_with_59_verso_cords(self):
        self.assertEqual(self.report["kh0326_leading_verso_cords"], 59)

    def test_first_cord_total_under_colour_band_rule(self):
        t = self.report["rules"]["colour_band"]["first_cord"]
        self.assertEqual(t["knotted_sum"], 360)
        self.assertEqual(t["knotted"] + t["knotless"] + t["unreadable"], 133)
        self.assertEqual((t["knotted"], t["knotless"], t["unreadable"]), (120, 10, 3))
        self.assertEqual(t["by_side_sum"], {"R": 91, "U": 2, "V": 267})
        self.assertEqual(t["per_khipu_sum"], [48, 80, 101, 84, 36, 11])
        self.assertEqual(t["by_side_sum"]["V"] + t["by_side_sum"]["R"] + t["by_side_sum"]["U"], 360)
        self.assertEqual(self.report["document"]["total_pesos"], 367)

    def test_positional_rule_shows_grouping_dependence(self):
        pos = self.report["rules"]["positional"]
        self.assertEqual(pos["groups"], 133)
        self.assertEqual(pos["first_cord"]["knotted_sum"], 749)

    def test_claim_statuses(self):
        s = {c["id"]: c["status"] for c in self.report["claims"]}
        self.assertEqual(s["khipus_in_corpus"], "REPLICATED")
        self.assertEqual(s["pendant_cords_804"], "REPLICATED")
        self.assertEqual(s["six_cord_groups_133"], "REPLICATED")
        self.assertEqual(s["identifier_recto_63_verso_70"], "PARTIAL")
        self.assertEqual(s["kh0326_59_leading_verso"], "REPLICATED")
        self.assertEqual(s["first_cord_total_near_367"], "PARTIAL")
        self.assertEqual(s["table_3_split_arithmetic"], "REPLICATED")
        self.assertEqual(s["tribute_paid_by_moiety"], "PARTIAL")
        self.assertEqual(s["six_cords_outside_groups"], "REPLICATED")
        self.assertTrue(all(c["status"] in self.sv.STATUSES for c in self.report["claims"]))

    def test_published_tribute_by_moiety_is_compared_with_both_side_assignments(self):
        self.assertEqual(self.report["published"]["tribute_by_moiety"],
                         {"verso_estimate": [381, 382], "recto": 86})
        sides = self.report["rules"]["colour_band"]["first_cord"]
        self.assertEqual(sides["by_side_sum"], {"R": 91, "U": 2, "V": 267})
        self.assertEqual(sides["by_published_side_sum"], {"R": 87, "V": 273})
        self.assertEqual(sides["unknotted_or_unreadable_by_side"], {"R": 0, "U": 0, "V": 13})

    def test_amount_owed_is_reported_both_ways(self):
        doc = self.report["document"]
        self.assertEqual(doc["owed_at_stated_rate_per_source_pesos"], 363)
        self.assertEqual(doc["tributaries_times_stated_rate"], {"pesos": 391, "reales": 7, "quartillos": 0})

    def test_kh0326_sequence_transcription_was_checked_against_the_source(self):
        claim = next(c for c in self.report["claims"] if c["id"] == "identifier_recto_63_verso_70")
        self.assertIn("checked against the preprint", claim["note"])

    def test_alignment_under_corpus_counts(self):
        a = self.report["alignment_with_corpus_counts"]
        self.assertEqual(a["best_verso"], ["Cuyuchin", "Guauyan", "Namus"])
        self.assertEqual(a["floor_error"], a["best_error"])

    def test_chance_check_is_deterministic_and_labelled(self):
        c = self.report["chance_check"]
        self.assertEqual(c["label"], "OURS_EXPLORATORY_NOT_IN_SOURCE")
        self.assertEqual(c["trials"], self.sv.CHANCE_TRIALS)
        self.assertTrue(0.0 < c["fraction_with_a_floor_split"] < 1.0)
        self.assertEqual(c, self.sv.audit()["chance_check"])

    def test_sealed_report_matches_recomputation(self):
        sealed = json.loads(SEALED.read_text(encoding="utf-8"))
        self.assertEqual(sealed, json.loads(json.dumps(self.report)))
        self.assertEqual(sealed["report_sha256"], self.sv.digest(sealed))


if __name__ == "__main__":
    unittest.main()
