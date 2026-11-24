# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Reference sketches for three transfers. MODELED; see README.md for prior art."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

GENESIS = "0" * 64


def _digest(value: object) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha3_256(body.encode("ascii")).hexdigest()


# --- 1. Delta layers with replay (prior art: terminusdb-store layers) -------


@dataclass(frozen=True)
class Layer:
    """An immutable set of additions and removals over a parent layer."""

    parent: str
    additions: tuple[str, ...]
    removals: tuple[str, ...]
    name: str = field(init=False)

    def __post_init__(self) -> None:
        if set(self.additions) & set(self.removals):
            raise ValueError("LAYER_ADDS_AND_REMOVES_SAME_ITEM")
        object.__setattr__(
            self,
            "name",
            _digest(
                {
                    "parent": self.parent,
                    "add": sorted(self.additions),
                    "del": sorted(self.removals),
                }
            ),
        )


def replay(layers: Sequence[Layer]) -> tuple[frozenset[str], str]:
    """Rebuild the state from the base up. Raises if the chain does not link."""

    state: set[str] = set()
    head = GENESIS
    for layer in layers:
        if layer.parent != head:
            raise ValueError("LAYER_CHAIN_BROKEN")
        missing = set(layer.removals) - state
        if missing:
            raise ValueError("LAYER_REMOVES_ABSENT_ITEM")
        state -= set(layer.removals)
        state |= set(layer.additions)
        head = layer.name
    return frozenset(state), head


# --- 2. Ancestor-checked head (prior art: terminusdb-store set_head) --------


class Branch:
    """A head pointer that only advances to a descendant, guarded by a version.

    There is deliberately no force path.
    """

    def __init__(self) -> None:
        self._parents: dict[str, str] = {}
        self.head = GENESIS
        self.version = 0

    def register(self, layer: Layer) -> None:
        if layer.parent != GENESIS and layer.parent not in self._parents:
            raise ValueError("LAYER_PARENT_UNKNOWN")
        self._parents[layer.name] = layer.parent

    def _descends_from(self, name: str, ancestor: str) -> bool:
        seen = 0
        while name != GENESIS and seen <= len(self._parents):
            if name == ancestor:
                return True
            name = self._parents.get(name, GENESIS)
            seen += 1
        return ancestor == GENESIS

    def set_head(self, name: str, expected_version: int) -> bool:
        if expected_version != self.version or name not in self._parents:
            return False
        if name == self.head or not self._descends_from(name, self.head):
            return False
        self.head = name
        self.version += 1
        return True


# --- 3. Bias-only dispatch (prior art: DeepSeek-V3 auxiliary-loss-free
#        load balancing, applied here to workers instead of experts) ---------


def dispatch(
    affinities: Sequence[Mapping[str, float]], gamma: float
) -> tuple[list[str], list[float], dict[str, int]]:
    """Assign each job to one worker.

    The bias changes which worker is selected and nothing else: the recorded
    score is always the unbiased affinity of the chosen worker. After each job
    an overloaded worker's bias falls by gamma and an underloaded one's rises.
    gamma = 0 is the no-bias baseline.
    """

    if not math.isfinite(gamma) or gamma < 0:
        raise ValueError("GAMMA_INVALID")
    workers = sorted({w for job in affinities for w in job})
    bias = dict.fromkeys(workers, 0.0)
    load = dict.fromkeys(workers, 0)
    chosen: list[str] = []
    scores: list[float] = []
    for step, job in enumerate(affinities, start=1):
        if not job or any(not math.isfinite(v) for v in job.values()):
            raise ValueError("AFFINITY_INVALID")
        pick = max(sorted(job), key=lambda w: job[w] + bias[w])
        chosen.append(pick)
        scores.append(job[pick])
        load[pick] += 1
        mean = step / len(workers)
        for w in workers:
            if load[w] > mean:
                bias[w] -= gamma
            elif load[w] < mean:
                bias[w] += gamma
    return chosen, scores, load


def load_variance(load: Mapping[str, int]) -> float:
    values = list(load.values())
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)
