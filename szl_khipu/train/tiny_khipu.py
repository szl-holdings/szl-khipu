# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""TinyKhipu silhouette: formula-token navigator. Hard ID filter. Not Qwen."""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

FORMULA_TOKS: tuple[str, ...] = (
    "F1",
    "F4",
    "F7",
    "F11",
    "F12",
    "F18",
    "F19",
    "F22",
    "LAMBDA",
    "YUYAY",
    "NAVIGATE",
    "ABSTAIN",
    "MEASURED",
    "REPORTED",
    "UNKNOWN",
    "BLOCKED",
)

V: int = len(FORMULA_TOKS) + 8
D: int = 12
NAVIGATE: int = 1
ABSTAIN: int = 0


def tok_id(s: str) -> int:
    up = s.upper()
    for i, tok in enumerate(FORMULA_TOKS):
        if tok in up:
            return i
    h = 0
    for ch in s:
        h = ((h * 31 + ord(ch)) & 0xFFFFFFFF)
        if h >= 0x80000000:
            h -= 0x100000000
    return len(FORMULA_TOKS) + (abs(h) % 8)


def _formula_in(text: str) -> str | None:
    up = text.upper()
    for tok in FORMULA_TOKS[:8]:
        if tok in up:
            return tok
    return None


def synth_curriculum(n: int = 80, seed: int = 20260721) -> list[dict[str, Any]]:
    """Navigate iff a formula token is in the query AND in a handle note."""
    rng = np.random.default_rng(int(seed))
    out: list[dict[str, Any]] = []
    locked = FORMULA_TOKS[:8]
    extra = FORMULA_TOKS[8:]
    for i in range(n):
        navigate = (i % 5) != 0
        tok = str(locked[int(rng.integers(0, len(locked)))])
        distractor = str(extra[int(rng.integers(0, len(extra)))])
        if navigate:
            query = f"resolve {tok} handle"
            notes = [
                f"{tok} node",
                f"{FORMULA_TOKS[int(rng.integers(0, 16))]} spare",
                "unrelated theorem",
            ]
            decision = NAVIGATE
            cite = [0]
        else:
            query = f"ask about {tok} with no handle"
            spare_pool = [t for t in FORMULA_TOKS if t != tok]
            spare = str(spare_pool[int(rng.integers(0, len(spare_pool)))])
            notes = [
                f"{distractor} other",
                f"{spare} spare",
                "unrelated theorem",
            ]
            decision = ABSTAIN
            cite = []
        handles = [{"id": f"h.{i}.{tag}", "note": note} for tag, note in zip("abc", notes)]
        # Label is the conjunction the user asked for.
        qtok = _formula_in(query)
        handle_hit = qtok is not None and any(qtok in h["note"].upper() for h in handles)
        decision = NAVIGATE if handle_hit else ABSTAIN
        cite = [0] if decision == NAVIGATE else []
        out.append(
            {
                "query": query,
                "handles": handles,
                "decision": decision,
                "cite": cite,
            }
        )
    return out


def init_weights(seed: int) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(int(seed))
    return {
        "E": rng.normal(0.0, 0.08, size=(V, D)),
        "W": rng.normal(0.0, 0.08, size=(2, D)),
        "b": np.zeros(2, dtype=np.float64),
        "Wc": rng.normal(0.0, 0.08, size=(D,)),
    }


def _embed_mean(w: dict[str, np.ndarray], text: str) -> np.ndarray:
    parts = [p for p in text.split() if p]
    acc = np.zeros(D, dtype=np.float64)
    n = max(len(parts), 1)
    for p in parts:
        acc += w["E"][tok_id(p)]
    return acc / n


def _softmax2(logits: np.ndarray) -> np.ndarray:
    m = float(np.max(logits))
    e = np.exp(logits - m)
    return e / e.sum()


def forward(w: dict[str, np.ndarray], ex: dict[str, Any]) -> dict[str, Any]:
    q = _embed_mean(w, ex["query"])
    logits = w["b"] + w["W"] @ q
    p = _softmax2(logits)
    handles: list[dict[str, str]] = list(ex["handles"])
    offered = {h["id"] for h in handles}
    cites = np.array(
        [float(np.dot(w["Wc"], _embed_mean(w, h["note"]))) for h in handles],
        dtype=np.float64,
    )
    decision = NAVIGATE if p[1] >= p[0] else ABSTAIN
    raw_cited: list[str] = []
    if decision == NAVIGATE and handles:
        raw_cited = [handles[int(np.argmax(cites))]["id"]]
    hallucinated = [cid for cid in raw_cited if cid not in offered]
    # Hard filter: cited IDs subset of offered.
    cited = [cid for cid in raw_cited if cid in offered]
    return {
        "p": p,
        "cites": cites,
        "decision": decision,
        "cited": cited,
        "hallucinated": len(hallucinated),
    }


def _step(w: dict[str, np.ndarray], batch: Sequence[dict[str, Any]], lr: float) -> float:
    gE = np.zeros_like(w["E"])
    gW = np.zeros_like(w["W"])
    gb = np.zeros_like(w["b"])
    gWc = np.zeros_like(w["Wc"])
    loss = 0.0
    for ex in batch:
        q = _embed_mean(w, ex["query"])
        logits = w["b"] + w["W"] @ q
        p = _softmax2(logits)
        y = int(ex["decision"])
        loss += -float(np.log(max(p[y], 1e-9)))
        dlog = p.copy()
        dlog[y] -= 1.0
        gb += dlog
        gW += dlog[:, None] * q[None, :]
        dq = dlog @ w["W"]
        parts = [pt for pt in ex["query"].split() if pt]
        ntok = max(len(parts), 1)
        for pt in parts:
            gE[tok_id(pt)] += dq / ntok
        for hi, h in enumerate(ex["handles"]):
            gold = 1.0 if hi in ex["cite"] else 0.0
            hv = _embed_mean(w, h["note"])
            score = float(np.dot(w["Wc"], hv))
            pred = 1.0 / (1.0 + np.exp(-np.clip(score, -40.0, 40.0)))
            loss += 0.35 * -(
                gold * np.log(max(pred, 1e-9)) + (1.0 - gold) * np.log(max(1.0 - pred, 1e-9))
            )
            gWc += 0.35 * (pred - gold) * hv
    n = max(len(batch), 1)
    w["E"] -= lr * gE / n
    w["W"] -= lr * gW / n
    w["b"] -= lr * gb / n
    w["Wc"] -= lr * gWc / n
    return loss / n


def evaluate(w: dict[str, np.ndarray], data: Sequence[dict[str, Any]]) -> dict[str, float]:
    plan = 0
    abstain = 0
    abstain_n = 0
    hall = 0
    for ex in data:
        f = forward(w, ex)
        hall += int(f["hallucinated"])
        offered = {h["id"] for h in ex["handles"]}
        cited_ok = all(cid in offered for cid in f["cited"])
        valid = cited_ok and (
            (f["decision"] == ABSTAIN and len(f["cited"]) == 0)
            or (f["decision"] == NAVIGATE and len(f["cited"]) >= 1)
        )
        if valid:
            plan += 1
        if ex["decision"] == ABSTAIN:
            abstain_n += 1
            if f["decision"] == ABSTAIN:
                abstain += 1
    n = max(len(data), 1)
    return {
        "plan_valid": plan / n,
        "abstain": (abstain / abstain_n) if abstain_n else 0.0,
        "hallucinated": float(hall),
    }


def train(
    seed: int = 20260721,
    steps: int = 280,
    n: int = 80,
    lr: float = 0.08,
) -> tuple[dict[str, np.ndarray], dict[str, float]]:
    data = synth_curriculum(n, seed)
    held = data[64:] if n > 64 else data[-max(1, n // 5) :]
    train_set = data[:64] if n > 64 else data[: max(1, n - len(held))]
    w = init_weights(seed)
    span = max(len(train_set) - 8, 1)
    for s in range(int(steps)):
        start = (s * 8) % span
        batch = train_set[start : start + 8]
        if len(batch) < 8:
            batch = train_set[:8] or train_set
        _step(w, batch, lr)
    ev = evaluate(w, held)
    return w, ev


def save_npz(path: str, weights: dict[str, np.ndarray]) -> None:
    np.savez(path, **weights)


def load_npz(path: str) -> dict[str, np.ndarray]:
    data = np.load(path)
    return {k: np.asarray(data[k], dtype=np.float64) for k in data.files}
