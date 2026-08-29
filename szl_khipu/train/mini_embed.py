# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Tiny hash+table embed: V=64, d=12, L2-normalized rows. Not a foundation embed."""

from __future__ import annotations

import hashlib
from typing import Iterable

import numpy as np

V: int = 64
D: int = 12


def token_id(token: str, vocab: int = V) -> int:
    h = hashlib.sha256(token.encode("utf-8")).digest()
    return int.from_bytes(h[:8], "little") % int(vocab)


def l2_normalize(m: np.ndarray, axis: int = -1, eps: float = 1e-12) -> np.ndarray:
    n = np.linalg.norm(m, axis=axis, keepdims=True)
    return m / np.maximum(n, eps)


class MiniEmbed:
    def __init__(self, seed: int = 0, v: int = V, d: int = D) -> None:
        self.V = int(v)
        self.D = int(d)
        rng = np.random.default_rng(int(seed))
        table = rng.normal(0.0, 0.08, size=(self.V, self.D))
        self.table = l2_normalize(table, axis=1)

    def ids(self, tokens: Iterable[str]) -> np.ndarray:
        return np.array([token_id(t, self.V) for t in tokens], dtype=np.int64)

    def lookup(self, tokens: Iterable[str]) -> np.ndarray:
        idx = self.ids(tokens)
        if idx.size == 0:
            return np.zeros((0, self.D), dtype=np.float64)
        return self.table[idx]

    def embed(self, text: str) -> np.ndarray:
        toks = [t for t in text.split() if t]
        if not toks:
            v = self.table[0].copy()
        else:
            v = self.lookup(toks).mean(axis=0)
        return l2_normalize(v, axis=0)

    def save_npz(self, path: str) -> None:
        np.savez(path, table=self.table, V=np.array(self.V), D=np.array(self.D))

    @classmethod
    def load_npz(cls, path: str) -> "MiniEmbed":
        data = np.load(path)
        obj = cls.__new__(cls)
        obj.table = l2_normalize(np.asarray(data["table"], dtype=np.float64), axis=1)
        obj.V = int(np.asarray(data["V"]).reshape(-1)[0]) if "V" in data.files else obj.table.shape[0]
        obj.D = int(np.asarray(data["D"]).reshape(-1)[0]) if "D" in data.files else obj.table.shape[1]
        return obj


def build(seed: int = 0) -> MiniEmbed:
    return MiniEmbed(seed=seed)


def save_npz(path: str, embed: MiniEmbed | np.ndarray) -> None:
    if isinstance(embed, MiniEmbed):
        embed.save_npz(path)
        return
    table = l2_normalize(np.asarray(embed, dtype=np.float64), axis=1)
    np.savez(path, table=table, V=np.array(table.shape[0]), D=np.array(table.shape[1]))


def load_npz(path: str) -> MiniEmbed:
    return MiniEmbed.load_npz(path)
