"""Credential-free post-hoc OKR spatial-null regression and denial tests."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import random
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "research/okr_corpus/spatial_null.py"
RECEIPT = ROOT / "research/okr_corpus/spatial_null_v1.json"

spec = importlib.util.spec_from_file_location("szl_posthoc_spatial_null_test", FILE)
assert spec is not None and spec.loader is not None
spatial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(spatial)


class SpatialNullTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = spatial.audit()

    def test_source_and_claim_scope(self):
        r = self.report
        self.assertEqual(r["schema"], spatial.SCHEMA)
        self.assertEqual(r["source_branch_snapshot"], spatial.SOURCE_HEAD)
        self.assertEqual(
            r["input_corpus_sha256"],
            "6ef204b641826b37c320509952ed4181e93865af20f1cdfefd7516a49cf8ad0d",
        )
        self.assertEqual(r["upstream_okr_revision"], "4039ca51f4de661d80d0160596309c983a62a9c7")
        self.assertEqual(r["status"], "POST_HOC_EXPLORATORY_CONTROL_ONLY")
        self.assertFalse(r["preregistered"])
        self.assertFalse(r["prospective_heldout"])
        self.assertFalse(r["independent_research_lab_replication"])
        self.assertFalse(r["historical_khipu_decipherment"])
        self.assertFalse(r["historical_intent_established"])
        self.assertFalse(r["HJO_mathematical_theorem_proved"])
        self.assertFalse(r["signature_verified"])
        self.assertEqual(r["production_qualification"], "NOT_ASSESSED")

    def test_posthoc_spatial_controls_match_measured_receipt(self):
        all_r = self.report["all_eligible"]
        named = self.report["specified_provenance_eligible"]
        self.assertEqual(self.report["khipus_all"], 619)
        self.assertEqual(self.report["provenance_blank_or_unknown_count"], 221)
        self.assertEqual(self.report["n_pendant_shiftable_records"], 35)
        self.assertEqual((all_r["eligible"], all_r["observed_r2"]), (35, 54))
        self.assertEqual((named["eligible"], named["observed_r2"]), (21, 29))
        self.assertEqual(
            (all_r["null_mean"], all_r["null_sd_sample"], all_r["null_max"]),
            (11.035, 3.5234, 27),
        )
        self.assertEqual(
            (named["null_mean"], named["null_sd_sample"], named["null_max"]),
            (6.127, 2.8144, 19),
        )
        self.assertEqual(all_r["monte_carlo_p_upper"], 0.000999)
        self.assertEqual(named["monte_carlo_p_upper"], 0.000999)
        self.assertEqual(all_r["simulation_trials"], 1000)
        self.assertEqual(named["simulation_trials"], 1000)

    def test_receipt_is_exact_unsigned_source_and_replays(self):
        report = self.report
        core = {key: value for key, value in report.items() if key != "sha256"}
        self.assertEqual(
            hashlib.sha256(spatial.DOMAIN + spatial.canonical(core)).hexdigest(),
            report["sha256"],
        )
        self.assertEqual(RECEIPT.read_bytes(), spatial.render(report))
        self.assertEqual(
            hashlib.sha256(RECEIPT.read_bytes()).hexdigest(),
            "b99bcd08c957702f28e4ba28c3bfa9622b68603ecaf47a826c44427ad6517ff9",
        )

    def test_unknown_breaks_runs_and_original_never_mutated(self):
        engine = spatial._engine()
        corpus = engine.load_corpus()
        example = next(
            k for k in corpus["khipus"]
            if engine._Structure(k).candidates()["R2"]
        )
        structure = engine._Structure(example)
        base = tuple(engine._value_vector(structure))
        runs = spatial.shift_runs(example, structure)
        before = json.dumps(example, sort_keys=True)
        after = spatial.shifted_values(base, runs, random.Random(1))
        self.assertEqual(before, json.dumps(example, sort_keys=True))
        seen = set()
        for group in runs:
            self.assertGreater(len(group), 1)
            self.assertTrue(all(structure.known[i] for i in group))
            self.assertTrue(all(i not in seen for i in group))
            seen.update(group)
            self.assertEqual(sorted(base[i] for i in group), sorted(after[i] for i in group))
        for index in range(len(base)):
            if index not in seen:
                self.assertEqual(base[index], after[index])
        self.assertEqual(len(base), len(after))

    def test_invalid_budget_and_seed_fail_closed(self):
        for kw in (
            {"trials": True}, {"trials": 1}, {"trials": 2001},
            {"trials": 2.0}, {"seed": -1}, {"seed": True},
            {"seed": 2**32}, {"seed": 1.3},
        ):
            with self.subTest(kwargs=kw), self.assertRaises(spatial.Hold):
                spatial.audit(**kw)
        with self.assertRaisesRegex(spatial.Hold, "SHIFT_RUN_INVALID"):
            spatial.shifted_values((1, 2), ((0, 0),), random.Random(0))
        with self.assertRaisesRegex(spatial.Hold, "KHIPU_PROVENANCE_INVALID"):
            spatial.is_named_provenance({"provenance": None})

    def test_cli_can_replay_and_corruption_holds(self):
        r = subprocess.run(
            [sys.executable, "-I", str(FILE), "--check", str(RECEIPT)],
            cwd=ROOT, capture_output=True, text=True, check=False, timeout=45,
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertEqual(json.loads(r.stdout)["status"], "REPLAY_MATCH")
        with self.subTest("tampered copy"), __import__("tempfile").TemporaryDirectory() as td:
            tampered = Path(td) / "spatial_null_v1.json"
            tampered.write_bytes(RECEIPT.read_bytes() + b"TAMPER")
            bad = subprocess.run(
                [sys.executable, "-I", str(FILE), "--check", str(tampered)],
                cwd=ROOT, capture_output=True, text=True, check=False, timeout=45,
            )
            self.assertEqual(bad.returncode, 3)
            self.assertEqual(json.loads(bad.stdout)["reason"], "RECEIPT_REPLAY_MISMATCH")


if __name__ == "__main__":
    unittest.main()
