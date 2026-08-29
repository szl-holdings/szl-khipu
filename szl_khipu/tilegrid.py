# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""TileDigest — receipt the Br×Bc schedule. Residual-vs-naive can hold while the grid lies.

Not a FlashAttention rehost. No tokens/s claim.
"""

from __future__ import annotations

import json
from typing import Any, TypedDict


class Tile(TypedDict):
    i0: int
    i1: int
    j0: int
    j1: int


def tile_schedule(n: int, br: int, bc: int) -> list[Tile]:
    br = max(1, int(br))
    bc = max(1, int(bc))
    tiles: list[Tile] = []
    i0 = 0
    while i0 < n:
        i1 = min(n, i0 + br)
        j0 = 0
        while j0 < n:
            tiles.append({"i0": i0, "i1": i1, "j0": j0, "j1": min(n, j0 + bc)})
            j0 += bc
        i0 += br
    return tiles


def schedule_cover(n: int, tiles: list[Tile]) -> bool:
    hit = [[0] * n for _ in range(n)]
    for t in tiles:
        for i in range(t["i0"], t["i1"]):
            for j in range(t["j0"], t["j1"]):
                hit[i][j] += 1
    return bool(tiles) and all(hit[i][j] == 1 for i in range(n) for j in range(n))


def _djb2(s: str) -> str:
    h = 5381
    for ch in s:
        h = ((h << 5) + h + ord(ch)) & 0xFFFFFFFF
    return f"{h:08x}"


def digest_tiles(n: int, d: int, br: int, bc: int, tiles: list[Tile]) -> str:
    return _djb2(json.dumps({"n": n, "d": d, "Br": br, "Bc": bc, "tiles": tiles}, separators=(",", ":")))


def run_tile_grid(n: int, d: int, br: int, bc: int, tamper: int = 0) -> dict[str, Any]:
    ran = tile_schedule(n, br, bc)
    ran_dig = digest_tiles(n, d, br, bc, ran)
    claimed_br, claimed_bc, claimed = br, bc, ran
    if tamper == 1:
        claimed_br = max(2, 4 if br == 2 else br - 2)
        claimed_bc = claimed_br
        claimed = tile_schedule(n, claimed_br, claimed_bc)
    elif tamper == 2:
        claimed = ran[:-1] if len(ran) > 1 else ran
    claim_dig = digest_tiles(n, d, claimed_br, claimed_bc, claimed)
    cover = 1 if schedule_cover(n, claimed) else 0
    grid_breaks = 0 if (ran_dig == claim_dig and cover == 1) else 1
    return {
        "n": n,
        "d": d,
        "Br": br,
        "Bc": bc,
        "claimedBr": claimed_br,
        "claimedBc": claimed_bc,
        "ran": ran,
        "claimed": claimed,
        "ranDig": ran_dig,
        "claimDig": claim_dig,
        "cover": cover,
        "gridBreaks": grid_breaks,
        "tileCount": len(claimed),
    }
