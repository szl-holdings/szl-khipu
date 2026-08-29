# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""szl-khipu CLI — train | demo-lambda | demo-yarqa | demo-anatomy | verify.

Never sets proven_trust true. Never fabricates joules. Never claims 1.5B
trained here. Λ uniqueness remains Conjecture 1 OPEN. Energy UNAVAILABLE.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from szl_khipu import YUYAY_FLOORS, evaluate_anatomy, evaluate_lambda, yarqa_attn
from szl_khipu.doctrine import proven_trust
from szl_khipu.train import tiny_khipu

WHAT_NOT = [
    "Not Qwen",
    "Not 1.5B trained here",
    "Not a FlashAttention rehost",
    "Lambda uniqueness remains Conjecture 1 OPEN",
    "No fabricated joules",
    "CUDA UNAVAILABLE",
    "proven_trust is false",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def cmd_train(args: argparse.Namespace) -> int:
    if proven_trust is True:
        raise SystemExit("refusing proven_trust true")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    weights, ev = tiny_khipu.train(seed=args.seed, steps=args.steps)
    npz_path = out_dir / "tiny_khipu.npz"
    tiny_khipu.save_npz(str(npz_path), weights)
    digest = hashlib.sha256(npz_path.read_bytes()).hexdigest()
    receipt = {
        "subject": "tiny_khipu",
        "seed": args.seed,
        "steps": args.steps,
        "loss": None,
        "plan_valid": ev.get("plan_valid"),
        "abstain": ev.get("abstain"),
        "hallucinated": ev.get("hallucinated"),
        "weights": str(npz_path),
        "sha256": digest,
        "honesty": "REPORTED",
        "proven_trust": False,
        "energy_j": None,
        "energy_status": "UNAVAILABLE",
        "conjecture_1": "OPEN",
        "whatNot": WHAT_NOT,
    }
    receipt_path = out_dir / "training_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"npz": str(npz_path), "receipt": str(receipt_path), "sha256": digest, **ev}))
    return 0


def cmd_demo_lambda(args: argparse.Namespace) -> int:
    axes = [float(x) for x in args.axes.split(",")] if args.axes else list(YUYAY_FLOORS)
    if args.zero is not None:
        if not 0 <= args.zero < len(axes):
            raise SystemExit(f"zero-route index {args.zero} out of range 0..{len(axes) - 1}")
        axes[args.zero] = 0.0
    ev = evaluate_lambda(axes)
    payload = {
        "value": ev["value"],
        "blocked": bool(ev["blocked"]),
        "reason": ev["reason"],
        "proven_trust": False,
        "conjecture_1": "OPEN",
        "energy_status": "UNAVAILABLE",
        "axes": axes,
    }
    print(json.dumps(payload, indent=2))
    return 0


def cmd_demo_yarqa(args: argparse.Namespace) -> int:
    rng = np.random.default_rng(args.seed)
    q = rng.standard_normal((args.seq, args.dim))
    k = rng.standard_normal((args.seq, args.dim))
    v = rng.standard_normal((args.seq, args.dim))
    _out, _probs, leaked = yarqa_attn(q, k, v, args.n_canals)
    payload = {
        "n_canals": args.n_canals,
        "seq": args.seq,
        "dim": args.dim,
        "leaked": float(leaked),
        "bound": 1e-9,
        "cuda": "UNAVAILABLE",
        "path": "cpu-numpy LIVE",
        "not": "SageAttention / FlashAttention rehost",
        "proven_trust": False,
        "energy_status": "UNAVAILABLE",
    }
    print(json.dumps(payload, indent=2))
    return 0


def cmd_demo_anatomy(args: argparse.Namespace) -> int:
    ev = evaluate_anatomy(
        zero_heart=bool(args.zero_heart),
        leak_canal=bool(args.leak_canal),
        tamper_chain=bool(args.tamper_chain),
        fabricate_joule=bool(args.fabricate_joule),
        break_skeleton=bool(args.break_skeleton),
        willay_fire=bool(args.willay_fire),
        seed=int(args.seed),
    )
    payload = {
        "live_count": ev["live_count"],
        "blocked": bool(ev["blocked"]),
        "reason": ev["reason"],
        "organs": [
            {"id": o["id"], "status": o["status"], "honesty": o["honesty"]} for o in ev["organs"]
        ],
        "willay": ev["willay"]["category"],
        "proven_trust": False,
        "conjecture_1": "OPEN",
        "energy_status": "UNAVAILABLE",
        "energy_j": None,
        "locked_proven": 8,
        "not": "Three.js rehost / 1.5B / fabricated joule",
    }
    print(json.dumps(payload, indent=2))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    path = Path(args.receipt)
    if not path.exists():
        print(json.dumps({"ok": False, "reason": f"missing {path}"}), file=sys.stderr)
        return 1
    data: dict[str, Any] = json.loads(path.read_text())
    if data.get("proven_trust") is True:
        print(json.dumps({"ok": False, "reason": "proven_trust true is forbidden"}), file=sys.stderr)
        return 1
    if data.get("energy_j") not in (None,):
        print(json.dumps({"ok": False, "reason": "fabricated joule"}), file=sys.stderr)
        return 1
    weights = data.get("weights")
    digest = data.get("sha256")
    if weights and digest:
        blob = Path(str(weights))
        if not blob.is_absolute():
            blob = path.parent / blob
        if blob.exists():
            actual = hashlib.sha256(blob.read_bytes()).hexdigest()
            if actual != digest:
                print(json.dumps({"ok": False, "reason": "sha256 mismatch", "actual": actual}), file=sys.stderr)
                return 1
    artifacts = data.get("artifacts") or {}
    for name, meta in artifacts.items():
        sha = (meta or {}).get("sha256") if isinstance(meta, dict) else None
        if not sha:
            continue
        blob = path.parent / name
        if blob.exists():
            actual = hashlib.sha256(blob.read_bytes()).hexdigest()
            if actual != sha:
                print(json.dumps({"ok": False, "reason": f"sha256 mismatch {name}", "actual": actual}), file=sys.stderr)
                return 1
    print(
        json.dumps(
            {
                "ok": True,
                "path": str(path),
                "honesty": data.get("honesty", "REPORTED"),
                "proven_trust": False,
                "energy_status": data.get("energy_status", "UNAVAILABLE"),
                "conjecture_1": "OPEN",
            }
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="szl-khipu",
        description="Knot the run. Hash the proof. Fail closed. Λ uniqueness OPEN. energy UNAVAILABLE.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("train", help="Train TinyKhipu silhouette; write npz + training_receipt.json")
    t.add_argument("--seed", type=int, default=20260721)
    t.add_argument("--steps", type=int, default=280)
    t.add_argument("--out", type=str, default=str(_repo_root() / "artifacts"))
    t.set_defaults(func=cmd_train)

    d = sub.add_parser("demo-lambda", help="Score 13 Yuyay axes through the advisory Λ gate")
    d.add_argument("--axes", type=str, default=None, help="comma-separated 13 floats in [0,1]")
    d.add_argument("--zero", type=int, default=None, help="zero-route this axis index (fail closed)")
    d.set_defaults(func=cmd_demo_lambda)

    y = sub.add_parser("demo-yarqa", help="Run canal attention; print leaked metric")
    y.add_argument("--n-canals", dest="n_canals", type=int, default=3)
    y.add_argument("--seq", type=int, default=12)
    y.add_argument("--dim", type=int, default=4)
    y.add_argument("--seed", type=int, default=7)
    y.set_defaults(func=cmd_demo_yarqa)

    a = sub.add_parser("demo-anatomy", help="Run the five-organ integrity kernel (fail closed)")
    a.add_argument("--seed", type=int, default=11)
    a.add_argument("--zero-heart", action="store_true")
    a.add_argument("--leak-canal", action="store_true")
    a.add_argument("--tamper-chain", action="store_true")
    a.add_argument("--fabricate-joule", action="store_true")
    a.add_argument("--break-skeleton", action="store_true")
    a.add_argument("--willay-fire", action="store_true")
    a.set_defaults(func=cmd_demo_anatomy)

    v = sub.add_parser("verify", help="Replay a training receipt (hash + honesty)")
    v.add_argument("receipt", nargs="?", default=str(_repo_root() / "artifacts" / "training_receipt.json"))
    v.set_defaults(func=cmd_verify)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
