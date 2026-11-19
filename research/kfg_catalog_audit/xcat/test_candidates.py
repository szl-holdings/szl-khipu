import contextlib
import io
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import candidate_concordance as c


class Tests(unittest.TestCase):
    def test_unknown_is_not_zero(self):
        cord=['']*22;cord[6]="'B'"
        self.assertIsNone(c.sql_value(cord,[]))
        cord[6]="'K'"
        self.assertEqual(c.sql_value(cord,[]),0)
        self.assertIsNone(c.sql_value(cord,[1,None]))
        self.assertIsNone(c.sql_value(cord,[0]))
        self.assertEqual(c.sql_value(cord,[10,3]),13)

    def test_arithmetic_not_export_labels(self):
        self.assertTrue(c.arithmetic([3,1,2])['exact_relation'])
        self.assertFalse(c.arithmetic([3,1,1])['exact_relation'])
        self.assertFalse(c.arithmetic([3,0,3])['eligible'])
        self.assertEqual(c.arithmetic([3,None,3])['status'],'unknown')

    def test_structural_candidates_include_unknown_target_and_both_sides(self):
        k={'cords':[dict(parent=10,parent_kind='primary',ordinal=i) for i in range(5)]}
        st=SimpleNamespace(roles=['pendant','pendant','top','pendant','pendant'],ids=list(range(5)),groups=[[0,1],[3,4]],group_of={0:0,1:0,3:1,4:1})
        self.assertEqual(list(c.single_group_candidates(k,st)),[(2,0),(2,1)])
        st.groups=[[0],[1],[3,4]];st.group_of={0:0,1:1,3:2,4:2}
        self.assertEqual(list(c.single_group_candidates(k,st)),[(2,2)])

    def test_missing_and_changed_inputs_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):c.run(d)
            Path(d,'corpus.json.gz').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):c.run(d)

    def test_import_does_not_read_inputs(self):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            result=subprocess.run([__import__('sys').executable,'-B','-c',
                "import sys;sys.path.insert(0,"+repr(str(Path(__file__).resolve().parent))+");from unittest.mock import patch;from pathlib import Path;\nwith patch.object(Path,'read_bytes',side_effect=RuntimeError('unexpected input read')):\n import candidate_concordance;import summarize"],cwd=d,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout,'')
            self.assertEqual(list(Path(d).iterdir()),[])

    @unittest.skipUnless(os.environ.get('KHIPU_XCAT_INPUTS'),'requires local pinned inputs')
    def test_pinned_full_denominator_and_partition(self):
        r=c.run(os.environ['KHIPU_XCAT_INPUTS'])
        self.assertEqual((r['shared_objects'],r['total_candidates'],r['strict_shared_candidates'],r['strict_known_both'],r['strict_unknown']),(557,412,385,276,109))
        self.assertEqual(r['mapping_counts'],{'group_members_differ':12,'nonadjacent_clusters':15,'strict_shared_candidate':385})
        self.assertEqual(r['strict_exact_relation_matrix'],{'okr_False_kfg_False':230,'okr_True_kfg_True':46})
        self.assertEqual(sum(r['mapping_counts'].values()),r['total_candidates'])
        self.assertEqual(sum(x['candidate_count'] for x in r['per_artifact']),412)
        self.assertEqual(len({(x['object_id'],x['target_id'],tuple(x['summand_ids'])) for x in r['rows']}),412)
        self.assertEqual(r['native_known_target_candidates_verified'],390)
        self.assertEqual(r['strict_values_identical'],270)
        self.assertEqual(r['strict_eligibility_matrix'],{'okr_False_kfg_False':79,'okr_True_kfg_True':197})
        self.assertEqual(r['strict_eligible_both_exact_matrix'],{'okr_False_kfg_False':151,'okr_True_kfg_True':46})
        self.assertEqual(r['strict_status_pairs'],{'known_known':276,'unknown_unknown':109})
        self.assertEqual(r['native_all_corpus_R2_union_candidates'],1812)
        self.assertEqual(r['native_shared_R2_union_candidates'],1652)
        self.assertEqual(len(r['identity_exclusions']),1)


if __name__=='__main__':unittest.main()
