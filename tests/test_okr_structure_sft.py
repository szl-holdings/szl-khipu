#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Canonical OKR structure SFT/eval builder: sealed rebuild, split, labels and fail-closed unknowns."""

import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "research" / "okr_structure_sft" / "build_structure_sft.py"
_spec = importlib.util.spec_from_file_location("build_structure_sft", SCRIPT)
builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(builder)

TOKEN = re.compile(r"^([A-Z?]{1,2})(\d+)$")


class Rebuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus, cls.train, cls.evals = builder.build()

    def test_rebuild_matches_the_sealed_manifest(self):
        sealed = json.loads(builder.MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(builder.manifest_for(self.corpus, self.train, self.evals), sealed)

    def test_split_is_disjoint_and_follows_the_khipu_id_rule(self):
        train_k = {r["khipu"] for r in self.train}
        eval_k = {r["khipu"] for r in self.evals}
        self.assertFalse(train_k & eval_k)
        self.assertEqual((len(train_k), len(eval_k)), (550, 61))
        by_okr = self.corpus["by_okr"]
        self.assertTrue(all(builder.held_out(by_okr[k]) for k in eval_k))
        self.assertFalse(any(builder.held_out(by_okr[k]) for k in train_k))
        self.assertFalse(any(r["tier"] == "okr-cord-sequence" for r in self.evals))

    def test_every_cipher_label_is_the_canonical_sum_of_its_listed_knots(self):
        rows = [r for r in self.train + self.evals if r["tier"] == "okr-cipher-qa"]
        self.assertEqual(sum(1 for r in self.evals if r["tier"] == "okr-cipher-qa"), 282)
        for r in rows:
            tokens = re.search(r"= (.+?)\. A knot", r["prompt"]).group(1).split(", ")
            values = []
            for t in tokens:
                m = TOKEN.match(t)
                self.assertIsNotNone(m, f"unknown or malformed knot in a scored row: {t!r}")
                values.append(int(m.group(2)))
            self.assertEqual(int(r["completion"]), sum(values), r["prompt"])
            self.assertEqual(r["rule"], "canonical")

    def test_pendant_sums_are_well_posed(self):
        for r in self.train + self.evals:
            if r["tier"] != "okr-pendant-sum-qa":
                continue
            listed = re.search(r"\[(.*)\]", r["prompt"]).group(1)
            self.assertNotIn("?", listed)
            self.assertEqual(int(r["completion"]), sum(int(x) for x in listed.split(", ")))

    def test_long_knot_counts_once(self):
        kh0256 = [r for r in self.evals if r["khipu"] == "KH0256" and r["tier"] == "okr-cipher-qa"]
        self.assertIn("S100, S100, S10, S10, L2.", kh0256[0]["prompt"])
        self.assertEqual(kh0256[0]["completion"], "222")

    def test_broken_knotless_pendants_are_unknown_not_zero(self):
        summary = next(r for r in self.train if r["khipu"] == "KH0255" and r["tier"] == "okr-structure-qa")
        self.assertIn("total decimal value unknown (3 pendant cords have unknown values", summary["completion"])
        seq = next(r for r in self.train if r["khipu"] == "KH0255" and r["tier"] == "okr-cord-sequence")
        self.assertTrue(seq["text"].split(": ", 1)[1].startswith("c1[len=0.5,col=AB,val=?,k=-]"))
        self.assertFalse(any(r["khipu"] == "KH0255" and r["tier"] == "okr-pendant-sum-qa" for r in self.train))


if __name__ == "__main__":
    unittest.main()
