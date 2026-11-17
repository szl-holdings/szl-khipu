# SPDX-License-Identifier: Apache-2.0
"""Tests of a future external evaluation intake, not tests of model quality."""
from __future__ import annotations
import hashlib
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
e = importlib.import_module('experiments.heldout_intake_v1.evaluate')
candidate_data = importlib.import_module('experiments.open_set_r1.train_open_set').candidate_data


def canon(value):
    return (json.dumps(value,sort_keys=True,separators=(",",":"),
                       ensure_ascii=False,allow_nan=False)+"\n").encode("utf-8")


def sample(tmp, n=40):
    root=Path(tmp)
    cases=[]
    for i in range(n):
        known=i<n//2
        cases.append({
            "schema":e.CASE_SCHEMA,
            "id":"case_%03d"%i,
            "question":(
                "Summarize decimal place values with fresh numeric example %03d."%i
                if known else
                "Help describe the travel gear required for hill cycling item %03d."%i
            ),
            "expected":"NUMERACY" if known else "ABSTAIN",
            "source_group":"alpha" if i%2==0 else "beta",
            "rights_class":"CALLER_DECLARED_EVAL_ONLY"
        })
    bytes_=b"".join(canon(row) for row in cases)
    p=root/"cases.jsonl";p.write_bytes(bytes_)
    m={
      "schema":e.MANIFEST_SCHEMA,"case_count":n,
      "cases_sha256":hashlib.sha256(bytes_).hexdigest(),
      "model_sha256":e.MODEL_SHA,
      "data_class":"EVALUATOR_AUTHORED_SYNTHETIC",
      "evaluation_permission":"CALLER_DECLARED_NOT_INDEPENDENTLY_VERIFIED",
      "training_admitted":False,
      "evaluator_identity_verified":False,
      "group_definition":"SOURCE_FAMILY_DECLARED_NOT_ATTESTED"
    }
    mf=root/"manifest.json";mf.write_bytes(canon(m))
    return mf,p,m,cases


def rewrite_cases(mf,p,manifest,cases):
    data=b"".join(canon(x) for x in cases)
    p.write_bytes(data)
    manifest["cases_sha256"]=hashlib.sha256(data).hexdigest()
    mf.write_bytes(canon(manifest))


class ExternalIntakeTest(unittest.TestCase):
    def test_model_source_sha_pinned_and_not_qualified(self):
        self.assertEqual(
            hashlib.sha256(e.MODEL.read_bytes()).hexdigest(),e.MODEL_SHA
        )
        self.assertEqual(len(e.MODEL_SHA),64)

    def test_developer_fixture_is_descriptive_hold_only(self):
        with tempfile.TemporaryDirectory() as temp:
            mf,p,_,cases=sample(temp)
            result=e.evaluate(mf,p)
            self.assertEqual(result["cases"]["n"],40)
            self.assertEqual(result["supported"]["n"],20)
            self.assertEqual(result["out_of_domain"]["n"],20)
            self.assertEqual(set(result["source_group_counts"]),{"alpha","beta"})
            self.assertFalse(result["production_qualified"])
            self.assertFalse(result["independent_evaluation_proved"])
            self.assertFalse(result["archaeological_accuracy_measured"])
            self.assertFalse(result["model_trained_this_run"])
            self.assertEqual(result["admission"],"HOLD_FOR_EXTERNAL_REVIEW_AND_PROVENANCE")
            self.assertNotIn(cases[0]["question"],json.dumps(result))
            self.assertNotIn(cases[-1]["question"],json.dumps(result))
            self.assertEqual(
                result["supported"]["n"],sum(v["supported_n"] for v in result["source_group_counts"].values())
            )

    def test_append_only_receipt_and_no_input_echo(self):
        with tempfile.TemporaryDirectory() as temp:
            mf,p,_,cases=sample(temp)
            out=Path(temp)/"receipt.json"
            with redirect_stdout(StringIO()) as output:
                self.assertEqual(e.main(["--manifest",str(mf),"--cases",str(p),"--out",str(out)]),0)
            raw=out.read_bytes()
            self.assertTrue(raw.endswith(b"\n"))
            self.assertIn("HOLD_FOR_EXTERNAL_REVIEW",output.getvalue())
            self.assertNotIn(cases[0]["question"],output.getvalue())
            with redirect_stdout(StringIO()):
                self.assertEqual(e.main(["--manifest",str(mf),"--cases",str(p),"--out",str(out)]),3)
            self.assertEqual(out.read_bytes(),raw)

    def test_case_tamper_denied_even_if_valid_json(self):
        with tempfile.TemporaryDirectory() as temp:
            mf,p,_,_=sample(temp)
            p.write_bytes(p.read_bytes()+b"\n")
            with self.assertRaisesRegex(e.EvaluationHold,"CASE_SHA256_MISMATCH"):
                e.validate(mf,p)

    def test_duplicate_id_denied_after_repin(self):
        with tempfile.TemporaryDirectory() as temp:
            mf,p,m,rows=sample(temp)
            rows[1]["id"]=rows[0]["id"]
            rewrite_cases(mf,p,m,rows)
            with self.assertRaisesRegex(e.EvaluationHold,"DUPLICATE_OR_INVALID_CASE_ID"):
                e.validate(mf,p)

    def test_duplicate_json_keys_denied(self):
        with tempfile.TemporaryDirectory() as temp:
            mf,p,m,_=sample(temp)
            text=mf.read_text(encoding="utf-8")
            mf.write_text(text.replace('"schema":','"schema":"junk","schema":'),encoding="utf-8")
            with self.assertRaisesRegex(e.EvaluationHold,"DUPLICATE_JSON_KEY"):
                e.validate(mf,p)

    def test_rights_or_identity_cannot_be_promoted_by_input(self):
        with tempfile.TemporaryDirectory() as temp:
            mf,p,m,_=sample(temp)
            m["evaluator_identity_verified"]=True
            mf.write_bytes(canon(m))
            with self.assertRaisesRegex(e.EvaluationHold,"RIGHTS_OR_CUSTODY_NOT_VERIFIED"):
                e.validate(mf,p)
            m["evaluator_identity_verified"]=False
            m["training_admitted"]=True
            mf.write_bytes(canon(m))
            with self.assertRaisesRegex(e.EvaluationHold,"RIGHTS_OR_CUSTODY_NOT_VERIFIED"):
                e.validate(mf,p)

    def test_missing_ood_denominator_holds(self):
        with tempfile.TemporaryDirectory() as temp:
            mf,p,m,rows=sample(temp)
            for row in rows:row["expected"]="NUMERACY"
            rewrite_cases(mf,p,m,rows)
            with self.assertRaisesRegex(e.EvaluationHold,"INCOMPLETE_DENOMINATORS"):
                e.validate(mf,p)

    def test_case_literal_training_overlap_holds(self):
        with tempfile.TemporaryDirectory() as temp:
            mf,p,m,rows=sample(temp)
            train,_,_=candidate_data(ROOT)
            rows[0]["question"]=train[0]["text"]
            rewrite_cases(mf,p,m,rows)
            with self.assertRaisesRegex(e.EvaluationHold,"PREVIOUSLY_SEEN_QUESTION_OVERLAP"):
                e.validate(mf,p)

    def test_wrong_model_sha_blocks_before_evaluation(self):
        with tempfile.TemporaryDirectory() as temp:
            mf,p,_,_=sample(temp)
            fake=Path(temp)/"modified-model.json"
            fake.write_bytes(e.MODEL.read_bytes()+b" ")
            with patch.object(e,"MODEL",fake):
                with self.assertRaisesRegex(e.EvaluationHold,"TRAINED_WEIGHT_BYTES_CHANGED"):
                    e.evaluate(mf,p)

    def test_wrong_model_revision_in_manifest_holds(self):
        with tempfile.TemporaryDirectory() as temp:
            mf,p,m,_=sample(temp)
            m["model_sha256"]="0"*64
            mf.write_bytes(canon(m))
            with self.assertRaisesRegex(e.EvaluationHold,"MODEL_REVISION_MISMATCH"):
                e.validate(mf,p)

    def test_input_schema_and_type_are_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            mf,p,m,rows=sample(temp)
            m["case_count"]=True
            mf.write_bytes(canon(m))
            with self.assertRaisesRegex(e.EvaluationHold,"CASE_COUNT_BUDGET"):
                e.validate(mf,p)
            m["case_count"]=len(rows)
            rows[0]["expected"]=1
            rewrite_cases(mf,p,m,rows)
            with self.assertRaisesRegex(e.EvaluationHold,"EXPECTED_INTENT"):
                e.validate(mf,p)

    def test_wilson_interval_is_conditional_and_bounded(self):
        self.assertIsNone(e.wilson_95(0,0))
        for a,n in ((0,20),(5,20),(20,20)):
            lo,hi=e.wilson_95(a,n)
            self.assertLessEqual(0,lo)
            self.assertGreaterEqual(1,hi)
            self.assertLessEqual(lo,a/n+1e-12)
            self.assertGreaterEqual(hi,a/n-1e-12)


    def test_pinned_r1_artifact_git_bytes_are_not_crlf_transformed(self):
        expected={
            "candidate_model.json":"1f5dfaf9da2ff2a6228eed02df0cdf12aa9407bf1d5df51f654d53c92c60f47e",
            "training_receipt.json":"fb238936f4e32833777c11444c24e0af2f93e606e70869c80c7c65f277b663ac",
            "training_intent.json":"2d46fb1d298adc97b61b0cf38b341990c41f509ed078e12dd4c6f55afb262bd2",
            "postfreeze_diagnostics.json":"78021a3bf0798c7b7aeaa86cfc1a702216690bd57c63be2fc1091c6f9b80db4d",
            "ARTIFACT_BINDING.json":"5f954edc6b33ddba2f5f5b2b30c664fa7b5f3d691027b6f14aab3534eccafcda",
        }
        root=ROOT/"experiments/open_set_r1"
        self.assertIn("*.json -text",(root/".gitattributes").read_text(encoding="utf-8"))
        for name,digest in expected.items():
            raw=(root/name).read_bytes()
            with self.subTest(name=name):
                self.assertNotIn(b"\r\n",raw)
                self.assertEqual(hashlib.sha256(raw).hexdigest(),digest)


if __name__=="__main__":
    unittest.main()
