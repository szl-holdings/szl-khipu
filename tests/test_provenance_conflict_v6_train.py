# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""v6 training pack contract: frozen bytes, composition, and disjointness from held-out sets."""
import hashlib, importlib.util, json, unittest
from pathlib import Path

R = Path(__file__).resolve().parents[1] / 'research'
D = R / 'provenance_conflict_v6_train'
PACK_SHA = '77a5963bf9fab9dab46dc3ac6ddfc9c1795896fe567cb1f92030fc4be8883029'

spec = importlib.util.spec_from_file_location('gen6', D / 'generate_conflict_pack_v6.py')
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


class Pack(unittest.TestCase):
    def test_frozen_bytes_and_regeneration(self):
        raw = (D / 'provenance_conflict_pack_v6.jsonl').read_text(encoding='utf-8')
        self.assertEqual(hashlib.sha256(raw.encode()).hexdigest(), PACK_SHA)
        self.assertEqual(gen.build(), raw)

    def test_composition(self):
        rows = [json.loads(line) for line in (D / 'provenance_conflict_pack_v6.jsonl').read_text(encoding='utf-8').splitlines()]
        heads = [r['messages'][2]['content'].split('.')[0] for r in rows]
        self.assertEqual(len(rows), 200)
        self.assertEqual(sum(h == 'The receipts conflict' for h in heads), 60)
        self.assertEqual(sum(h == 'The receipts disagree' for h in heads), 60)
        self.assertEqual(sum(h.startswith('Both receipts record') for h in heads), 60)

    def test_disjoint_from_heldout_sets(self):
        self.assertEqual(gen.check_disjoint(R), [])


if __name__ == '__main__':
    unittest.main()
