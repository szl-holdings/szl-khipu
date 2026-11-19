# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Matching-khipu search and copy-fidelity test: alignment, seeds, nulls, sealed report."""
from __future__ import annotations

import importlib.util
import json
import random
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "research/okr_readings/matching_khipus.py"
SEALED = ROOT / "research/okr_readings/matching_khipus_v1.json"
INFO = {v: 2.0 if v < 2 else 10.0 for v in range(0, 2000)}


def _load():
    spec = importlib.util.spec_from_file_location("szl_okr_matching_khipus_test", FILE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Alignment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mk = _load()

    def test_identical_sequences_align_cord_for_cord(self):
        seq = [12, 7, 305, 0, 44, 9]
        score, pairs = self.mk.align(seq, seq, INFO)
        self.assertEqual(pairs, [(i, i) for i in range(6)])
        self.assertAlmostEqual(score, 5 * 10.0 + 2.0)

    def test_a_missing_cord_is_bridged_by_a_gap(self):
        a = [12, 7, 305, 44, 9, 61]
        b = [12, 7, 305, 999, 44, 9, 61]
        _, pairs = self.mk.align(a, b, INFO)
        self.assertEqual(pairs, [(0, 0), (1, 1), (2, 2), (3, 4), (4, 5), (5, 6)])

    def test_values_one_apart_count_half_and_unknowns_count_nothing(self):
        score, pairs = self.mk.align([126, None, 229], [127, 55, 229], INFO)
        self.assertEqual(pairs, [(0, 0), (1, 1), (2, 2)])
        self.assertAlmostEqual(score, 5.0 + 0.0 + 10.0)

    def test_unrelated_sequences_do_not_align(self):
        score, pairs = self.mk.align([12, 7, 305], [44, 9, 61], INFO)
        self.assertEqual((score, pairs), (0.0, []))


class Seeds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mk = _load()

    def test_shared_informative_trigram_seeds_a_pair_in_the_right_orientation(self):
        # Two rare values and a common one: enough bits for a trigram seed, too
        # few rare values for the shared-rare-value seed that ignores order.
        seqs = {"A": [5, 1, 12, 7, 1], "B": [0, 7, 12, 1, 0], "C": [1, 12, 7], "D": [1, 1, 1, 1]}
        seeds = self.mk.seed_pairs(seqs, INFO)
        self.assertIn(("A", "C", "fwd"), seeds)
        self.assertIn(("A", "B", "rev"), seeds)
        self.assertNotIn(("A", "B", "fwd"), seeds)
        self.assertFalse(any("D" in s[:2] for s in seeds))

    def test_three_shared_rare_values_within_one_seed_both_orientations(self):
        seqs = {"A": [126, 0, 229, 0, 367], "B": [368, 1, 1, 127, 1, 229]}
        seeds = self.mk.seed_pairs(seqs, INFO)
        self.assertEqual({s for s in seeds if s[:2] == ("A", "B")}, {("A", "B", "fwd"), ("A", "B", "rev")})

    def test_two_shared_rare_values_are_not_enough(self):
        self.assertEqual(self.mk.seed_pairs({"A": [126, 0, 229], "B": [229, 1, 126]}, INFO), set())


class Bound(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mk = _load()

    def test_the_cheap_bound_never_undercuts_the_alignment(self):
        rng = random.Random(11)
        for _ in range(200):
            a = [rng.choice([0, 1, 12, 13, 40, 41, 305, None]) for _ in range(rng.randrange(1, 12))]
            b = [rng.choice([0, 1, 12, 13, 40, 41, 305, None]) for _ in range(rng.randrange(1, 12))]
            score, pairs = self.mk.align(a, b, INFO)
            exact = sum(1 for i, j in pairs if a[i] is not None and a[i] == b[j] and a[i] > 0)
            top_score, top_exact = self.mk.bound(a, b, INFO)
            self.assertGreaterEqual(top_score + 1e-9, score, (a, b))
            self.assertGreaterEqual(top_exact, exact, (a, b))

    def test_the_bound_is_zero_for_khipus_with_nothing_in_common(self):
        self.assertEqual(self.mk.bound([12, 7, 305], [44, 9, 61], INFO), (0.0, 0))


class OrderNull(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mk = _load()

    def test_a_long_identical_run_beats_every_shuffle(self):
        rng = random.Random(4)
        seq = [rng.randrange(2, 900) for _ in range(40)]
        p = self.mk.order_p(seq, seq, INFO, trials=50, seed="t")
        self.assertEqual(p, round(1 / 51, 4))

    def test_same_values_in_scrambled_order_do_not(self):
        rng = random.Random(4)
        seq = [rng.randrange(2, 900) for _ in range(40)]
        other = seq[:]
        rng.shuffle(other)
        self.assertGreater(self.mk.order_p(seq, other, INFO, trials=50, seed="t"), 0.1)


    def test_the_null_reports_how_far_the_shuffles_got(self):
        rng = random.Random(4)
        seq = [rng.randrange(2, 900) for _ in range(40)]
        null = self.mk.order_null(seq, seq, INFO, trials=50, seed="t")
        self.assertEqual(null["p_order"], self.mk.order_p(seq, seq, INFO, trials=50, seed="t"))
        self.assertLess(null["null_max_bits"], 400.0)
        self.assertLessEqual(null["null_mean_bits"], null["null_max_bits"])


class Lengths(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mk = _load()

    def test_one_object_measured_twice_agrees_to_the_centimetre(self):
        rows = [(30.0 + 3 * i, 30.5 + 3 * i) for i in range(12)]
        r = self.mk.length_agreement(rows)
        self.assertEqual((r["compared"], r["median_abs_diff_cm"]), (12, 0.5))
        self.assertEqual(r["spearman"], 1.0)
        self.assertTrue(self.mk.one_object(129.5, 129.0, r))

    def test_unrecorded_lengths_are_left_out(self):
        r = self.mk.length_agreement([(30.0, 31.0), (0.0, 40.0), (None, 12.0), (44.0, 0)])
        self.assertEqual(r["compared"], 1)
        self.assertIsNone(r["spearman"])

    def test_two_khipus_of_different_size_are_not_one_object(self):
        rows = [(60.0 + (i * 7) % 11, 40.0 + (i * 5) % 13) for i in range(20)]
        r = self.mk.length_agreement(rows)
        self.assertGreater(r["median_abs_diff_cm"], 3.0)
        self.assertFalse(self.mk.one_object(210.0, 66.0, r))

    def test_a_missing_main_cord_length_never_counts_as_one_object(self):
        r = self.mk.length_agreement([(30.0 + i, 30.0 + i) for i in range(12)])
        self.assertFalse(self.mk.one_object(0, 77.0, r))
        self.assertFalse(self.mk.one_object(None, None, r))

    def test_cords_agreeing_under_main_cords_of_different_length_are_not_one_object(self):
        r = self.mk.length_agreement([(30.0 + i, 30.0 + i) for i in range(12)])
        self.assertFalse(self.mk.one_object(100.0, 80.0, r))


class Breakage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mk = _load()

    def test_a_value_that_lost_its_lower_knots_is_a_truncation(self):
        self.assertEqual(self.mk.truncated(4130, 4000), 3)
        self.assertEqual(self.mk.truncated(932, 900), 2)
        self.assertEqual(self.mk.truncated(1074, 1070), 1)
        self.assertEqual(self.mk.truncated(110, 100), 2)

    def test_other_differences_are_not_truncations(self):
        for high, low in ((1036, 136), (575, 400), (100, 110), (5, 0), (12, 12), (None, 10), (10, None)):
            self.assertIsNone(self.mk.truncated(high, low), (high, low))

    def test_truncations_on_shorter_cords_are_counted_against_a_fair_coin(self):
        # rows: (value on a, value on b, cm on a, cm on b); b's cords run at 0.8 of a's.
        rows = [(4130, 4000, 50.0, 7.0), (932, 900, 48.0, 16.5), (1074, 1070, 41.5, 21.5),
                (1036, 136, 49.5, 46.5), (447, None, 40.0, 3.0), (20, 20, 40.0, 32.0)]
        r = self.mk.breakage(rows, ratio=0.8)
        self.assertEqual((r["differing"], r["truncated"], r["truncated_with_lengths"]), (4, 3, 3))
        self.assertEqual((r["truncated_on_b"], r["truncated_on_shorter_cord"]), (3, 3))
        self.assertEqual(r["p_shorter"], round(1 / 8, 4))
        self.assertEqual((r["unreadable"], r["unreadable_on_shorter_cord"]), (1, 1))

    def test_a_truncation_on_the_longer_cord_counts_against_breakage(self):
        r = self.mk.breakage([(4130, 4000, 10.0, 60.0)], ratio=1.0)
        self.assertEqual((r["truncated"], r["truncated_on_shorter_cord"], r["p_shorter"]), (1, 0, 1.0))


class Fidelity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mk = _load()

    def test_agreement_counts_only_cords_where_both_sides_are_recorded(self):
        rows = [("W", "W", 5), ("AB", "W", 5), (None, "W", 7), ("AB", "AB", 9)]
        r = self.mk.fidelity(rows, trials=50, seed="t")
        self.assertEqual((r["agree"], r["compared"]), (2, 3))

    def test_a_copied_pattern_beats_the_shuffle_and_an_inverted_one_falls_below_it(self):
        same = [("S" if i % 3 else "Z", "S" if i % 3 else "Z", i) for i in range(30)]
        flipped = [(a, "Z" if b == "S" else "S", v) for a, b, v in same]
        self.assertEqual(self.mk.fidelity(same, trials=200, seed="t")["p_above"], round(1 / 201, 4))
        self.assertEqual(self.mk.fidelity(flipped, trials=200, seed="t")["p_below"], round(1 / 201, 4))

    def test_value_strata_show_when_agreement_is_only_the_values_agreeing(self):
        # Direction is a function of the value on both khipus, so inside a value
        # stratum nothing can move and the stratified null equals the observation.
        rows = [("S", "S", 1)] * 10 + [("Z", "Z", 4)] * 10
        r = self.mk.fidelity(rows, trials=100, seed="t")
        self.assertEqual(r["p_above"], round(1 / 101, 4))
        self.assertEqual(r["movable_within_value"], 0)
        self.assertEqual(r["p_above_within_value"], 1.0)

    def test_a_consistent_relabelling_is_seen_even_when_no_code_is_equal(self):
        # Two recorders, or two makers, may use different names for the same
        # distinction: count the cords that follow the commonest a-to-b pairing.
        rows = [(("LB", "YG", "W")[i % 3], ("RB", "GG", "AB")[i % 3], i) for i in range(30)]
        r = self.mk.fidelity(rows, trials=200, seed="t")
        self.assertEqual((r["agree"], r["consistent"], r["compared"]), (0, 30, 30))
        self.assertEqual(r["p_consistent"], round(1 / 201, 4))

    def test_a_feature_that_never_varies_is_consistent_but_proves_nothing(self):
        r = self.mk.fidelity([("S", "S", i) for i in range(20)], trials=100, seed="t")
        self.assertEqual((r["consistent"], r["p_consistent"]), (20, 1.0))

    def test_dominant_value_needs_a_clear_majority(self):
        self.assertEqual(self.mk.dominant(["R"] * 9 + ["V"]), "R")
        self.assertEqual(self.mk.dominant(["R"] * 6 + ["V"] * 4), "mixed")
        self.assertIsNone(self.mk.dominant(["R", None, None]))


class Catalogue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mk = _load()
        cls.sealed = json.loads(SEALED.read_text(encoding="utf-8"))

    def test_scope(self):
        r = self.sealed
        self.assertEqual(r["schema"], self.mk.SCHEMA)
        self.assertEqual(r["status"], "POST_HOC_EXPLORATORY_SEARCH")
        for flag in ("preregistered", "historical_khipu_decipherment", "meaning_assigned_to_any_feature",
                     "pairs_verified_on_the_objects", "signature_verified"):
            self.assertIs(r[flag], False, flag)

    def test_candidates_and_scores_match_recomputation(self):
        fresh = self.mk.audit(trials=0)
        self.assertEqual(fresh["search"], self.sealed["search"])
        self.assertEqual([(p["a"], p["b"], p["orientation"], p["score_bits"]) for p in fresh["scored"]],
                         [(p["a"], p["b"], p["orientation"], p["score_bits"]) for p in self.sealed["scored"]])

    def test_known_puruchuco_pairs_are_found(self):
        found = {frozenset((p["a_name"], p["b_name"])) for p in self.sealed["pairs"]}
        for pair in (("UR064", "UR068"), ("UR066", "UR067")):
            self.assertIn(frozenset(pair), found, pair)
        status = {c["id"]: c["status"] for c in self.sealed["known_pairs"]}
        self.assertEqual(status["UR064~UR068"], "REPLICATED")
        self.assertEqual(status["UR066~UR067"], "REPLICATED")
        self.assertIn(status["UR063~UR073"], ("REPLICATED", "PARTIAL", "NOT_FOUND"))

    def test_every_accepted_pair_beats_its_own_order_shuffles(self):
        floor = round(1 / (self.mk.N_ORDER + 1), 4)
        self.assertGreaterEqual(len(self.sealed["pairs"]), 8)
        for p in self.sealed["pairs"]:
            self.assertEqual(p["p_order"], floor, (p["a_name"], p["b_name"]))
            self.assertGreaterEqual(p["exact_nonzero"], self.mk.MIN_EXACT)
            for feature in self.mk.FEATURES:
                self.assertIn(feature, p["fidelity"])

    def test_every_accepted_pair_clears_the_best_shuffle(self):
        for p in self.sealed["pairs"]:
            self.assertLess(p["null_max_bits"], p["score_bits"], (p["a_name"], p["b_name"]))
            self.assertEqual(len(p["span"]), 2)

    def test_a_khipu_entered_twice_is_told_apart_from_two_khipus(self):
        by = {frozenset((p["a_name"], p["b_name"])): p for p in self.sealed["pairs"]}
        twice = by[frozenset(("UR1107", "UR237"))]
        self.assertTrue(twice["one_object_suspected"])
        self.assertLessEqual(twice["cord_length"]["median_abs_diff_cm"], 2.0)
        self.assertEqual(twice["orientation"], "rev")
        for pair in (("UR064", "UR068"), ("UR066", "UR067"), ("UR1175", "UR233")):
            self.assertFalse(by[frozenset(pair)]["one_object_suspected"], pair)
        groups = self.sealed["fidelity_summary"]
        self.assertEqual(set(groups), {"two_objects", "one_object_suspected"})
        self.assertEqual(groups["one_object_suspected"]["pairs"] + groups["two_objects"]["pairs"],
                         len(self.sealed["pairs"]))

    def test_the_damaged_partner_explains_the_lima_goteborg_disagreements(self):
        by = {frozenset((p["a_name"], p["b_name"])): p for p in self.sealed["pairs"]}
        pair = by[frozenset(("AS038/HP036", "UR122"))]
        damage = pair["breakage"]
        self.assertGreaterEqual(damage["truncated"], 4)
        self.assertEqual(damage["truncated_on_b"], damage["truncated"])
        self.assertEqual(damage["truncated_on_shorter_cord"], damage["truncated_with_lengths"])
        self.assertGreaterEqual(damage["unreadable"], 10)
        self.assertEqual(damage["unreadable_on_shorter_cord"], damage["unreadable_with_lengths"])

    def test_known_duplicates_are_credited_to_their_source(self):
        flagged = {frozenset((p["a_name"], p["b_name"])) for p in self.sealed["pairs"] if p["one_object_suspected"]}
        credited = {frozenset(entry["pair"]) for entry in self.sealed["prior_art"]
                    if entry["kind"] == "listed_duplicate"}
        self.assertEqual(flagged, credited)
        for entry in self.sealed["prior_art"]:
            self.assertTrue(entry["seen_via"] and entry["source"], entry)
            if entry["kind"] != "okr_note":
                self.assertIn("khipufieldguide.com", entry["source"])

    def test_one_long_khipu_carries_the_runs_of_two_shorter_ones(self):
        by = {frozenset((p["a_name"], p["b_name"])): p for p in self.sealed["pairs"]}
        first, second = by[frozenset(("UR1175", "UR233"))], by[frozenset(("UR1175", "UR232"))]
        self.assertLess(first["span"][0][1], second["span"][0][0])

    def test_one_pair_null_matches_recomputation(self):
        want = self.sealed["pairs"][0]
        fresh = self.mk.audit(only=(want["a"], want["b"]))
        self.assertEqual(fresh["pairs"], [want])

    def test_sealed_digest(self):
        self.assertEqual(self.sealed["report_sha256"], self.mk.digest(self.sealed))


if __name__ == "__main__":
    unittest.main()
