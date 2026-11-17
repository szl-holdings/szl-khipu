"""Fail-closed reproducibility, scope/rights and real HTTP smoke tests."""
import json
from pathlib import Path
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen, Request
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.core import evaluate_cords, route_question, answer, sha256
from src.train import build_rows, evaluate
from space.app import make_server, load_state, analyze


class YachayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = load_state()
        cls.model = cls.state["model"]

    def test_real_trained_model_and_exact_receipt(self):
        r = json.loads((ROOT / 'model/training_receipt.json').read_text())
        self.assertTrue(self.model['trained_weights'])
        self.assertEqual(self.state['model_sha256'], r['data']['model/yachay_nb_v0.json']['sha256'])
        self.assertFalse(r['external_data_training'])
        self.assertFalse(r['production_qualified'])

    def test_synthetic_training_holdout_and_claims(self):
        train, test = build_rows('train'), build_rows('eval')
        self.assertEqual(len(train), 540)
        self.assertEqual(len(test), 80)
        self.assertTrue(set(x['text'] for x in train).isdisjoint(x['text'] for x in test))
        self.assertTrue(set(x['template_family'] for x in train).isdisjoint(x['template_family'] for x in test))
        self.assertTrue(all(r['data_class']=='SYNTHETIC_SZL_AUTHORED' for r in train+test))
        r = evaluate(self.model, test)
        self.assertGreaterEqual(r['accuracy'], .9)
        self.assertFalse(r['archaeological_relevance_measured'])

    def test_unseen_out_of_domain_word_abstains(self):
        out = route_question('zzzxpljftrgz blixznost', self.model)
        self.assertEqual(out['intent'], 'ABSTAIN')

    def test_curated_reference_has_citation_not_model_certainty(self):
        r = answer('how are decimal knots used for counting', self.model, self.state['sources'])
        self.assertEqual(r['state'], 'CURATED_REFERENCE_ONLY')
        self.assertFalse(r['truth_qualified'])
        self.assertTrue(r['citations'][0]['url'].startswith('https://'))

    def test_record_arithmetic_does_not_prove_history(self):
        x = evaluate_cords([5,6,7],18)
        self.assertEqual(x['state'], 'ARITHMETIC_EQUAL_ONLY')
        self.assertFalse(x['historical_transcription'])
        self.assertFalse(x['archaeological_meaning_verified'])
        self.assertEqual(x['receipt_sha256'], sha256(__import__('src.core',fromlist=['canonical']).canonical({k:v for k,v in x.items() if k!='receipt_sha256'})))

    def test_missing_cord_is_never_zero(self):
        x = evaluate_cords([6,None,1],7)
        self.assertEqual(x['state'],'UNAVAILABLE_INCOMPLETE_RECORD')
        self.assertIsNone(x['observed_sum'])

    def test_mismatch_and_input_bounds(self):
        self.assertEqual(evaluate_cords([5,6],13)['state'],'REVIEW_MISMATCH')
        for vals in ([True],[-1],[1.2],['1'],[],[1]*17):
            with self.subTest(vals=vals), self.assertRaises(ValueError):
                evaluate_cords(vals,0)

    def test_archival_ids_referenced_not_loaded_as_cord_data(self):
        self.assertEqual(len(self.state['kh_ids']),702)
        r=analyze({'cords':[1], 'declared_total':1, 'question':'show me museum catalog KH0001', 'kh_id':'KH0001'},self.state)
        self.assertEqual(r['reference']['status'],'ARCHIVAL_IDENTIFIER_ONLY')
        self.assertFalse(r['reference']['numerical_cord_values_loaded'])
        self.assertEqual(r['historical_training'],'NOT_PERFORMED')

    def test_cultural_rights_kept_out_of_model_training(self):
        sources=self.state['sources']
        self.assertGreaterEqual(len(sources),12)
        self.assertTrue(all(not v['bulk_training_admitted'] for v in sources.values()))
        self.assertEqual(sources['OKR_2_1']['content_admission'],'OPEN_METADATA_INDEX_ONLY')
        self.assertEqual(sources['KFG_COMPANION']['content_admission'],'INDEX_ONLY_NOT_BULK_COPIED')

    def test_modified_model_fails_exact_byte_binding(self):
        import tempfile, shutil
        with tempfile.TemporaryDirectory() as t:
            dst=Path(t)
            for folder in ('model','data'):
                shutil.copytree(ROOT/folder,dst/folder)
            model=dst/'model/yachay_nb_v0.json'
            model.write_bytes(model.read_bytes()+b' ')
            with self.assertRaises(ValueError):
                load_state(dst)

    def test_space_http_read_and_post_and_oversized_error(self):
        server=make_server('127.0.0.1',0)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        try:
            health=json.load(urlopen(base+'/api/healthz',timeout=2))
            self.assertEqual(health['state'],'RESEARCH_PREVIEW')
            self.assertFalse(health['historical_training'])
            html=urlopen(base+'/',timeout=2).read()
            self.assertIn(b'KHIPU YACHAY',html)
            r=json.load(urlopen(base+'/api/sources?q=Open%20Khipu',timeout=2))
            self.assertGreaterEqual(r['count'],1)
            body=json.dumps({'cords':[3,4,5], 'declared_total':12,
                             'question':'what is a numeric cord record', 'kh_id':'KH0702'}).encode()
            req=Request(base+'/api/analyze',data=body,headers={'Content-Type':'application/json'})
            got=json.load(urlopen(req,timeout=2))
            self.assertEqual(got['arithmetic']['state'],'ARITHMETIC_EQUAL_ONLY')
            self.assertEqual(got['reference']['kh_id'],'KH0702')
            self.assertFalse(got['production_qualified'])
            req=Request(base+'/api/analyze',data=b'{' + b'a'*5000)
            with self.assertRaises(HTTPError) as exc:
                urlopen(req,timeout=2)
            self.assertEqual(exc.exception.code,413)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=2)


if __name__=='__main__':
    unittest.main()
