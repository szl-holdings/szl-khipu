"""Bounded stdlib-only regressions for the separate Open-Set R1 trained router.

No sklearn import, no model download, and no re-training under CI.
No history/archaeology conclusions or runtime promotion are authorized.
"""
from __future__ import annotations
import json
import hashlib
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from experiments.open_set_r1.train_open_set import (
    LABELS, OOD, candidate_data, metrics, predict, sha
)

ART=ROOT/"experiments/open_set_r1"
MODEL_BYTES_SHA="1f5dfaf9da2ff2a6228eed02df0cdf12aa9407bf1d5df51f654d53c92c60f47e"


class OpenSetResearchChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload=(ART/"candidate_model.json").read_bytes()
        cls.model=json.loads(cls.payload)
        cls.receipt=json.loads((ART/"training_receipt.json").read_bytes())
        cls.intent=json.loads((ART/"training_intent.json").read_bytes())
        cls.postfreeze=json.loads((ART/"postfreeze_diagnostics.json").read_bytes())

    def test_weight_digest_exact(self):
        self.assertEqual(hashlib.sha256(self.payload).hexdigest(),MODEL_BYTES_SHA)
        self.assertEqual(self.receipt["trained_model_sha256"],MODEL_BYTES_SHA)
        self.assertEqual(len(self.payload),self.receipt["trained_model_bytes"])
        self.assertLess(len(self.payload),2_000_000)

    def test_artifact_schema_and_authority(self):
        model=self.model
        self.assertEqual(model["schema"],"szl.khipu-yachay.open-set-router/v1")
        self.assertEqual(set(model["classes"]),set(LABELS)|{OOD})
        self.assertEqual(model["runtime"],"STDLIB_ONLY")
        self.assertFalse(model["historical_training"])
        self.assertFalse(model["production_qualified"])
        self.assertEqual(model["weight_identity"],"RESEARCH_CANDIDATE_NOT_QUALIFIED")
        self.assertEqual(len(model["features"]),self.receipt["feature_count"])
        self.assertEqual(len(model["weights"]),6)
        self.assertEqual(len(model["bias"]),6)
        self.assertEqual(len(model["idf"]),len(model["features"]))
        self.assertEqual(self.receipt["gpu_hours"],0)
        self.assertEqual(self.receipt["paid_jobs"],0)
        self.assertFalse(self.receipt["model_weights_published"])

    def test_sources_remain_first_party_and_separate(self):
        train,dev,binding=candidate_data(ROOT)
        self.assertEqual(len(train),720)
        self.assertEqual(len(dev),132)
        self.assertEqual(binding,self.receipt["fixed_source_training_inputs"])
        self.assertEqual(binding["archaeological_samples_used"],0)
        self.assertEqual(binding["pinned_source_sha256"],
                         hashlib.sha256((ROOT/"data/synthetic_train.jsonl").read_bytes()).hexdigest())
        self.assertEqual({r["text"] for r in train}&{r["text"] for r in dev},set())

    def test_no_original_eval_or_posthoc_as_training(self):
        self.assertEqual(set(self.intent["excluded"]),
                         {"synthetic_eval.jsonl","posthoc_ood_v0.jsonl",
                          "historical_cord_content"})
        self.assertEqual(self.receipt["status"],"TRAINED_RESEARCH_CANDIDATE")
        self.assertEqual(self.receipt["optimizer_iterations"],30)
        self.assertEqual(self.receipt["evaluation_from_developer_viewed_sets"] if
                         "evaluation_from_developer_viewed_sets" in self.receipt else
                         "NOT_USED_FOR_TRAINING_OR_SELECTION","NOT_USED_FOR_TRAINING_OR_SELECTION")

    def test_internal_dev_replays_exact_receipt_not_qualification(self):
        _,dev,_=candidate_data(ROOT)
        observed=metrics(self.model,dev)
        self.assertEqual(observed,self.receipt["internal_dev"])
        self.assertEqual(observed["in_n"],60)
        self.assertEqual(observed["ood_n"],72)
        self.assertEqual(observed["in_correct"],36)
        self.assertEqual(observed["ood_false_accept"],0)
        self.assertTrue(self.receipt["development_gate_pass"])
        self.assertFalse(self.receipt["production_qualified"])

    def test_stdlib_predict_is_bounded_and_abstains_unknown(self):
        self.assertEqual(predict("zzzxqyvmvw superduperunseenwordx",self.model)["intent"],
                         "ABSTAIN")
        for query in ("What is the significance of decimal knots?",
                      "Explain circuit breaker repair", "Cultural rights of a quipu record"):
            answer=predict(query,self.model)
            self.assertIn(answer["intent"],(*LABELS,"ABSTAIN"))
            if answer["prob"] is not None:
                self.assertGreaterEqual(answer["prob"],0)
                self.assertLessEqual(answer["prob"],1)
        for invalid in ("", "x"*501, True, None):
            with self.subTest(invalid=type(invalid).__name__),self.assertRaises(ValueError):
                predict(invalid,self.model)

    def test_postfreeze_diagnostics_do_not_claim_independence(self):
        f=self.postfreeze
        self.assertEqual(f["new_model_sha256"],MODEL_BYTES_SHA)
        self.assertTrue(f["developer_authored_or_previously_tuned"])
        self.assertFalse(f["model_weights_modified"])
        self.assertFalse(f["production_qualified"])
        self.assertEqual(f["postfreeze_diagnostics"]["owner_posthoc_52"]["candidate_in_correct"],21)
        self.assertEqual(f["postfreeze_diagnostics"]["owner_posthoc_52"]["candidate_ood_false_accept"],7)
        self.assertEqual(f["postfreeze_diagnostics"]["separate_developer_100"]["candidate_ood_false_accept"],13)

    def test_training_intent_predates_weights_and_has_no_historical_samples(self):
        self.assertEqual(self.intent["git_sha"],self.receipt["source_git_sha"])
        self.assertTrue(self.intent["no_paid_jobs"])
        self.assertEqual(self.intent["inputs"]["archaeological_samples_used"],0)
        self.assertEqual(self.intent["train_count"],720)
        self.assertTrue(self.intent["no_model_promotion"])


if __name__=="__main__":
    unittest.main()
