# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""The okr_readings README must say what the sealed reports say, and no more."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "research/okr_readings"
README = DIR / "README.md"


def sealed(name: str) -> dict:
    return json.loads((DIR / name).read_text(encoding="utf-8"))


class ReadmeMirrorsSealedReports(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = README.read_text(encoding="utf-8")

    def test_every_claim_status_is_stated_as_sealed(self):
        for name in ("santa_valley_v1.json", "puruchuco_v1.json", "syllabary_stress_v1.json"):
            for claim in sealed(name)["claims"]:
                self.assertRegex(self.text,
                                 rf"`{re.escape(claim['id'])}`[^\n]*\*\*{claim['status']}\*\*",
                                 (name, claim["id"]))

    def test_report_digests_are_listed(self):
        for name in ("santa_valley_v1.json", "puruchuco_v1.json", "hidden_cord_v1.json",
                     "syllabary_stress_v1.json", "knot_direction_v1.json", "matching_khipus_v1.json"):
            self.assertIn(sealed(name)["report_sha256"], self.text, name)

    def test_headline_numbers_match(self):
        band = sealed("santa_valley_v1.json")["rules"]["colour_band"]
        att, first = band["identifier_attachment"], band["first_cord"]
        self.assertIn(f"{att['R']} recto, {att['V']} verso, {att['U']} unspecified", self.text)
        self.assertIn(f"sum to {first['knotted_sum']}", self.text)
        hidden = sealed("hidden_cord_v1.json")["targets"]
        for target, context in (("colour", "neighbours"), ("value_class", "colour"),
                                ("attach", "neighbours"), ("knot_dir", "neighbours")):
            row = hidden[target]["contexts"][context]
            self.assertIn(f"| {target} | {context} | {row['gain_bits_per_cord']:.4f} | "
                          f"{row['excess_bits_per_cord']:.4f} |", self.text, (target, context))

    def test_syllabary_stress_rows_match(self):
        stress = sealed("syllabary_stress_v1.json")
        for name, block in stress["dictionaries"].items():
            for rule, r in block["rules"].items():
                row = (f"| {name} | {rule} | {100 * r['density']['two_syllables']:.1f}% | "
                       f"{r['observed']['hits']} | {r['random_mappings']['null_mean']:.0f} | "
                       f"{r['order_shuffle']['null_mean']:.0f} | {r['khipu_shuffle']['null_mean']:.0f} | "
                       f"{r['refit']['best_hits_on_real_cords']} | "
                       f"{r['refit']['null_min']}-{r['refit']['null_max']} |")
                self.assertIn(row, self.text, (name, rule))
        self.assertIn("It does not show that the proposal is wrong", self.text)
        self.assertIn("Sivan", self.text)

    def test_published_tribute_figures_are_reported_with_the_measured_ones(self):
        first = sealed("santa_valley_v1.json")["rules"]["colour_band"]["first_cord"]
        self.assertIn(f"recto {first['by_published_side_sum']['R']}", self.text)
        self.assertIn(f"verso {first['by_published_side_sum']['V']}", self.text)
        self.assertIn("381 or 382", self.text)

    def test_knot_direction_numbers_match_and_the_old_guess_is_withdrawn(self):
        knots = sealed("knot_direction_v1.json")
        acc = knots["majority_accuracy"]
        self.assertIn(f"{100 * acc['khipu']:.1f}%", self.text)
        self.assertIn(f"{100 * acc['type']:.1f}%", self.text)
        self.assertIn(f"{knots['bits_per_knot_khipu']:.4f}", self.text)
        self.assertIn(f"{knots['contexts']['type']['gain_bits_per_knot']:.4f}", self.text)
        self.assertNotIn("follows something OKR does not record", self.text)
        self.assertIn("largely follows knot type", self.text)

    def test_matching_pairs_are_listed_as_sealed(self):
        match = sealed("matching_khipus_v1.json")
        for p in match["pairs"]:
            row = (f"| {p['a_name']} ~ {p['b_name']} | {p['orientation']} | {p['score_bits']:.1f} | "
                   f"{p['null_max_bits']:.1f} | {p['exact_nonzero']} |")
            self.assertIn(row, self.text, (p["a_name"], p["b_name"]))
        for known in match["known_pairs"]:
            self.assertRegex(self.text, rf"`{re.escape(known['id'])}`[^\n]*\*\*{known['status']}\*\*")
        two = match["fidelity_summary"]["two_objects"]["breakage"]
        self.assertIn(f"{two['unreadable_on_shorter_cord']} of {two['unreadable_with_lengths']}", self.text)
        self.assertIn(f"{two['truncated_on_shorter_cord']} of {two['truncated_with_lengths']}", self.text)

    def test_prior_art_for_the_pairs_is_credited(self):
        for phrase in ("Khipu Field Guide", "Karen Thompson", "Manuel Medrano", "spliced", "Urton and Brezine"):
            self.assertIn(phrase, self.text, phrase)
        # An earlier version credited a duplicate to "Winston Wright" from a search summary;
        # the Field Guide's own pages do not say so.
        self.assertNotIn("Winston Wright", self.text)
        self.assertNotIn("search-engine summaries", self.text)

    def test_the_goteborg_record_is_reported(self):
        for phrase in ("1938.45.0228", "Nordenski\u00f6ld", "24.6.117", "Museo Hist\u00f3rico", "since at least 1929"):
            self.assertIn(phrase, self.text, phrase)

    def test_limits_are_stated(self):
        for phrase in ("not decipherment", "post hoc", "No neural model", "were not read"):
            self.assertIn(phrase, self.text, phrase)
        self.assertNotRegex(self.text, r"(?i)\bwe (have )?deciphered\b")


if __name__ == "__main__":
    unittest.main()
