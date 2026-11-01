# SPDX-License-Identifier: Apache-2.0
"""Independent checks for curriculum label and citation integrity."""
import re
import unittest

from szl_khipu.train import tiny_khipu


class TinyKhipuCurriculumTests(unittest.TestCase):
    def test_full_formula_identifiers_are_not_prefixes(self):
        for token in ("F1", "F4", "F7", "F11", "F12", "F18", "F19", "F22"):
            with self.subTest(token=token):
                self.assertEqual(tiny_khipu._formula_in(f"resolve ({token.lower()})"), token)

    def test_embedded_or_longer_identifiers_are_not_formulas(self):
        for text in ("F100", "F110", "AF1", "F1x", "x_F1", "F1_suffix"):
            with self.subTest(text=text):
                self.assertIsNone(tiny_khipu._formula_in(text))

    def test_known_false_positive_is_abstain(self):
        # Source 8ba6893 labeled this NAVIGATE and cited "ABSTAIN other".
        example = tiny_khipu.synth_curriculum(80, 20260721)[5]
        self.assertEqual(example["query"], "ask about F18 with no handle")
        self.assertEqual(example["handles"][1]["note"], "F1 spare")
        self.assertEqual(example["decision"], tiny_khipu.ABSTAIN)
        self.assertEqual(example["cite"], [])

    def test_generated_labels_and_citations_agree_with_independent_oracle(self):
        # Parse general F+digits tokens, rather than reuse the implementation's
        # locked-formula regular expression or private extraction helper.
        def identifiers(text):
            return set(re.findall(r"\bF[0-9]+\b", text.upper()))

        for seed in (20260721, 11, 23, 37):
            rows = tiny_khipu.synth_curriculum(2000, seed)
            for index, example in enumerate(rows):
                query_ids = identifiers(example["query"])
                matching = [
                    i for i, handle in enumerate(example["handles"])
                    if query_ids.intersection(identifiers(handle["note"]))
                ]
                with self.subTest(seed=seed, index=index):
                    expected = tiny_khipu.NAVIGATE if matching else tiny_khipu.ABSTAIN
                    self.assertEqual(example["decision"], expected)
                    self.assertEqual(example["cite"], matching[:1])
                    self.assertEqual(bool(example["cite"]), bool(matching))
            self.assertEqual(rows, tiny_khipu.synth_curriculum(2000, seed))

    def test_inference_encoding_is_not_silently_migrated(self):
        # This repair does not pretend old artifacts use a new tokenizer.
        self.assertEqual(tiny_khipu.tok_id("F11"), tiny_khipu.tok_id("F1"))


if __name__ == "__main__":
    unittest.main()
