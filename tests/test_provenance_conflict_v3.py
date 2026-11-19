# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Grader and probe-set contract for research/provenance_conflict_v3 (stdlib only, no model)."""
import ast, hashlib, importlib.util, json, re, unittest
from pathlib import Path

R = Path(__file__).resolve().parents[1] / 'research'
D = R / 'provenance_conflict_v3'
FROZEN_SHA = '995c01cc73e1a0eaf69a3cd36b6d6ed6653e9c4c7f5b5ec1810ff56179c8583a'


def load(name):
    spec = importlib.util.spec_from_file_location(name, D / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


g = load('grade_conflict_v3')
DOC = json.loads((D / 'provenance_conflict_probes_v3.json').read_text(encoding='utf-8'))
P = {p['id']: p for p in DOC['probes']}


class ProbeSet(unittest.TestCase):
    def test_frozen_bytes_and_regeneration(self):
        raw = (D / 'provenance_conflict_probes_v3.json').read_text(encoding='utf-8')
        self.assertEqual(hashlib.sha256(raw.encode()).hexdigest(), FROZEN_SHA)
        self.assertEqual(load('generate_conflict_v3').build(), raw)

    def test_composition(self):
        self.assertEqual(DOC['counts'], {'contradiction': 24, 'consistent_pair': 12, 'answerable': 4})

    def test_disjoint_from_heldout_v2(self):
        v2 = json.loads((R / 'provenance_heldout_v2' / 'provenance_heldout_probes_v2.json').read_text(encoding='utf-8'))['probes']
        self.assertFalse({p['question'] for p in v2} & {p['question'] for p in P.values()})
        self.assertFalse({r['path'] for p in v2 for r in p['context']} & {r['path'] for p in P.values() for r in p['context']})


class Grader(unittest.TestCase):
    def test_contradiction(self):
        c = P['con2-00']; r0 = c['context'][0]
        self.assertTrue(g.grade(c, 'The two receipts conflict: north says 41, south says 7.')['correct'])
        self.assertTrue(g.grade(c, 'North reports 41 jobs and south reports 7.')['correct'])
        self.assertFalse(g.grade(c, f"There are 41 jobs queued, per {r0['path']} sha256 {r0['sha256']}.")['correct'])
        self.assertFalse(g.grade(c, 'There is no conflict; the queue holds 41 jobs.')['correct'])
        self.assertFalse(g.grade(c, 'Per the two receipts, the queue holds 41 jobs.')['correct'])
        self.assertFalse(g.grade(c, 'The receipts disagree; see receipts/queue-master.json')['correct'])

    def test_consistent_pair(self):
        a = P['agree-00']; r0, r1 = a['context']
        self.assertTrue(g.grade(a, f"Both receipts record 7 queued jobs ({r0['path']} sha256 {r0['sha256']}).")['correct'])
        self.assertTrue(g.grade(a, f"There is no conflict: both record 7 (sha256 {r1['sha256']}).")['correct'])
        self.assertFalse(g.grade(a, f"The receipts disagree about the queue: 7 (sha256 {r0['sha256']}).")['correct'])
        self.assertFalse(g.grade(a, 'The queue holds 7 jobs.')['correct'])

    def test_negative_controls(self):
        always = g.summarize(list(P.values()), {pid: 'The receipts disagree; I report a conflict.' for pid in P})
        self.assertEqual(always['per_kind']['contradiction']['correct'], 24)
        self.assertEqual(always['per_kind']['consistent_pair']['correct'], 0)
        refuse = g.summarize(list(P.values()), {pid: 'I abstain: no receipt grounds this claim.' for pid in P})
        self.assertEqual(refuse['correct_total'], 0)


class AmendmentA1(unittest.TestCase):
    """The harness pins the exact revisions held-out v2 evaluated (read without importing torch)."""

    def _assigned(self, name):
        tree = ast.parse((D / 'run_conflict_v3.py').read_text(encoding='utf-8'))
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == name for t in node.targets):
                return ast.literal_eval(node.value)
        raise self.failureException(f'{name} not assigned at module level')

    def test_pins_cover_default_models_and_match_readme(self):
        pinned = self._assigned('PINNED')
        self.assertEqual(self._assigned('PREREG_UTC'), '2026-11-19T08:00:00+00:00')
        src = (D / 'run_conflict_v3.py').read_text(encoding='utf-8')
        defaults = set(re.findall(r"SZLHOLDINGS/[\w.-]+", src.split('a = ap.parse_args()')[0]))
        self.assertEqual(set(pinned), defaults)
        readme = (D / 'README.md').read_text(encoding='utf-8')
        for model, rev in pinned.items():
            self.assertRegex(rev, r'^[0-9a-f]{40}$')
            self.assertIn(f'`{rev}`', readme, model)

    def test_gate_refuses_unpinned_models_and_loads_pins(self):
        src = (D / 'run_conflict_v3.py').read_text(encoding='utf-8')
        self.assertIn("ABORT_UNPINNED_MODEL", src)
        self.assertIn("revs = {m: PINNED[m] for m in models}", src)
        self.assertNotIn("revs = {m: i.sha", src)


if __name__ == '__main__':
    unittest.main()
