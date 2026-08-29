# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Ñan cuts — TileDigest, Chaski, Ayni, Shard, Bay, GreenLight."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from szl_khipu.ayni import run_ayni
from szl_khipu.bay import run_bay
from szl_khipu.chaski import drain, enqueue_all, run_chaski
from szl_khipu.greenlight import run_greenlight
from szl_khipu.shard import SHARD_K, SHARD_N, decode_rs, encode_rs, run_shard
from szl_khipu.tilegrid import digest_tiles, run_tile_grid, schedule_cover, tile_schedule


class TileDigestTests(unittest.TestCase):
    def test_clean_cover(self) -> None:
        tiles = tile_schedule(8, 4, 4)
        self.assertEqual(len(tiles), 4)
        self.assertTrue(schedule_cover(8, tiles))
        y = run_tile_grid(8, 4, 4, 4, 0)
        self.assertEqual(y["gridBreaks"], 0)
        self.assertEqual(y["ranDig"], y["claimDig"])

    def test_coarser_br_breaks(self) -> None:
        y = run_tile_grid(8, 4, 4, 4, 1)
        self.assertEqual(y["gridBreaks"], 1)
        self.assertNotEqual(y["ranDig"], y["claimDig"])

    def test_drop_last_cover_hole(self) -> None:
        y = run_tile_grid(8, 4, 4, 4, 2)
        self.assertEqual(y["cover"], 0)
        self.assertEqual(y["gridBreaks"], 1)

    def test_digest_includes_schedule(self) -> None:
        a = digest_tiles(8, 4, 4, 4, tile_schedule(8, 4, 4))
        b = digest_tiles(8, 4, 2, 2, tile_schedule(8, 2, 2))
        self.assertNotEqual(a, b)


class ChaskiTests(unittest.TestCase):
    def test_fifo_identity(self) -> None:
        msgs = [3, 1, 4, 1, 5]
        self.assertEqual(drain(enqueue_all(msgs)), msgs)

    def test_clean_holds(self) -> None:
        y = run_chaski(11)
        self.assertEqual(y["broken"], 0)
        self.assertEqual(y["fifoHold"], 1)

    def test_swap_fail_closes(self) -> None:
        y = run_chaski(11, reorder=1)
        self.assertEqual(y["broken"], 1)

    def test_drop_fail_closes(self) -> None:
        y = run_chaski(11, drop=1)
        self.assertEqual(y["broken"], 1)
        self.assertEqual(y["dropped"], 1)


class AyniTests(unittest.TestCase):
    def test_identity_skip(self) -> None:
        y = run_ayni(7, leak=0)
        self.assertLess(y["leak"], 1e-12)

    def test_scaled_skip_leaks(self) -> None:
        y = run_ayni(7, leak=1)
        self.assertGreater(y["leak"], 1e-3)


class ShardTests(unittest.TestCase):
    def test_full_recovers(self) -> None:
        y = run_shard(11)
        self.assertEqual(y["recovered"], 1)
        self.assertEqual(y["live"], SHARD_N)

    def test_any_six_recover(self) -> None:
        mask = (1 << SHARD_K) - 1
        y = run_shard(11, mask=mask)
        self.assertEqual(y["live"], 6)
        self.assertEqual(y["recovered"], 1)

    def test_five_cannot(self) -> None:
        mask = (1 << (SHARD_K - 1)) - 1
        y = run_shard(11, mask=mask)
        self.assertEqual(y["live"], 5)
        self.assertEqual(y["recovered"], 0)
        self.assertIsNone(decode_rs([None] * SHARD_N))
        code = encode_rs([1, 2, 3, 4, 5, 6])
        self.assertEqual(len(code), SHARD_N)


class BayTests(unittest.TestCase):
    def test_default_four_rails(self) -> None:
        y = run_bay()
        self.assertEqual(y["blocked"], 0)
        self.assertEqual(y["collapsed"], 0)

    def test_record_on_product(self) -> None:
        y = run_bay(proof_into_product=1)
        self.assertEqual(y["blocked"], 1)

    def test_hub_as_proof(self) -> None:
        y = run_bay(hub_as_proof=1)
        self.assertEqual(y["blocked"], 1)

    def test_space_as_receipt(self) -> None:
        y = run_bay(space_as_receipt=1)
        self.assertEqual(y["blocked"], 1)


class GreenLightTests(unittest.TestCase):
    def test_honest_path(self) -> None:
        y = run_greenlight()
        self.assertEqual(y["greenlit"], 1)
        self.assertEqual(y["painted"], 0)
        self.assertFalse(y["provenTrust"] if isinstance(y["provenTrust"], bool) else y["provenTrust"])

    def test_paint_sorry(self) -> None:
        y = run_greenlight(paint_sorry=1)
        self.assertEqual(y["blocked"], 1)

    def test_claim_proven(self) -> None:
        y = run_greenlight(claim_proven=1)
        self.assertEqual(y["blocked"], 1)

    def test_fabricated_joule(self) -> None:
        y = run_greenlight(stamp_joule=1)
        self.assertEqual(y["blocked"], 1)
        self.assertEqual(y["energy"], "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
