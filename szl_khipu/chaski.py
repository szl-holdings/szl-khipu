# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Hash-chained runner FIFO. F7 silhouette: drain(enqueueAll([], msgs)) = msgs.

A swap or drop is BLOCKED — not retried. Not a Kafka rehost.
"""

from __future__ import annotations

from typing import Any, TypedDict

GENESIS = "00000000"


class ChaskiMsg(TypedDict):
    seq: int
    body: int
    prev: str
    digest: str


def djb2(s: str) -> str:
    h = 5381
    for ch in s:
        h = ((h << 5) + h + ord(ch)) & 0xFFFFFFFF
    return f"{h:08x}"


def enqueue_all(bodies: list[int], genesis: str = GENESIS) -> list[ChaskiMsg]:
    out: list[ChaskiMsg] = []
    prev = genesis
    for i, body in enumerate(bodies):
        digest = djb2(f"{i}|{body}|{prev}")
        out.append({"seq": i, "body": int(body), "prev": prev, "digest": digest})
        prev = digest
    return out


def drain(queue: list[ChaskiMsg]) -> list[int]:
    return [m["body"] for m in queue]


def verify_chain(msgs: list[ChaskiMsg]) -> tuple[int, int]:
    chain_breaks = 0
    reorder = 0
    prev = GENESIS
    for i, m in enumerate(msgs):
        expect = djb2(f"{m['seq']}|{m['body']}|{m['prev']}")
        if m["digest"] != expect:
            chain_breaks += 1
        if m["prev"] != prev:
            chain_breaks += 1
        if m["seq"] != i:
            reorder += 1
        prev = m["digest"]
    return chain_breaks, reorder


def run_chaski(seed: int, reorder: int = 0, drop: int = 0, n: int = 8) -> dict[str, Any]:
    rng = __import__("numpy").random.default_rng(seed)
    n = max(3, min(12, int(n)))
    bodies = [int(rng.integers(0, 1000)) for _ in range(n)]
    q = enqueue_all(bodies)
    if reorder == 1 and len(q) >= 2:
        at = min(2, len(q) - 2)
        q[at], q[at + 1] = q[at + 1], q[at]
    if drop == 1 and q:
        q = q[:-1]
    chain_breaks, reorder_n = verify_chain(q)
    drained = drain(q)
    order_hold = (
        drop != 1 and len(drained) == len(bodies) and drained == bodies
    )
    fifo_hold = 1 if order_hold and chain_breaks == 0 and reorder_n == 0 else 0
    return {
        "n": len(q),
        "broken": 0 if fifo_hold else 1,
        "reorder": reorder_n,
        "chainBreaks": chain_breaks,
        "dropped": 1 if drop == 1 else 0,
        "fifoHold": fifo_hold,
        "queue": q,
        "bodies": bodies,
    }
