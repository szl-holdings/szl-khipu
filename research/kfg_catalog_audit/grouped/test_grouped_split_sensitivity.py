import unittest
from pathlib import Path
import grouped_split_sensitivity as g

class GroupTests(unittest.TestCase):
    def setUp(self): self.rows=[{'id':x,'okr_num':f'KH{x:04}'} for x in range(1,20)]
    def test_singletons_keep_original(self):
        self.assertEqual(g.grouped_assignments(self.rows,[]),{k['okr_num']:g.original(k) for k in self.rows})
    def test_group_order_invariant(self):
        a=[('KH0001','KH0003'),('KH0003','KH0002')]
        b=[('KH0002','KH0003'),('KH0003','KH0001')]
        self.assertEqual(g.grouped_assignments(self.rows,a),g.grouped_assignments(list(reversed(self.rows)),b))
    def test_transitive_component_same_split(self):
        r=g.grouped_assignments(self.rows,[('KH0001','KH0002'),('KH0002','KH0003')])
        self.assertEqual([r[f'KH{i:04}'] for i in (1,2,3)],[g.original(self.rows[0])]*3)
    def test_missing_pair_rejected(self):
        with self.assertRaises(ValueError): g.grouped_assignments(self.rows,[('KH0001','MISSING')])
    def test_duplicate_okr_identity_rejected(self):
        with self.assertRaises(ValueError):g.grouped_assignments(self.rows+self.rows[:1],[])
    def test_content_identity_ignores_only_split(self):
        self.assertEqual(g.content_id({'split':'train','a':1}),g.content_id({'split':'eval','a':1}))
        self.assertNotEqual(g.content_id({'a':1}),g.content_id({'a':2}))
    def test_real_replay(self):
        r=g.replay(Path(__file__).parent/'source')
        self.assertEqual(r['baseline']['train']['rows'],2857)
        self.assertEqual(r['baseline']['eval']['rows'],366)
        a=r['scenarios']['aliases_only']; b=r['scenarios']['aliases_plus_similarity_sensitivity']
        self.assertEqual(a['moved_khipus'],[])
        self.assertEqual({x['khipu'] for x in b['moved_khipus']},{'KH0303','KH0470'})
        self.assertEqual((b['train']['rows'],b['eval']['rows']),(2867,354))
        self.assertEqual((b['rows_eval_to_train'],b['removed_content_rows'],b['added_content_rows']),(8,4,2))
        self.assertTrue(all(not p['cross_split_after'] for p in b['pair_checks']))
        self.assertFalse(r['training_run']);self.assertFalse(r['heldout_qualification'])

if __name__=='__main__':unittest.main()
