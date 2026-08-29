#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Train TinyKhipu, ReceiptAgent, moons; write artifacts + TRAINING_RECEIPT.json.

Honesty: REPORTED. proven_trust is false. energy_j is null / UNAVAILABLE.
Never claims 1.5B trained here. Never fabricates joules.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from szl_khipu.doctrine import proven_trust  # noqa: E402
from szl_khipu.train import mini_embed, moons, receipt_agent, tiny_khipu  # noqa: E402

WHAT_NOT = [
    "Not Qwen",
    "Not 1.5B trained here",
    "Not SZL-Khipu-1.5B",
    "Not SZL-Forge-1.5B-ReceiptAgent",
    "Not a FlashAttention rehost",
    "Not SageAttention",
    "Lambda uniqueness remains Conjecture 1 OPEN",
    "No fabricated joules",
    "CUDA UNAVAILABLE",
    "proven_trust is false",
    "TinyKhipu is a NAVIGATE/ABSTAIN silhouette",
    "ReceiptAgent-Nano is a 4-way gate silhouette; the kernel is truth",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if proven_trust is True:
        raise SystemExit("refusing proven_trust true")
    art = ROOT / "artifacts"
    art.mkdir(parents=True, exist_ok=True)

    seed = 20260721
    tiny_w, tiny_ev = tiny_khipu.train(seed=seed, steps=280)
    agent_w, agent_ev = receipt_agent.train(seed=seed, max_steps=400)
    moons_w, moons_ev = moons.train(seed=seed, steps=400)

    tiny_path = art / "tiny_khipu.npz"
    agent_path = art / "receipt_agent.npz"
    moons_path = art / "moons.npz"
    tiny_khipu.save_npz(str(tiny_path), tiny_w)
    receipt_agent.save_npz(str(agent_path), agent_w)
    moons.save_npz(str(moons_path), moons_w)

    embed = mini_embed.build(seed=seed)
    embed_path = art / "mini_embed.npz"
    mini_embed.save_npz(str(embed_path), embed)

    artifacts = {
        "tiny_khipu.npz": {
            "sha256": _sha256(tiny_path),
            "seed": seed,
            "steps": 280,
            "loss": None,
            "plan_valid": tiny_ev.get("plan_valid"),
            "abstain": tiny_ev.get("abstain"),
            "hallucinated": tiny_ev.get("hallucinated"),
            "what": "TinyKhipu-Nano NAVIGATE/ABSTAIN silhouette",
        },
        "receipt_agent.npz": {
            "sha256": _sha256(agent_path),
            "seed": seed,
            "steps": agent_ev.get("steps"),
            "loss": None,
            "agree": agent_ev.get("agree"),
            "what": "ReceiptAgent-Nano 4-way gate silhouette; kernel is truth",
        },
        "moons.npz": {
            "sha256": _sha256(moons_path),
            "seed": seed,
            "steps": 400,
            "loss": moons_ev.get("loss"),
            "acc": moons_ev.get("acc"),
            "what": "2→8→2 MLP on two moons. Not 1.5B.",
        },
        "mini_embed.npz": {
            "sha256": _sha256(embed_path),
            "seed": seed,
            "steps": 0,
            "loss": None,
            "what": "V=64 d=12 L2 table. Not a foundation embed.",
        },
    }

    receipt = {
        "id": "szl-khipu.training.v0.1.0",
        "ts": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "steps": {
            "tiny_khipu": 280,
            "receipt_agent": agent_ev.get("steps"),
            "moons": 400,
        },
        "loss": {
            "tiny_khipu": None,
            "receipt_agent": None,
            "moons": moons_ev.get("loss"),
        },
        "artifacts": artifacts,
        "honesty": "REPORTED",
        "proven_trust": False,
        "energy_j": None,
        "energy_status": "UNAVAILABLE",
        "conjecture_1": "OPEN",
        "doctrine": "v11 LOCKED",
        "locked": {"declarations": 749, "axioms": 14, "sorries": 163, "proven": 8},
        "cuda": "UNAVAILABLE",
        "cpu_numpy": "LIVE",
        "whatNot": WHAT_NOT,
    }
    if receipt["proven_trust"] is True:
        raise SystemExit("refusing to write proven_trust true")
    if receipt["energy_j"] is not None:
        raise SystemExit("refusing to fabricate joules")

    out = art / "TRAINING_RECEIPT.json"
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"receipt": str(out), "artifacts": {k: v["sha256"] for k, v in artifacts.items()}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
