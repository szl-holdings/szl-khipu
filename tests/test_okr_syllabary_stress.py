# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Stress test of a published syllabary proposal: scoring rule, shuffles, refits, sealed report."""
from __future__ import annotations

import importlib.util
import json
import os
import random
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "research/okr_readings/syllabary_stress.py"
SEALED = ROOT / "research/okr_readings/syllabary_stress_v1.json"
DICT_DIR = os.environ.get("SZL_ALBA_DICT_DIR")


def _load():
    spec = importlib.util.spec_from_file_location("szl_okr_syllabary_stress_test", FILE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def knot(kind, turns=None):
    return {"type": kind, "turns": turns}


class CordSymbols(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ss = _load()

    def test_two_long_or_figure_eight_knots_make_a_string_cord(self):
        self.assertEqual(self.ss.classify([knot("L", 4), knot("S"), knot("L", 8), knot("E")]),
                         (True, (4, 8, "E")))

    def test_one_long_knot_is_an_ordinary_number_cord(self):
        self.assertEqual(self.ss.classify([knot("S"), knot("L", 4)]), (False, None))

    def test_long_knots_without_a_turn_count_are_dropped_from_the_sequence(self):
        self.assertEqual(self.ss.classify([knot("L", None), knot("L", 3)]), (True, None))
        self.assertEqual(self.ss.classify([knot("L", None), knot("L", 3), knot("E")]), (True, (3, "E")))

    def test_other_knot_types_are_not_symbols(self):
        self.assertEqual(self.ss.classify([knot("EE"), knot("LL", 3), knot("L", 3)]), (False, None))


class ScoringRule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ss = _load()

    def test_lookup_adds_suffixed_forms_and_prefixes_of_four_or_more_letters(self):
        lookup = self.ss.build_lookup({"mama"})
        for form in ("mama", "mamata", "mamat", "mamay"):
            self.assertIn(form, lookup, form)
        self.assertNotIn("mam", lookup)
        self.assertNotIn("tama", lookup)

    def test_exact_rule_has_no_expansion(self):
        self.assertEqual(self.ss.build_exact({"mama", "Pata ", ""}), {"mama", "pata"})

    def test_score_counts_cords_whose_reading_is_in_the_lookup(self):
        mapping = {3: "ma", 4: "ka", "E": "qa"}
        seqs = Counter({(3, 3): 2, (4, 3): 1, (3, 9): 5, (3,): 4})
        self.assertEqual(self.ss.score(mapping, seqs, {"mama", "kama", "ma"}), 3)

    def test_density_is_the_share_of_all_possible_readings_that_count(self):
        self.assertEqual(self.ss.density(("ma", "ka"), {"mama", "kama"}, 2), 0.5)

    def test_onset_coda_reading_uses_the_onset_form_only_first(self):
        onset, coda = {7: "wa", 3: "ma"}, {7: "y", 3: "ma"}
        self.assertEqual(self.ss.read((7, 3, 7), onset, coda), "wamay")
        self.assertIsNone(self.ss.read((7, 99), onset, coda))


class Shuffles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ss = _load()
        cls.by_khipu = {"A": [(1, 2, 3), (4, 5)], "B": [(6, 6), (7, 8, 9)]}

    def test_order_shuffle_keeps_each_cords_own_symbols(self):
        out = self.ss.shuffle_order(self.by_khipu, random.Random(1))
        for name, seqs in self.by_khipu.items():
            self.assertEqual([sorted(s) for s in out[name]], [sorted(s) for s in seqs])

    def test_khipu_shuffle_keeps_lengths_and_each_khipus_symbol_pool(self):
        out = self.ss.shuffle_khipu(self.by_khipu, random.Random(1))
        for name, seqs in self.by_khipu.items():
            self.assertEqual([len(s) for s in out[name]], [len(s) for s in seqs])
            self.assertEqual(sorted(x for s in out[name] for x in s), sorted(x for s in seqs for x in s))

    def test_khipu_shuffle_moves_symbols_between_cords(self):
        big = {"A": [tuple(range(i, i + 3)) for i in range(0, 60, 3)]}
        self.assertNotEqual(self.ss.shuffle_khipu(big, random.Random(1)), big)


class Refit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ss = _load()

    def test_fit_recovers_a_planted_mapping(self):
        truth = {1: "ma", 2: "ka", 3: "ta"}
        words = {"mama", "kama", "taka", "maka", "tata"}
        inverse = {v: k for k, v in truth.items()}
        seqs = Counter()
        for w in words:
            seqs[(inverse[w[:2]], inverse[w[2:]])] += 5
        fitted, hits = self.ss.fit(seqs, ("ma", "ka", "ta", "pa", "si"), words, seed=3,
                                   start={1: "pa", 2: "si", 3: "ka"})
        self.assertEqual(hits, 25)
        self.assertEqual(fitted, truth)

    def test_fit_never_scores_below_its_starting_mapping(self):
        seqs = Counter({(1, 2): 3, (2, 1): 2, (1, 1): 1})
        lookup = {"maka", "kama"}
        start = {1: "ma", 2: "ka"}
        _, hits = self.ss.fit(seqs, ("ma", "ka", "ta"), lookup, seed=1, start=start)
        self.assertGreaterEqual(hits, self.ss.score(start, seqs, lookup))

    def test_fit_is_deterministic(self):
        seqs = Counter({(1, 2): 3, (2, 3): 2, (3, 1): 1})
        args = (seqs, ("ma", "ka", "ta", "pa"), {"maka", "kata", "tama", "paka"})
        self.assertEqual(self.ss.fit(*args, seed=5), self.ss.fit(*args, seed=5))


class Corpus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ss = _load()
        cls.sealed = json.loads(SEALED.read_text(encoding="utf-8"))

    def test_scope_and_attribution(self):
        r = self.sealed
        self.assertEqual(r["schema"], self.ss.SCHEMA)
        self.assertEqual(r["status"], "POST_HOC_INDEPENDENT_STRESS_TEST_OF_A_PUBLISHED_PROPOSAL")
        for flag in ("preregistered", "historical_khipu_decipherment", "new_reading_claimed",
                     "third_party_code_executed", "peer_reviewed_source", "signature_verified"):
            self.assertIs(r[flag], False, flag)
        self.assertEqual(r["proposal"]["licence"], "MIT")
        self.assertIn("Sivan", r["proposal"]["cite"])
        self.assertEqual(len(r["proposal"]["repository_commit"]), 40)

    def test_census_matches_the_pinned_corpus(self):
        census = self.ss.census(self.ss.load_corpus())
        self.assertEqual(census, self.sealed["census"])
        self.assertEqual((census["knotted_cords"], census["string_cords"], census["sequences"]),
                         (37082, 2728, 2256))
        self.assertEqual(census["distinct_sequences"], 529)

    def test_census_is_compared_with_the_published_count(self):
        claim = self.sealed["claims"][0]
        self.assertEqual(claim["id"], "string_cords_1992_of_37206")
        self.assertEqual(claim["status"], "PARTIAL")

    def test_the_published_random_mapping_result_is_reproduced_and_qualified(self):
        claim = self.sealed["claims"][1]
        self.assertEqual(claim["id"], "mapping_beats_random_mappings")
        self.assertEqual(claim["status"], "REPLICATED")
        self.assertIn("scrambled", claim["note"])

    def test_scrambled_cords_are_scored_like_real_ones_under_the_published_rule(self):
        rule = self.sealed["dictionaries"]["kaikki_2074"]["rules"]["published_lookup"]
        self.assertGreater(rule["order_shuffle"]["p_upper"], 0.05)
        self.assertGreater(rule["khipu_shuffle"]["p_upper"], 0.05)
        self.assertEqual(rule["refit"]["scrambled_refits_at_or_above_the_proposal"], self.ss.N_REFIT)
        self.assertGreater(rule["density"]["two_syllables"], 0.8)

    def test_enough_refits_for_a_five_percent_floor(self):
        self.assertGreaterEqual(self.ss.N_REFIT, 20)

    def test_every_dictionary_and_rule_is_reported(self):
        for name in self.ss.DICTIONARIES:
            block = self.sealed["dictionaries"][name]
            self.assertEqual(block["sha256"], self.ss.DICTIONARIES[name]["sha256"])
            self.assertEqual(sorted(block["rules"]), ["exact", "published_lookup"])
            for rule in block["rules"].values():
                for key in ("density", "observed", "random_mappings", "order_shuffle",
                            "khipu_shuffle", "refit"):
                    self.assertIn(key, rule)

    def test_p_values_respect_their_floors(self):
        for block in self.sealed["dictionaries"].values():
            for rule in block["rules"].values():
                self.assertGreaterEqual(rule["random_mappings"]["p_upper"],
                                        round(1 / (self.ss.N_RANDOM + 1), 4))
                for key in ("order_shuffle", "khipu_shuffle"):
                    self.assertGreaterEqual(rule[key]["p_upper"], round(1 / (self.ss.N_SHUFFLE + 1), 4))

    def test_sealed_digest(self):
        self.assertEqual(self.sealed["report_sha256"], self.ss.digest(self.sealed))

    @unittest.skipUnless(DICT_DIR, "third-party dictionaries not present (set SZL_ALBA_DICT_DIR)")
    def test_full_recomputation_matches_the_sealed_report(self):
        self.assertEqual(json.loads(json.dumps(self.ss.audit(Path(DICT_DIR)))), self.sealed)

    @unittest.skipUnless(DICT_DIR, "third-party dictionaries not present (set SZL_ALBA_DICT_DIR)")
    def test_a_dictionary_with_the_wrong_digest_is_refused(self):
        with self.assertRaises(self.ss.Hold):
            self.ss.load_words(Path(DICT_DIR) / self.ss.DICTIONARIES["kaikki_2074"]["file"], "0" * 64)


if __name__ == "__main__":
    unittest.main()
