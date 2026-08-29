# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""PrefixWitness — radix-prefix KV digest. Original cut of SGLang RadixAttention.

A poisoned cache after digest fail-closes. Not SGLang. No tokens/s claim.
"""

from __future__ import annotations

from typing import Any

from .chaski import djb2

PREFIX_STEMS: tuple[str, ...] = ("NAV", "NAV ABSTAIN", "YUYAY", "YUYAY WILLAY ARI")


def longest_hit(query: str, nodes: list[dict[str, str]]) -> dict[str, str] | None:
    best: dict[str, str] | None = None
    for n in nodes:
        prefix = n["prefix"]
        if query == prefix or query.startswith(prefix + " "):
            if best is None or len(prefix) > len(best["prefix"]):
                best = n
    return best


def run_prefix(seed: int = 11, hijack: int = 0, query: str = "NAV") -> dict[str, Any]:
    nodes: list[dict[str, str]] = []
    for prefix in PREFIX_STEMS:
        kv = f"kv:{int(seed)}:{prefix}"
        nodes.append({"prefix": prefix, "kv": kv, "digest": djb2(kv)})
    claimed = "|".join(n["digest"] for n in nodes)
    if hijack == 1:
        poisoned = dict(nodes[0])
        poisoned["kv"] = f"{poisoned['kv']}#POISON"
        nodes[0] = poisoned
    now = "|".join(djb2(n["kv"]) for n in nodes)
    hit = longest_hit(query, nodes)
    hit_ok = hit is not None and djb2(hit["kv"]) == hit["digest"]
    hold = 1 if (now == claimed and hit_ok and hijack != 1) else 0
    return {
        "hold": hold,
        "broken": 0 if hold else 1,
        "hijack": 1 if hijack == 1 else 0,
        "hitOk": 1 if hit_ok else 0,
        "nodes": nodes,
        "query": query,
        "hit": hit["prefix"] if hit else "∅",
        "hitDigest": hit["digest"] if hit else "",
        "claimed": claimed,
        "now": now,
        "reason": (
            "PrefixWitness HOLDS · radix digest matches · not SGLang · no tokens/s claim"
            if hold
            else "PrefixWitness BROKEN · cached KV mutated after digest · fail closed · not a silent reuse"
        ),
        "what_not": "Not SGLang. Not RadixAttention. Original cut.",
    }
