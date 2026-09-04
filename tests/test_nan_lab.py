# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import unittest

from szl_khipu.nan_lab import FAIL, RUNNERS, run_codex, run_estate, run_ouroboros, selftest


class NanLabTests(unittest.TestCase):
    def test_selftest(self) -> None:
        self.assertEqual(selftest(), 0)
        self.assertIn("ouroboros", RUNNERS)
        self.assertIn("codex", RUNNERS)
        self.assertIn("estate", RUNNERS)

    def test_ouroboros_fixture(self) -> None:
        y = run_ouroboros(11, 0)
        self.assertEqual(y["tax"]["modelMs"], 1120)
        self.assertEqual(y["tax"]["overheadMs"], 180)
        self.assertEqual(y["hold"], 1)
        self.assertEqual(run_ouroboros(11, **FAIL["ouroboros"])["broken"], 1)

    def test_codex_rejects_unsigned(self) -> None:
        self.assertEqual(run_codex(11, 0)["hold"], 1)
        self.assertEqual(run_codex(11, 1)["hold"], 0)

    def test_estate_rejects_szlholdings(self) -> None:
        self.assertEqual(run_estate(11, 0)["hold"], 1)
        self.assertEqual(run_estate(11, 1)["hold"], 0)
        self.assertEqual(run_estate(11, 1)["audit"]["github_org"], "SZLHoldings")


if __name__ == "__main__":
    unittest.main()
