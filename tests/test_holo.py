"""EVALUATION_HOLD tests for KHIPU-HOLO v0.4. Not a production stamp."""
import unittest

from szl_khipu.holo import MATCH_THRESHOLD, decode_erasures, encode, run_holo, similarity, bind, unbind, random_phasor


class TestHolo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = run_holo()

    def test_rs_3_erasure(self):
        msg = [11, 22, 33, 44, 55]
        cw = encode(msg)
        rec = list(cw)
        rec[0] = rec[3] = rec[7] = None
        ok, rec_msg, rec_cw = decode_erasures(rec)
        self.assertTrue(ok)
        self.assertEqual(rec_msg, msg)
        self.assertEqual(rec_cw, cw)

    def test_fhrr_identity(self):
        a, b = random_phasor("a"), random_phasor("b")
        self.assertGreater(similarity(unbind(bind(a, b), b), a), 0.999)

    def test_hop1_match(self):
        self.assertEqual(self.r["hop1"], "MATCH")
        self.assertGreaterEqual(self.r["hop1_sim"], MATCH_THRESHOLD)

    def test_twin_hold(self):
        self.assertEqual(self.r["hop1_twin"], "HOLD")
        self.assertLess(self.r["hop1_twin_sim"], MATCH_THRESHOLD)

    def test_erasure_match(self):
        self.assertEqual(self.r["hop1_3erasure"], "MATCH")

    def test_atomic_measured(self):
        self.assertIn(self.r["hop2_atomic"], ("MATCH", "HOLD"))

    def test_compose_hold(self):
        self.assertEqual(self.r["hop2"], "HOLD")

    def test_sequential_hold(self):
        self.assertEqual(self.r["hop2_sequential"], "HOLD")

    def test_ladder(self):
        self.assertEqual(len(self.r["ladder"]), 5)
        self.assertEqual(self.r["ladder"][0]["extra"], 0)
        self.assertEqual(self.r["ladder"][4]["extra"], 64)

    def test_doctrine(self):
        self.assertFalse(self.r["ready"])
        self.assertEqual(self.r["energy"], "UNAVAILABLE")
        self.assertFalse(self.r["production_authorized"])
        self.assertEqual(self.r["kernel"], "khipu-holo/v0.4-eval")


if __name__ == "__main__":
    unittest.main()
