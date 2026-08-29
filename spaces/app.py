# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""SZL KHIPU Gradio 4 space.

Banner states Conjecture 1 OPEN and energy UNAVAILABLE.
YAML emoji is Hub metadata only — not product chrome.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if not (ROOT / "szl_khipu").is_dir() and (ROOT.parent / "szl_khipu").is_dir():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

import gradio as gr  # noqa: E402
import numpy as np  # noqa: E402

from szl_khipu import (  # noqa: E402
    YUYAY_AXES,
    YUYAY_FLOORS,
    UnifiedReceiptChain,
    evaluate_lambda,
    yarqa_attn,
)
from szl_khipu.train import tiny_khipu  # noqa: E402

BANNER = (
    "**SZL KHIPU** — Knot the run. Hash the proof. Fail closed.\n\n"
    "Conjecture 1 OPEN · energy UNAVAILABLE · proven_trust=false · "
    "CPU numpy LIVE · CUDA UNAVAILABLE · not Qwen · not 1.5B · not a FlashAttention rehost"
)

CHAIN = UnifiedReceiptChain()


def _mint(kernel: str, op: str, payload: dict) -> int:
    CHAIN.emit(kernel, op, payload)
    _ok, depth, _brk = CHAIN.verify()
    return int(depth)


def score_lambda(*values: float) -> tuple[str, str, str, str]:
    axes = [float(v) for v in values]
    ev = evaluate_lambda(axes)
    depth = _mint("lambda", "score", {"value": float(ev["value"]), "blocked": bool(ev["blocked"])})
    status = "BLOCKED" if ev["blocked"] else "advisory pass"
    return (
        f"{float(ev['value']):.6f}",
        status,
        str(ev["reason"]),
        f"chain depth {depth} · proven_trust=false · Conjecture 1 OPEN",
    )


def run_yarqa(n_canals: float) -> tuple[str, str, str]:
    n = int(n_canals)
    rng = np.random.default_rng(7)
    seq, dim = 12, 4
    q = rng.standard_normal((seq, dim))
    k = rng.standard_normal((seq, dim))
    v = rng.standard_normal((seq, dim))
    _out, _probs, leaked = yarqa_attn(q, k, v, n)
    depth = _mint("yarqa", "attn", {"n_canals": n, "leaked": float(leaked)})
    return (
        f"{float(leaked):.3e}",
        f"n_canals={n} · bound leaked ≤ 1e-9 · CUDA UNAVAILABLE",
        f"chain depth {depth}",
    )


def train_tiny() -> tuple[str, str, str, str]:
    _w, ev = tiny_khipu.train(seed=20260721, steps=280)
    depth = _mint("tiny_khipu", "train", dict(ev))
    plan = float(ev["plan_valid"])
    abstain = float(ev["abstain"])
    hall = ev["hallucinated"]
    return (
        f"{plan * 100:.0f}%",
        f"{abstain * 100:.0f}%",
        str(int(hall) if float(hall) == int(hall) else hall),
        f"chain depth {depth} · silhouette, not 1.5B · honesty REPORTED",
    )


def chain_status() -> str:
    ok, depth, brk = CHAIN.verify()
    status = "ok" if ok else f"BREAK at {brk}"
    return (
        f"last chain depth {depth} · {status} · "
        f"energy UNAVAILABLE · proven_trust=false"
    )


AXES = list(YUYAY_AXES)
FLOORS = list(YUYAY_FLOORS)


with gr.Blocks(title="SZL KHIPU") as demo:
    gr.Markdown(BANNER)
    with gr.Tabs():
        with gr.Tab("Lambda"):
            gr.Markdown(
                "Λ = weighted geometric mean over 13 Yuyay axes. Any zero axis fail-closes to 0. "
                "Advisory always. Uniqueness is Conjecture 1 — OPEN."
            )
            sliders = [
                gr.Slider(0, 1, value=float(FLOORS[i]), step=0.01, label=AXES[i])
                for i in range(13)
            ]
            lam_score = gr.Textbox(label="score", interactive=False)
            lam_blocked = gr.Textbox(label="blocked", interactive=False)
            lam_reason = gr.Textbox(label="reason", interactive=False)
            lam_chain = gr.Textbox(label="receipt", interactive=False)
            lam_btn = gr.Button("Score Λ")
            lam_btn.click(score_lambda, inputs=sliders, outputs=[lam_score, lam_blocked, lam_reason, lam_chain])
            for s in sliders:
                s.release(score_lambda, inputs=sliders, outputs=[lam_score, lam_blocked, lam_reason, lam_chain])

        with gr.Tab("YARQA"):
            gr.Markdown(
                "Original canal / compartment attention. Not SageAttention. "
                "Attend only inside each canal. Cross-canal leak is a chain break. CUDA UNAVAILABLE."
            )
            n_canals = gr.Slider(2, 6, value=3, step=1, label="n_canals")
            leaked = gr.Textbox(label="leaked", interactive=False)
            yarqa_note = gr.Textbox(label="note", interactive=False)
            yarqa_chain = gr.Textbox(label="receipt", interactive=False)
            yarqa_btn = gr.Button("Run YARQA")
            yarqa_btn.click(run_yarqa, inputs=[n_canals], outputs=[leaked, yarqa_note, yarqa_chain])
            n_canals.release(run_yarqa, inputs=[n_canals], outputs=[leaked, yarqa_note, yarqa_chain])

        with gr.Tab("Train TinyKhipu"):
            gr.Markdown(
                "NAVIGATE or ABSTAIN silhouette. Cited IDs are hard-filtered to the offered set. "
                "A few thousand floats. Not Qwen. Not 1.5B. Abstain is the thing to beat."
            )
            plan_box = gr.Textbox(label="plan-valid", interactive=False)
            abs_box = gr.Textbox(label="abstain", interactive=False)
            hall_box = gr.Textbox(label="hallucinated", interactive=False)
            train_note = gr.Textbox(label="receipt", interactive=False)
            train_btn = gr.Button("Train TinyKhipu")
            train_btn.click(train_tiny, inputs=None, outputs=[plan_box, abs_box, hall_box, train_note])

        with gr.Tab("Receipts"):
            gr.Markdown("Hash-chained receipts. Depth is integrity, not authorship. Energy UNAVAILABLE.")
            depth_box = gr.Textbox(label="last chain depth", interactive=False)
            depth_btn = gr.Button("Read chain")
            depth_btn.click(chain_status, inputs=None, outputs=[depth_box])


if __name__ == "__main__":
    demo.launch()
