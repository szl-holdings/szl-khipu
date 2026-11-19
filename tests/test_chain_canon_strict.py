# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Receipt canonicalization binds types: emit refuses inputs that would collide."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from szl_khipu.chain import UnifiedReceiptChain, canon, canon_strict

GOLDEN = (
    '{"arr":[1.0,2.0],"b":true,"d":{"z":[1,2.5,false]},"f":0.5,"i":3,'
    '"l":[null,"y"],"n":null,"np":4,"s":"x"}'
)


class CanonStrictTests(unittest.TestCase):
    def test_emit_refuses_colliding_inputs(self) -> None:
        cases = [
            {"v": float("nan")},
            {"v": float("inf")},
            {"v": np.float64("-inf")},
            {1: "a"},
            {"x": object},
        ]
        for attrs in cases:
            with self.subTest(attrs=repr(attrs)):
                c = UnifiedReceiptChain()
                with self.assertRaises((ValueError, TypeError)):
                    c.emit("k", "o", attrs)
                self.assertEqual(len(c.receipts), 0)
                self.assertEqual(c.verify(), (True, 0, -1))

    def test_strict_accepts_string_lookalikes(self) -> None:
        self.assertEqual(canon_strict({"x": "nan"}), '{"x":"nan"}')
        self.assertEqual(canon_strict({"1": "a"}), '{"1":"a"}')

    def test_supported_types_byte_identical(self) -> None:
        obj = {
            "f": 0.5,
            "i": 3,
            "b": True,
            "n": None,
            "s": "x",
            "d": {"z": [1, 2.5, False]},
            "l": [None, "y"],
            "np": np.int64(4),
            "arr": np.array([1.0, 2.0]),
        }
        self.assertEqual(canon_strict(obj), GOLDEN)
        self.assertEqual(canon(obj), GOLDEN)

    def test_verify_reports_break_on_post_emit_nan(self) -> None:
        c = UnifiedReceiptChain()
        for i in range(3):
            c.emit("k", "o", {"v": float(i)})
        self.assertEqual(c.verify(), (True, 3, -1))
        c._receipts[1].payload["v"] = float("nan")
        self.assertEqual(c.verify(), (False, 3, 1))

    def test_lenient_canon_unchanged_for_kernel_digests(self) -> None:
        self.assertEqual(canon({"x": float("nan")}), '{"x":"nan"}')


if __name__ == "__main__":
    unittest.main()
