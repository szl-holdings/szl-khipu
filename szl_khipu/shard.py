# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""RS(10,6) evaluation code over GF(257). CHECKED ≠ Lean F18 PROVEN.

Recoverable iff ≥ 6 of 10 shards. Not RAID. Not a storage product.
"""

from __future__ import annotations

from typing import Any

import numpy as np

SHARD_N = 10
SHARD_K = 6
P = 257


def gf_add(a: int, b: int) -> int:
    return (a + b) % P


def gf_sub(a: int, b: int) -> int:
    return (a - b + P) % P


def gf_mul(a: int, b: int) -> int:
    return (a * b) % P


def gf_pow(a: int, exp: int) -> int:
    r, b, e = 1, ((a % P) + P) % P, exp
    while e > 0:
        if e & 1:
            r = (r * b) % P
        b = (b * b) % P
        e >>= 1
    return r


def gf_inv(a: int) -> int:
    x = ((a % P) + P) % P
    return 0 if x == 0 else gf_pow(x, P - 2)


def _eval_poly(coeff: list[int], x: int) -> int:
    y, p = 0, 1
    for c in coeff:
        y = gf_add(y, gf_mul(c, p))
        p = gf_mul(p, x)
    return y


def encode_rs(data: list[int]) -> list[int]:
    return [_eval_poly(data, i + 1) for i in range(SHARD_N)]


def _solve(a: list[list[int]], b: list[int]) -> list[int] | None:
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        piv = next((r for r in range(col, n) if m[r][col] != 0), -1)
        if piv < 0:
            return None
        if piv != col:
            m[col], m[piv] = m[piv], m[col]
        inv = gf_inv(m[col][col])
        if inv == 0:
            return None
        for j in range(col, n + 1):
            m[col][j] = gf_mul(m[col][j], inv)
        for r in range(n):
            if r == col or m[r][col] == 0:
                continue
            f = m[r][col]
            for j in range(col, n + 1):
                m[r][j] = gf_sub(m[r][j], gf_mul(f, m[col][j]))
    return [row[n] for row in m]


def decode_rs(points: list[tuple[int, int] | None]) -> list[int] | None:
    live = [p for p in points if p is not None]
    if len(live) < SHARD_K:
        return None
    take = live[:SHARD_K]
    a: list[list[int]] = []
    for x, _y in take:
        row, pw = [], 1
        for _ in range(SHARD_K):
            row.append(pw)
            pw = gf_mul(pw, x)
        a.append(row)
    return _solve(a, [y for _x, y in take])


def run_shard(seed: int, mask: int = (1 << SHARD_N) - 1) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    data = [int(rng.integers(0, 256)) for _ in range(SHARD_K)]
    code = encode_rs(data)
    present = [bool(mask & (1 << i)) for i in range(SHARD_N)]
    points: list[tuple[int, int] | None] = [
        (i + 1, y) if present[i] else None for i, y in enumerate(code)
    ]
    live = sum(1 for p in present if p)
    decoded = decode_rs(points)
    match = decoded is not None and decoded == data
    return {
        "data": data,
        "code": code,
        "present": present,
        "live": live,
        "recovered": 1 if match else 0,
        "decoded": decoded,
        "singleton": SHARD_N - SHARD_K + 1,
    }
