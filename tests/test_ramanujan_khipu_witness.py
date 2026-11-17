"""Credential-free, offline negative controls for a finite, nonqualification lab."""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "frontier"))
import ramanujan_khipu_witness as rr


class TestRamanujanKhipuWitness(unittest.TestCase):
    def test_two_identities_through_128(self):
        report = rr.build_witness(128)
        self.assertEqual(report["status"], "FINITE_MATCH")
        self.assertTrue(rr.verify_witness(report))
        self.assertEqual(len(report["checks"]), 2)
        self.assertEqual([x["identity"] for x in report["checks"]], ["RR1", "RR2"])
        self.assertEqual(len(report["checks"][0]["coefficients"]), 129)
        self.assertEqual(len(report["checks"][1]["coefficients"]), 129)

    def test_small_known_counts(self):
        witness = rr.build_witness(6)
        first, second = witness["checks"]
        self.assertEqual(first["coefficients"][6]["gap_count"], 3)
        self.assertEqual(second["coefficients"][6]["residue_count"], 2)
        self.assertEqual(first["coefficients"][0]["gap_count"], 1)

    def test_different_recursions_are_not_the_same_implementation(self):
        self.assertEqual(rr.gap_counts(64, 1), rr.residue_counts(64, (1, 4)))
        self.assertEqual(rr.gap_counts(64, 2), rr.residue_counts(64, (2, 3)))

    def test_negative_control_wrong_residue_fails(self):
        self.assertNotEqual(rr.gap_counts(24, 1), rr.residue_counts(24, (1, 3)))

    def test_roundtrip_place_value(self):
        for number in [0, 1, 9, 10, 100, 1009, 123456789, 10**25]:
            self.assertEqual(rr.read_digital_cord(rr.digital_cord(number)), number)
        self.assertEqual(rr.digital_cord(0), {"present": True, "digits": []})

    def test_missing_is_not_zero(self):
        with self.assertRaisesRegex(rr.EvidenceHold, "MISSING_NOT_ZERO"):
            rr.read_digital_cord({"present": False, "digits": []})

    def test_reject_invalid_cords(self):
        invalid = [
            {"present": True, "digits": [[0, 0]]},
            {"present": True, "digits": [[0, 10]]},
            {"present": True, "digits": [[0, 1], [1, 1]]},
            {"present": True, "digits": [[0, 1], [0, 2]]},
            {"present": True, "digits": [[True, 1]]},
            {"present": True, "digits": [[0, True]]},
            {"present": True, "digits": [[-1, 4]]},
            {"present": True, "digits": "0"},
            {"present": True, "digits": [], "extra": 1},
        ]
        for cord in invalid:
            with self.subTest(cord=cord), self.assertRaises(rr.EvidenceHold):
                rr.read_digital_cord(cord)

    def test_bounds_fail_closed(self):
        for bound in [True, -1, 129, 1.5, None, "64"]:
            with self.subTest(bound=bound), self.assertRaises(rr.EvidenceHold):
                rr.build_witness(bound)

    def test_tampered_coefficient_fails(self):
        report = rr.build_witness(20)
        edited = copy.deepcopy(report)
        edited["checks"][0]["coefficients"][6]["gap_count"] += 1
        with self.assertRaisesRegex(rr.EvidenceHold, "WITNESS_NOT_REPRODUCIBLE"):
            rr.verify_witness(edited)

    def test_tampered_cord_fails_even_if_counts_match(self):
        edited = copy.deepcopy(rr.build_witness(12))
        edited["checks"][0]["coefficients"][6]["cord"]["digits"][0][1] = 9
        with self.assertRaisesRegex(rr.EvidenceHold, "WITNESS_NOT_REPRODUCIBLE"):
            rr.verify_witness(edited)

    def test_self_hash_is_not_a_signature(self):
        r = rr.build_witness(2)
        self.assertFalse(r["signature_verified"])
        self.assertFalse(r["proof_of_infinite_identity"])
        self.assertFalse(r["claims_historical_khipu_decipherment"])
        self.assertEqual(r["model_qualification"], "NOT_ASSESSED")
        tampered = copy.deepcopy(r)
        tampered["sha256"] = "0"*64
        with self.assertRaises(rr.EvidenceHold):
            rr.verify_witness(tampered)

    def test_cli_and_invalid_bound(self):
        script = ROOT / "frontier" / "ramanujan_khipu_witness.py"
        ok = subprocess.run([sys.executable, str(script), "--n", "8"],
                            capture_output=True, text=True, check=False)
        self.assertEqual(ok.returncode, 0)
        self.assertTrue(rr.verify_witness(json.loads(ok.stdout)))
        bad = subprocess.run([sys.executable, str(script), "--n", "129"],
                             capture_output=True, text=True, check=False)
        self.assertEqual(bad.returncode, 3)
        self.assertEqual(json.loads(bad.stdout)["status"], "HOLD")


if __name__ == "__main__":
    unittest.main()
