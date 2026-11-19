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
        for name in ("santa_valley_v1.json", "puruchuco_v1.json"):
            for claim in sealed(name)["claims"]:
                self.assertRegex(self.text,
                                 rf"`{re.escape(claim['id'])}`[^\n]*\*\*{claim['status']}\*\*",
                                 (name, claim["id"]))

    def test_report_digests_are_listed(self):
        for name in ("santa_valley_v1.json", "puruchuco_v1.json", "hidden_cord_v1.json"):
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

    def test_limits_are_stated(self):
        for phrase in ("not decipherment", "post hoc", "No neural model", "were not read"):
            self.assertIn(phrase, self.text, phrase)
        self.assertNotRegex(self.text, r"(?i)\bwe (have )?deciphered\b")


if __name__ == "__main__":
    unittest.main()
