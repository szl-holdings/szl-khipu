# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Hidden-cord information test: leave-one-out arithmetic, leak guard, sealed report."""
from __future__ import annotations

import importlib.util
import json
import math
import random
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "research/okr_readings/hidden_cord.py"
SEALED = ROOT / "research/okr_readings/hidden_cord_v1.json"
HALF = {"A": 0.5, "B": 0.5}


def _load():
    spec = importlib.util.spec_from_file_location("szl_okr_hidden_cord_test", FILE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LeaveOneOutArithmetic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hc = _load()

    def test_khipu_model_hides_the_cord_being_scored(self):
        # A: (2-1+0.5)/(3-1+1) = 1/2 ; B: (1-1+0.5)/3 = 1/6
        cost = self.hc.bits_khipu(["A", "A", "B"], HALF)
        self.assertAlmostEqual(cost, 2.0 + math.log2(6), places=12)

    def test_context_model_backs_off_to_the_khipu_model(self):
        # A in context x: (2-1+0.5)/(2-1+1) = 3/4 ; B alone in context y: (0+1/6)/(0+1) = 1/6
        cost = self.hc.bits_context(["x", "x", "y"], ["A", "A", "B"], HALF)
        self.assertAlmostEqual(cost, 2 * math.log2(4 / 3) + math.log2(6), places=12)

    def test_constant_context_costs_about_the_same_as_no_context(self):
        rng = random.Random(3)
        values = [rng.choice("AAB") for _ in range(400)]
        delta = self.hc.bits_context(["k"] * 400, values, HALF) - self.hc.bits_khipu(values, HALF)
        self.assertLess(abs(delta) / 400, 0.001)

    def test_informative_context_costs_fewer_bits(self):
        values = ["A", "B"] * 50
        keys = ["odd" if v == "A" else "even" for v in values]
        self.assertLess(self.hc.bits_context(keys, values, HALF), 0.2 * self.hc.bits_khipu(values, HALF))

    def test_neighbour_probability_on_an_alternating_sequence(self):
        seq = ["A", "B"] * 4
        # cord 2 sees (B, B); the two other (B, B) cords are both A; khipu model gives 3.5/8
        self.assertAlmostEqual(self.hc.neighbour_prob([seq], 0, 2, HALF), (2 + 3.5 / 8) / 3, places=12)

    def test_neighbour_model_never_counts_a_cord_whose_context_contains_the_hidden_value(self):
        # In AAAA, cord 2's context (A, A) only exists because cord 1 is A, so scoring
        # cord 1 must not use it: the estimate falls back to the khipu model, 3.5/4.
        self.assertAlmostEqual(self.hc.neighbour_prob([["A"] * 4], 0, 1, HALF), 3.5 / 4, places=12)

    def test_neighbours_do_not_cross_primary_cords(self):
        split = self.hc.bits_neighbours([["A", "B", "A"], ["B", "A", "B"]], HALF)
        joined = self.hc.bits_neighbours([["A", "B", "A", "B", "A", "B"]], HALF)
        self.assertNotAlmostEqual(split, joined, places=6)

    def test_unrecorded_slots_are_context_but_never_scored(self):
        with_gap = self.hc.bits_neighbours([["A", None, "A", "A"]], HALF)
        self.assertGreater(with_gap, 0.0)
        self.assertEqual(self.hc.bits_neighbours([[None, None]], HALF), 0.0)

    def test_structured_sequence_gains_and_random_sequences_do_not(self):
        alternating = ["A", "B"] * 30
        gain = self.hc.bits_khipu(alternating, HALF) - self.hc.bits_neighbours([alternating], HALF)
        self.assertGreater(gain / 60, 0.5)
        rng = random.Random(7)
        total_gain, cords = 0.0, 0
        for _ in range(300):
            seq = [rng.choice("AB") for _ in range(12)]
            total_gain += self.hc.bits_khipu(seq, HALF) - self.hc.bits_neighbours([seq], HALF)
            cords += 12
        self.assertLess(total_gain / cords, 0.02)

    def test_value_classes(self):
        vc = self.hc.value_class
        self.assertEqual([vc(0, "knotless"), vc(7, "known"), vc(10, "known"), vc(99, "known"),
                          vc(100, "known"), vc(999, "known"), vc(1000, "known")],
                         ["0", "1-9", "10-99", "10-99", "100-999", "100-999", "1000+"])
        self.assertIsNone(vc(None, "unknown"))

    def test_position_is_counted_inside_each_cluster_and_capped(self):
        clusters = [1, 1, 1, 2, 2] + [3] * 15
        got = self.hc.positions(clusters)
        self.assertEqual(got[:5], [0, 1, 2, 0, 1])
        self.assertEqual(got[-1], self.hc.POSITION_CAP)


class WithinClusterShuffle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hc = _load()

    def test_values_stay_inside_their_cluster_and_gaps_stay_put(self):
        column = ["A", "B", None, "C", "D", "E", None, "F"]
        runs = [(0, 3), (3, 8)]
        out = self.hc.shuffle_within(column, runs, random.Random(5))
        self.assertEqual([i for i, v in enumerate(out) if v is None], [2, 6])
        self.assertEqual(sorted(v for v in out[0:3] if v), ["A", "B"])
        self.assertEqual(sorted(v for v in out[3:8] if v), ["C", "D", "E", "F"])
        self.assertEqual(column, ["A", "B", None, "C", "D", "E", None, "F"])

    def test_it_actually_moves_values(self):
        column = list("ABCDEFGHIJKL")
        self.assertNotEqual(self.hc.shuffle_within(column, [(0, 12)], random.Random(5)), column)

    def test_cluster_runs_follow_consecutive_cluster_ids(self):
        self.assertEqual(self.hc.runs([7, 7, 7, 9, 9, 7]), [(0, 3), (3, 5), (5, 6)])


class HiddenCordCorpus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hc = _load()
        cls.sealed = json.loads(SEALED.read_text(encoding="utf-8"))
        cls.observed = cls.hc.audit(trials=0)

    def test_claim_scope(self):
        r = self.sealed
        self.assertEqual(r["schema"], self.hc.SCHEMA)
        self.assertEqual(r["status"], "POST_HOC_EXPLORATORY_INFORMATION_TEST")
        for flag in ("preregistered", "historical_khipu_decipherment", "meaning_assigned_to_any_feature",
                     "neural_model_evaluated", "independent_research_lab_replication",
                     "signature_verified"):
            self.assertIs(r[flag], False, flag)
        self.assertEqual(r["parameters"]["trials"], self.hc.TRIALS)

    def test_inputs_are_pinned(self):
        r = self.sealed
        self.assertEqual(r["input_corpus_sha256"],
                         "6ef204b641826b37c320509952ed4181e93865af20f1cdfefd7516a49cf8ad0d")
        self.assertEqual(r["input_features_sha256"],
                         "1cd7c4cd822e0783969ca69a2dfae484b8c81b48ca57989fb535d53367e1d3c9")

    def test_every_target_reports_every_context(self):
        for target in self.hc.TARGETS:
            block = self.sealed["targets"][target]
            self.assertEqual(sorted(block["contexts"]), sorted(self.hc.contexts_for(target)), target)
            self.assertGreaterEqual(block["khipus"], 1)
            self.assertGreater(block["cords"], block["khipus"] * (self.hc.MIN_RECORDED - 1))

    def test_definitional_pairs_are_not_scored(self):
        self.assertNotIn("knot_dir", self.sealed["targets"]["value_class"]["contexts"])
        self.assertNotIn("value_class", self.sealed["targets"]["knot_dir"]["contexts"])
        self.assertIn(["value_class", "knot_dir"], self.sealed["definitional_pairs_not_scored"])

    def test_observed_values_match_recomputation(self):
        for target in self.hc.TARGETS:
            want, got = self.sealed["targets"][target], self.observed["targets"][target]
            for key in ("khipus", "cords", "alphabet_size", "bits_per_cord_corpus", "bits_per_cord_khipu"):
                self.assertEqual(want[key], got[key], (target, key))
            for context, row in want["contexts"].items():
                self.assertEqual(row["gain_bits_per_cord"],
                                 got["contexts"][context]["gain_bits_per_cord"], (target, context))

    def test_shuffle_null_for_one_target_matches_recomputation(self):
        again = self.hc.audit(trials=self.hc.TRIALS, targets=("attach",))
        self.assertEqual(again["targets"]["attach"], self.sealed["targets"]["attach"])

    def test_verdicts_follow_the_stated_rule(self):
        floor = round(1 / (self.hc.TRIALS + 1), 4)
        for target, block in self.sealed["targets"].items():
            for context, row in block["contexts"].items():
                gain, top = row["gain_bits_per_cord"], row["null_max"]
                if gain <= top:
                    want = "NOT_ABOVE_SHUFFLE_NULL"
                elif gain > 0:
                    want = "ABOVE_SHUFFLE_NULL_NET_SAVING"
                else:
                    want = "ABOVE_SHUFFLE_NULL_NO_NET_SAVING"
                self.assertEqual(row["verdict"], want, (target, context))
                self.assertEqual(row["p_upper"] == floor, gain > top, (target, context))
                self.assertEqual(row["excess_bits_per_cord"], round(gain - row["null_mean"], 4),
                                 (target, context))

    def test_feature_links_also_face_a_within_cluster_shuffle(self):
        for target, block in self.sealed["targets"].items():
            for context, row in block["contexts"].items():
                if context in self.hc.STRUCTURE:
                    self.assertNotIn("cluster_null_max", row, (target, context))
                    continue
                self.assertEqual(row["survives_within_cluster_shuffle"],
                                 row["gain_bits_per_cord"] > row["cluster_null_max"], (target, context))
                self.assertEqual(row["excess_within_cluster"],
                                 round(row["gain_bits_per_cord"] - row["cluster_null_mean"], 4),
                                 (target, context))

    def test_enough_shuffles_for_a_one_percent_floor(self):
        self.assertGreaterEqual(self.hc.TRIALS, 100)

    def test_colour_is_strongly_predicted_by_its_neighbours(self):
        row = self.sealed["targets"]["colour"]["contexts"]["neighbours"]
        self.assertEqual(row["verdict"], "ABOVE_SHUFFLE_NULL_NET_SAVING")
        self.assertGreater(row["gain_bits_per_cord"], 0.5)

    def test_spin_and_fibre_are_almost_entirely_khipu_level(self):
        for target in ("spin", "fibre"):
            self.assertLess(self.sealed["targets"][target]["bits_per_cord_khipu"], 0.05, target)

    def test_santa_valley_block_covers_the_six_khipus(self):
        self.assertEqual(sorted(self.sealed["santa_valley"]),
                         ["KH0323", "KH0324", "KH0325", "KH0326", "KH0327", "KH0328"])

    def test_sealed_digest(self):
        self.assertEqual(self.sealed["report_sha256"], self.hc.digest(self.sealed))


if __name__ == "__main__":
    unittest.main()
