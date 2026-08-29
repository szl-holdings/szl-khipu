import unittest

from szl_khipu.train import moons, receipt_agent, tiny_khipu


class TrainTests(unittest.TestCase):
    def test_tiny_khipu(self):
        w, ev = tiny_khipu.train(seed=20260721, steps=120)
        self.assertEqual(ev["hallucinated"], 0.0)
        self.assertGreaterEqual(ev["plan_valid"], 0.5)

    def test_receipt_agent(self):
        w, ev = receipt_agent.train(seed=7, max_steps=400)
        self.assertGreaterEqual(ev["agree"], 0.85)

    def test_moons(self):
        w, ev = moons.train(seed=11, steps=120)
        self.assertGreater(ev["acc"], 0.7)


if __name__ == "__main__":
    unittest.main()
