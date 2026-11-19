#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Knot-value rule audit: token parsing, label classification, fail-closed rescoring, sealed corpus replay."""

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "research" / "okr_value_rule" / "audit_value_rule.py"
SEALED = ROOT / "research" / "okr_value_rule" / "value_rule_audit_v1.json"
RELATIONS = ROOT / "research" / "okr_corpus" / "okr_relations_v1.json"

_spec = importlib.util.spec_from_file_location("audit_value_rule", SCRIPT)
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

TEMPLATE = ("Khipu {kh}, cord 1: knots in order (type+place) = {knots}. Using the decimal place system "
            "(1000/100/10/1; single knots count 1, long knots count their turns), what is the cord's total value?")


def row(knots, completion, kh="KH0001"):
    return {"prompt": TEMPLATE.format(kh=kh, knots=knots), "completion": completion, "khipu": kh}


class ParseAndValue(unittest.TestCase):
    def test_long_knot_is_counted_once_under_canonical_and_squared_under_turns_multiplied(self):
        knots = audit.parse_knots("S100, S100, S10, S10, L2.02")
        self.assertEqual(knots[-1], ("L", 2, 2))
        self.assertEqual(audit.cord_value(knots, "canonical"), 222)
        self.assertEqual(audit.cord_value(knots, "turns_multiplied"), 224)
        self.assertEqual(audit.cord_value(audit.parse_knots("S10, L8.08"), "canonical"), 18)
        self.assertEqual(audit.cord_value(audit.parse_knots("S10, L8.08"), "turns_multiplied"), 74)

    def test_multi_letter_types_and_tens_place_long_knot(self):
        knots = audit.parse_knots("EE1, TF10, L30.03")
        self.assertEqual([k[0] for k in knots], ["EE", "TF", "L"])
        self.assertEqual(audit.cord_value(knots, "canonical"), 41)
        self.assertEqual(audit.cord_value(knots, "turns_multiplied"), 101)

    def test_unknown_value_is_none_not_zero(self):
        self.assertIsNone(audit.cord_value(audit.parse_knots("S10, L0.00"), "canonical"))
        self.assertIsNone(audit.cord_value(audit.parse_knots("S0"), "turns_multiplied"))

    def test_bad_tokens_and_rules_hold(self):
        for bad in ("S10, ,L2", "S-10", "L2.x", ""):
            with self.assertRaises(audit.AuditHold):
                audit.parse_knots(bad)
        with self.assertRaises(audit.AuditHold):
            audit.cord_value([("S", 10, None)], "locke")


class Labels(unittest.TestCase):
    def test_classification(self):
        rows = [
            row("S100, S100, S10, S10, L2.02", "224"),
            row("S100, S100, S10, S10, L2.02", "222"),
            row("S10, S10", "20"),
            row("S10, S10", "21"),
            row("L3.03", "7"),
            row("S10, L0.00", "10"),
            row("S10, L2.0x", "12"),
            row("S10", "ten"),
            {"prompt": "Khipu KH0001: summarize its physical structure.", "completion": "..."},
            {"completion": "1"},
        ]
        counts, details = audit.audit_labels(rows)
        self.assertEqual(counts, {
            "gold_canonical": 1, "gold_neither": 1, "gold_turns_multiplied": 1, "not_applicable": 1,
            "rules_agree_gold_ok": 1, "rules_agree_gold_other": 1, "unknown_value": 1, "unparsed": 3,
        })
        self.assertEqual(len(details), 9)

    def test_rescore_reproduces_published_metric_and_scores_canonical(self):
        rows = [row("S10, L2.02", "14", "KH1"), row("S10, L3.03", "19", "KH2"), row("S10", "10", "KH3")]
        _, details = audit.audit_labels(rows)
        preds = [{"khipu": "KH1", "gold": 14, "pred": 14}, {"khipu": "KH2", "gold": 19, "pred": 13},
                 {"khipu": "KH3", "gold": 10, "pred": 10}]
        got = audit.rescore_predictions(details, preds)
        self.assertEqual(got["exact_vs_published_gold"], [2, 3])
        self.assertEqual(got["exact_vs_canonical"], [2, 3])
        self.assertEqual(got["exact_vs_turns_multiplied"], [2, 3])

    def test_misaligned_predictions_are_refused(self):
        _, details = audit.audit_labels([row("S10", "10", "KH1"), row("S1, L2.02", "5", "KH2")])
        with self.assertRaises(audit.AuditHold):
            audit.rescore_predictions(details, [{"khipu": "KH1", "gold": 10, "pred": 10}])
        with self.assertRaises(audit.AuditHold):
            audit.rescore_predictions(details, [{"khipu": "KH1", "gold": 10, "pred": 10},
                                                {"khipu": "KH9", "gold": 5, "pred": 5}])


class PinnedCorpus(unittest.TestCase):
    def test_sealed_result_replays_exactly(self):
        sealed = json.loads(SEALED.read_text(encoding="utf-8"))
        self.assertEqual(audit.corpus_audit(), sealed)

    def test_canonical_rule_matches_the_committed_relations_report(self):
        sealed = json.loads(SEALED.read_text(encoding="utf-8"))
        report = json.loads(RELATIONS.read_text(encoding="utf-8"))
        self.assertEqual(sealed["corpus_sha256"], report["corpus_sha256"])
        self.assertEqual(sealed["relations"]["canonical"], report["statistics"]["observed"])

    def test_turns_multiplied_rule_breaks_top_cord_arithmetic(self):
        rel = json.loads(SEALED.read_text(encoding="utf-8"))["relations"]
        self.assertLess(rel["turns_multiplied"]["R2"], rel["canonical"]["R2"])
        self.assertLess(rel["turns_multiplied"]["R1"], rel["canonical"]["R1"])


if __name__ == "__main__":
    unittest.main()
