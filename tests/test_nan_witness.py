# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Ñan silhouette witnesses. Honest holds. Tamper fail-closes. No joules."""

from __future__ import annotations

import unittest

from szl_khipu.huklla import run_huklla
from szl_khipu.kancha import run_kancha
from szl_khipu.nina import run_nina
from szl_khipu.rimay import run_rimay
from szl_khipu.sami import run_sami
from szl_khipu.suyay import run_suyay
from szl_khipu.wasi import run_wasi
from szl_khipu.yawar import run_yawar


class NanWitnessTests(unittest.TestCase):
    def test_honest_holds_and_tamper_breaks(self) -> None:
        runners = (
            run_yawar,
            run_wasi,
            run_sami,
            run_kancha,
            run_rimay,
            run_nina,
            run_suyay,
            run_huklla,
        )
        for fn in runners:
            hon = fn(11, mode=0)
            brk = fn(11, mode=1)
            self.assertEqual(hon["hold"], 1, fn.__name__)
            self.assertEqual(brk["broken"], 1, fn.__name__)
            self.assertIsNone(hon.get("joule"))


if __name__ == "__main__":
    unittest.main()
