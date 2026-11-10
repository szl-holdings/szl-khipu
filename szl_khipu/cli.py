# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""szl-khipu CLI — train | demo-lambda | demo-yarqa | demo-anatomy | serve | verify.

Never sets proven_trust true. Never fabricates joules. Never claims 1.5B
trained here. Λ uniqueness remains Conjecture 1 OPEN. Energy UNAVAILABLE.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from szl_khipu import YUYAY_FLOORS, evaluate_anatomy, evaluate_lambda, run_tile_grid, yarqa_attn
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


# Working-directory relative and outside artifacts/: that directory holds the
# committed, Hub-published historical silhouettes, which a retrain must never
# overwrite (current source does not reproduce their bytes).
DEFAULT_RUN_DIR = Path("runs") / "tinykhipu"
SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


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
        # Relative to this receipt's directory, so `verify` finds the weights
        # wherever the run directory is moved or whatever the caller's cwd is.
        "weights": npz_path.name,
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


def cmd_demo_tiledigest(args: argparse.Namespace) -> int:
    y = run_tile_grid(8, 4, args.br, args.br, args.tamper)
    payload = {
        "Br": args.br,
        "tamper": args.tamper,
        "gridBreaks": y["gridBreaks"],
        "cover": y["cover"],
        "ranDig": y["ranDig"],
        "claimDig": y["claimDig"],
        "tileCount": y["tileCount"],
        "not": "FlashAttention rehost",
        "proven_trust": False,
        "energy_status": "UNAVAILABLE",
    }
    print(json.dumps(payload, indent=2))
    return 0 if y["gridBreaks"] == 0 or args.tamper != 0 else 1


def _refuse(reason: str, **extra: Any) -> int:
    print(json.dumps({"ok": False, "reason": reason, **extra}), file=sys.stderr)
    return 1


def _weights_candidates(receipt: Path, declared: str) -> list[Path]:
    """Where a declared weights file may live, without consulting the caller's cwd.

    Relative paths resolve against the receipt's directory. Receipts written by
    earlier versions of ``train`` recorded a cwd-relative path (for example
    ``artifacts/tiny_khipu.npz``) for a file that ``train`` always writes next
    to the receipt, so the file name in the receipt's directory is the second
    candidate. Any candidate is accepted only when its bytes match the digest.
    """
    blob = Path(declared)
    if blob.is_absolute():
        return [blob]
    candidates = [receipt.parent / blob]
    if blob.name and receipt.parent / blob.name not in candidates:
        candidates.append(receipt.parent / blob.name)
    return candidates


def cmd_verify(args: argparse.Namespace) -> int:
    """Fail closed: every declared digest must be recomputed over bytes that exist."""
    path = Path(args.receipt)
    if not path.is_file():
        return _refuse(f"missing {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return _refuse(f"unreadable receipt {path}: {exc}")
    if not isinstance(data, dict):
        return _refuse("receipt is not a JSON object")
    if data.get("proven_trust") is True:
        return _refuse("proven_trust true is forbidden")
    if data.get("energy_j") is not None:
        return _refuse("fabricated joule")

    checks: list[tuple[str, list[Path], Any]] = []
    weights = data.get("weights")
    digest = data.get("sha256")
    if weights is not None or digest is not None:
        if not isinstance(weights, str) or not weights:
            return _refuse("receipt declares a sha256 without a weights path")
        checks.append((weights, _weights_candidates(path, weights), digest))
    artifacts = data.get("artifacts")
    if artifacts is not None:
        if not isinstance(artifacts, dict):
            return _refuse("receipt artifacts must be an object")
        for name, meta in artifacts.items():
            sha = meta.get("sha256") if isinstance(meta, dict) else None
            if sha is None:
                continue  # descriptive entries without a digest are not claims to verify
            if Path(name).is_absolute() or ".." in Path(name).parts:
                return _refuse(f"artifact name escapes the receipt directory: {name}")
            checks.append((name, [path.parent / name], sha))
    if not checks:
        # A receipt with nothing to hash is not evidence; never report it as verified.
        return _refuse("receipt declares no artifact digest to verify")

    verified = []
    for name, candidates, sha in checks:
        if not isinstance(sha, str) or not SHA256_HEX.fullmatch(sha):
            return _refuse(f"malformed sha256 for {name}")
        blob = next((c for c in candidates if c.is_file()), None)
        if blob is None:
            return _refuse(f"declared file is missing: {name}", looked_in=[str(c) for c in candidates])
        actual = hashlib.sha256(blob.read_bytes()).hexdigest()
        if actual != sha:
            return _refuse(f"sha256 mismatch {name}", path=str(blob), actual=actual, expected=sha)
        verified.append({"file": str(blob), "sha256": actual})
    print(
        json.dumps(
            {
                "ok": True,
                "path": str(path),
                "verified": verified,
                "honesty": data.get("honesty", "REPORTED"),
                "proven_trust": False,
                "energy_status": data.get("energy_status", "UNAVAILABLE"),
                "conjecture_1": "OPEN",
            }
        )
    )
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from szl_khipu.http_app import serve

    serve(host=args.host, port=int(args.port))
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
    t.add_argument(
        "--out",
        type=str,
        default=str(DEFAULT_RUN_DIR),
        help=f"run directory, relative to the working directory (default: {DEFAULT_RUN_DIR})",
    )
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

    g = sub.add_parser("demo-tiledigest", help="Receipt the Br×Bc schedule; fail-close on a lying grid")
    g.add_argument("--br", type=int, default=4)
    g.add_argument("--tamper", type=int, default=0, help="0 clean · 1 coarser Br · 2 drop last K-tile")
    g.set_defaults(func=cmd_demo_tiledigest)

    v = sub.add_parser(
        "verify",
        help="Replay a training receipt: recompute every declared sha256 (fail closed) and check honesty fields",
    )
    v.add_argument("receipt", nargs="?", default=str(DEFAULT_RUN_DIR / "training_receipt.json"))
    v.set_defaults(func=cmd_verify)

    s = sub.add_parser("serve", help="Python frontend + JSON kernel backend (stdlib HTTP)")
    s.add_argument("--host", default="0.0.0.0")
    s.add_argument("--port", type=int, default=7860)
    s.set_defaults(func=cmd_serve)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
