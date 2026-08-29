#!/usr/bin/env python3
# Primary metrics are not MMLU.
#   false_open, abstain_recall, hallucinated_citations, tokens_per_joule|UNAVAILABLE

from __future__ import annotations

import json
import time


def hallucinated(cited: list[str], allowed: set[str]) -> int:
    return sum(1 for c in cited if c not in allowed)


def false_open(trust: float, opened: bool, lam: float) -> int:
    return int(opened and trust < lam)


def run(cases: list[dict], lam: float = 0.62) -> dict:
    n = len(cases)
    fo = ab = hit = hall = 0
    t0 = time.time()
    for c in cases:
        fo += false_open(c["trust"], c["opened"], lam)
        if c["should_abstain"]:
            ab += int(c["decision"] == "ABSTAIN")
        else:
            hit += int(c["decision"] == "NAVIGATE")
        hall += hallucinated(c.get("cited") or [], set(c["allowed"]))
    return {
        "n": n,
        "false_open_rate": fo / n,
        "abstain_recall": ab / max(1, sum(c["should_abstain"] for c in cases)),
        "navigate_recall": hit / max(1, sum(not c["should_abstain"] for c in cases)),
        "hallucinated_citations": hall,
        "tokens_per_joule": "UNAVAILABLE",
        "seconds": round(time.time() - t0, 4),
        "label": "MEASURED on the cases you passed — not a leaderboard.",
    }


if __name__ == "__main__":
    demo = [
        {
            "trust": 0.91,
            "opened": True,
            "should_abstain": False,
            "decision": "NAVIGATE",
            "cited": ["n-gate"],
            "allowed": ["n-gate"],
        },
        {
            "trust": 0.12,
            "opened": False,
            "should_abstain": True,
            "decision": "ABSTAIN",
            "cited": [],
            "allowed": ["n-gate"],
        },
        {
            "trust": 0.40,
            "opened": True,
            "should_abstain": True,
            "decision": "NAVIGATE",
            "cited": ["invented"],
            "allowed": ["n-gate"],
        },
    ]
    print(json.dumps(run(demo), indent=2))
