# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Paged KV cache: block table gather + BlockWitness on swap."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .chain import canon, sha256_hex


def block_kv_gather(pages: np.ndarray, table: np.ndarray | list[int]) -> np.ndarray:
    """Gather logical blocks from physical pages via the block table.

    pages: (P, ...) physical slots
    table: (L,) logical -> physical indices
    """
    pages = np.asarray(pages)
    idx = np.asarray(table, dtype=np.int64).ravel()
    if idx.size == 0:
        return pages[:0].copy()
    if np.any(idx < 0) or np.any(idx >= pages.shape[0]):
        raise ValueError("block table index out of range (fail-closed)")
    return pages[idx]


def _digest_arr(a: np.ndarray) -> str:
    rounded = np.round(np.asarray(a, dtype=np.float64), 8)
    return sha256_hex(canon(rounded.tolist()))


@dataclass
class BlockWitness:
    swapped: tuple[int, int]
    before_digest: str
    after_digest: str
    changed: bool
    table_before: list[int]
    table_after: list[int]


class PagedCache:
    """Logical sequence over physical pages, addressed by a block table."""

    def __init__(self, pages: np.ndarray, table: np.ndarray | list[int]) -> None:
        self.pages = np.asarray(pages).copy()
        self.table = np.asarray(table, dtype=np.int64).ravel().copy()

    def gather(self) -> np.ndarray:
        return block_kv_gather(self.pages, self.table)

    def swap(self, i: int, j: int) -> BlockWitness:
        """Swap two table entries. Witness records whether gather changed."""
        i, j = int(i), int(j)
        if not (0 <= i < self.table.size and 0 <= j < self.table.size):
            raise ValueError("swap indices out of range")
        before = self.gather()
        table_before = self.table.tolist()
        before_d = _digest_arr(before)
        self.table[i], self.table[j] = self.table[j], self.table[i]
        after = self.gather()
        table_after = self.table.tolist()
        after_d = _digest_arr(after)
        changed = not np.array_equal(before, after)
        return BlockWitness(
            swapped=(i, j),
            before_digest=before_d,
            after_digest=after_d,
            changed=changed,
            table_before=table_before,
            table_after=table_after,
        )


def make_cache(
    n_logical: int = 8,
    n_physical: int = 6,
    dim: int = 4,
    seed: int = 11,
) -> PagedCache:
    rng = np.random.default_rng(seed)
    pages = rng.normal(0.0, 0.4, size=(n_physical, dim))
    table = np.arange(n_logical, dtype=np.int64) % n_physical
    return PagedCache(pages, table)


def witness_swap(cache: PagedCache, i: int = 0, j: int = 1) -> dict[str, Any]:
    w = cache.swap(i, j)
    return {
        "swapped": w.swapped,
        "changed": w.changed,
        "before_digest": w.before_digest,
        "after_digest": w.after_digest,
    }
