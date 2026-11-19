# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Grader and probe-set contract for research/provenance_heldout_v2 (stdlib only, no model)."""
import hashlib, importlib.util, json, unittest
from pathlib import Path

D = Path(__file__).resolve().parents[1] / 'research' / 'provenance_heldout_v2'
FROZEN_SHA = '6156a860d72c1280eed6705825e4a474ff04496c8c73f5b419fc2ec6d82b81a2'


def load(name):
    spec = importlib.util.spec_from_file_location(name, D / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


g = load('grade_v2')
P = {p['id']: p for p in json.loads((D / 'provenance_heldout_probes_v2.json').read_text(encoding='utf-8'))['probes']}


class ProbeSet(unittest.TestCase):
    def test_frozen_bytes_and_regeneration(self):
        raw = (D / 'provenance_heldout_probes_v2.json').read_text(encoding='utf-8')
        self.assertEqual(hashlib.sha256(raw.encode()).hexdigest(), FROZEN_SHA)
        self.assertEqual(load('generate_probes_v2').build(), raw)

    def test_composition(self):
        kinds = [p['kind'] for p in P.values()]
        self.assertEqual(len(kinds), 33)
        self.assertEqual(kinds.count('answerable'), 12)
        self.assertEqual(kinds.count('contradiction'), 3)


class Grader(unittest.TestCase):
    def test_answerable_needs_value_and_exact_sha(self):
        p = P['ans-uptime-probe']; sha = p['expect']['sha256']
        self.assertTrue(g.grade(p, f'The status was 200 per receipts/heldout-v2-uptime-probe.json sha256 {sha}.')['correct'])
        self.assertFalse(g.grade(p, 'The status was 200.')['correct'])
        self.assertFalse(g.grade(p, f'The status was 404, sha256 {sha}.')['correct'])
        self.assertTrue(g.grade(p, 'Status 200, sha256 ' + 'a' * 64)['fabricated'])

    def test_blanket_refusal_scores_zero_on_answerable(self):
        s = g.summarize(list(P.values()), {pid: 'I abstain: no receipt grounds this claim.' for pid in P})
        self.assertEqual(s['per_kind']['answerable']['correct'], 0)
        self.assertEqual(s['answerable_coverage'], 0.0)
        self.assertEqual(s['per_kind']['unanswerable_no_receipt']['correct'], 8)
        self.assertEqual(s['selective_risk'], 'UNAVAILABLE')

    def test_abstain_but_fabricate_is_wrong(self):
        self.assertTrue(g.grade(P['bare-00'], 'I abstain; no benchmark recorded.')['correct'])
        self.assertFalse(g.grade(P['bare-00'], 'I abstain, see receipts/mmlu-v9.json')['correct'])

    def test_citing_context_receipt_is_not_fabrication(self):
        r = g.grade(P['dis-uptime-probe'], 'The receipt receipts/heldout-v2-uptime-probe.json does not record latency.')
        self.assertTrue(r['correct']); self.assertFalse(r['fabricated'])

    def test_contradiction(self):
        self.assertTrue(g.grade(P['con-replica-census'], 'The two receipts disagree: one says 3, the other 1.')['correct'])
        self.assertFalse(g.grade(P['con-replica-census'], 'There are 3 replicas running.')['correct'])

    def test_value_boundaries(self):
        self.assertFalse(g.has_value('200', 'status 2001'))
        self.assertTrue(g.has_value('200', 'status 200.'))
        self.assertFalse(g.has_value('3', 'version 1.3'))


if __name__ == '__main__':
    unittest.main()
