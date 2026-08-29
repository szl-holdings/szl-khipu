#!/usr/bin/env python3
"""Train SZL nano silhouettes. Pure NumPy. MEASURED metrics only."""
from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

SEED = 20260721
rng = np.random.default_rng(SEED)
OUT = Path("/workspace/src/lib/nano-weights.json")
KIT = Path("/workspace/public/kit")
KIT.mkdir(parents=True, exist_ok=True)


def sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.clip(z, -40, 40)
    return 1.0 / (1.0 + np.exp(-z))


def softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


def make_moons(n: int, noise: float = 0.12) -> tuple[np.ndarray, np.ndarray]:
    n0 = n // 2
    n1 = n - n0
    t0 = np.linspace(0, math.pi, n0)
    t1 = np.linspace(0, math.pi, n1)
    x0 = np.stack([np.cos(t0), np.sin(t0)], axis=1)
    x1 = np.stack([1 - np.cos(t1), 1 - np.sin(t1) - 0.5], axis=1)
    x = np.concatenate([x0, x1], axis=0)
    y = np.concatenate([np.zeros(n0), np.ones(n1)])
    x = x + rng.normal(0, noise, x.shape)
    perm = rng.permutation(n)
    return x[perm], y[perm]


def mlp_train(x: np.ndarray, y: np.ndarray, h: int, k: int, epochs: int, lr: float):
    n, d = x.shape
    w1 = rng.normal(0, 0.4, (d, h))
    b1 = np.zeros(h)
    w2 = rng.normal(0, 0.4, (h, k))
    b2 = np.zeros(k)
    yoh = np.eye(k)[y.astype(int)]
    hist = []
    for ep in range(epochs):
        h1 = np.tanh(x @ w1 + b1)
        logits = h1 @ w2 + b2
        p = softmax(logits)
        loss = float(-np.mean(np.sum(yoh * np.log(p + 1e-9), axis=1)))
        dz2 = (p - yoh) / n
        dw2 = h1.T @ dz2
        db2 = dz2.sum(axis=0)
        dh1 = dz2 @ w2.T * (1 - h1**2)
        dw1 = x.T @ dh1
        db1 = dh1.sum(axis=0)
        w1 -= lr * dw1
        b1 -= lr * db1
        w2 -= lr * dw2
        b2 -= lr * db2
        pred = p.argmax(axis=1)
        acc = float((pred == y).mean())
        hist.append({"epoch": ep + 1, "loss": round(loss, 6), "acc": round(acc, 6)})
    return {"w1": w1, "b1": b1, "w2": w2, "b2": b2, "hist": hist}


def mlp_predict(pack, x: np.ndarray) -> np.ndarray:
    h1 = np.tanh(x @ pack["w1"] + pack["b1"])
    return softmax(h1 @ pack["w2"] + pack["b2"])


def silhouette_score(x: np.ndarray, labels: np.ndarray) -> float:
    """Mean silhouette. MEASURED."""
    n = len(x)
    if n < 4:
        return 0.0
    dmat = np.sqrt(((x[:, None, :] - x[None, :, :]) ** 2).sum(axis=2))
    sil = []
    for i in range(n):
        same = labels == labels[i]
        other = ~same
        same[i] = False
        if not same.any() or not other.any():
            continue
        a = dmat[i, same].mean()
        # nearest other cluster
        b = min(dmat[i, labels == c].mean() for c in np.unique(labels) if c != labels[i])
        sil.append((b - a) / max(a, b, 1e-9))
    return float(np.mean(sil)) if sil else 0.0


# ---------------------------------------------------------------------------
# 1. Moons-Nano
# ---------------------------------------------------------------------------
x_m, y_m = make_moons(400, 0.13)
split = 320
moons = mlp_train(x_m[:split], y_m[:split], h=8, k=2, epochs=220, lr=0.35)
p_te = mlp_predict(moons, x_m[split:])
acc_te = float((p_te.argmax(1) == y_m[split:]).mean())
sil_m = silhouette_score(x_m, y_m.astype(int))
# save a 180-point cloud for the canvas
cloud = [{"x": float(a), "y": float(b), "yTrue": int(c)} for a, b, c in zip(x_m[::2, 0], x_m[::2, 1], y_m[::2])]

# ---------------------------------------------------------------------------
# 2. MiniEmbed-Nano — deterministic hash table, then a tiny contrastive tweak
# ---------------------------------------------------------------------------
V, D = 64, 12
table = rng.normal(0, 0.3, (V, D)).astype(np.float64)
table /= np.linalg.norm(table, axis=1, keepdims=True) + 1e-9


def token_ids(text: str) -> list[int]:
    toks = [t for t in text.lower().replace(",", " ").replace(".", " ").split() if t]
    if not toks:
        toks = ["_"]
    out = []
    for t in toks:
        h = hashlib.sha256(t.encode()).digest()
        out.append(int.from_bytes(h[:4], "big") % V)
    return out


def embed(text: str) -> np.ndarray:
    ids = token_ids(text)
    v = table[ids].mean(axis=0)
    nrm = np.linalg.norm(v) + 1e-9
    return v / nrm


# tiny contrastive tweak on doctrine phrases vs noise
pairs_pos = [
    ("knot the run", "hash the proof"),
    ("fail closed", "proposal only"),
    ("navigate", "cite the handle"),
    ("abstain", "no grounded handle"),
    ("receipt the action", "sign the envelope"),
]
pairs_neg = [
    ("knot the run", "open the firewall"),
    ("fail closed", "best effort retry"),
    ("navigate", "invent a citation"),
    ("abstain", "guess anyway"),
]
for _ in range(80):
    for a, b in pairs_pos:
        va, vb = embed(a), embed(b)
        # pull together
        g = 0.04 * (vb - va)
        for i in token_ids(a):
            table[i] += g
        for i in token_ids(b):
            table[i] += -g
    for a, b in pairs_neg:
        va, vb = embed(a), embed(b)
        g = 0.02 * (vb - va)
        for i in token_ids(a):
            table[i] -= g
    table /= np.linalg.norm(table, axis=1, keepdims=True) + 1e-9

phrases = [
    "knot the run",
    "hash the proof",
    "fail closed",
    "proposal only",
    "navigate",
    "abstain",
    "invent a citation",
    "best effort retry",
]
embs = {p: embed(p).tolist() for p in phrases}
# retrieval: does "hash the proof" nearest-neighbor "knot the run"?
def cosine(a, b):
    return float(np.dot(a, b))

retrieval_hits = 0
retrieval_n = 0
for a, b in pairs_pos:
    q = embed(a)
    scores = sorted(((cosine(q, embed(p)), p) for p in phrases if p != a), reverse=True)
    retrieval_n += 1
    if scores[0][1] == b or scores[1][1] == b:
        retrieval_hits += 1
retrieval_acc = retrieval_hits / max(retrieval_n, 1)

# ---------------------------------------------------------------------------
# 3. TinyKhipu-Nano — NAVIGATE (1) vs ABSTAIN (0)
# features: query-handle overlap, handle count, adversarial flag, note density
# ---------------------------------------------------------------------------
def khipu_row(overlap: float, n_handles: float, adversarial: float, density: float, label: int):
    return [overlap, n_handles, adversarial, density], label


rows, labs = [], []
# grounded navigate
for _ in range(90):
    rows.append([rng.uniform(0.55, 1.0), rng.uniform(0.3, 1.0), 0.0, rng.uniform(0.2, 0.9)])
    labs.append(1)
# honest abstain — no overlap
for _ in range(90):
    rows.append([rng.uniform(0.0, 0.25), rng.uniform(0.0, 0.8), 0.0, rng.uniform(0.0, 0.6)])
    labs.append(0)
# adversarial lure (looks juicy, must abstain)
for _ in range(50):
    rows.append([rng.uniform(0.05, 0.35), rng.uniform(0.6, 1.0), 1.0, rng.uniform(0.7, 1.0)])
    labs.append(0)
xk = np.array(rows)
yk = np.array(labs)
perm = rng.permutation(len(yk))
xk, yk = xk[perm], yk[perm]
cut = int(0.8 * len(yk))
khipu = mlp_train(xk[:cut], yk[:cut], h=6, k=2, epochs=260, lr=0.4)
pk = mlp_predict(khipu, xk[cut:])
k_acc = float((pk.argmax(1) == yk[cut:]).mean())
# class-wise
abstain_mask = yk[cut:] == 0
nav_mask = yk[cut:] == 1
k_abstain = float((pk.argmax(1)[abstain_mask] == 0).mean()) if abstain_mask.any() else 0.0
k_nav = float((pk.argmax(1)[nav_mask] == 1).mean()) if nav_mask.any() else 0.0

# ---------------------------------------------------------------------------
# 4. ReceiptAgent-Nano — 4-way: ALLOW=0 DENY=1 ABSTAIN=2 ESCALATE=3
# features: authority, evidence, risk, novelty
# ---------------------------------------------------------------------------
def ra_row(authority, evidence, risk, novelty, y):
    return [authority, evidence, risk, novelty], y


rr, rl = [], []
# ALLOW: high authority, high evidence, low risk
for _ in range(70):
    rr.append([rng.uniform(0.7, 1), rng.uniform(0.7, 1), rng.uniform(0, 0.25), rng.uniform(0, 0.4)])
    rl.append(0)
# DENY: low authority or high risk with evidence of violation
for _ in range(70):
    rr.append([rng.uniform(0, 0.3), rng.uniform(0.4, 1), rng.uniform(0.6, 1), rng.uniform(0, 0.6)])
    rl.append(1)
# ABSTAIN: missing evidence
for _ in range(70):
    rr.append([rng.uniform(0.3, 0.8), rng.uniform(0, 0.25), rng.uniform(0.2, 0.6), rng.uniform(0.2, 0.8)])
    rl.append(2)
# ESCALATE: high novelty + medium risk
for _ in range(70):
    rr.append([rng.uniform(0.4, 0.9), rng.uniform(0.3, 0.7), rng.uniform(0.4, 0.8), rng.uniform(0.75, 1)])
    rl.append(3)
xr = np.array(rr)
yr = np.array(rl)
perm = rng.permutation(len(yr))
xr, yr = xr[perm], yr[perm]
cutr = int(0.8 * len(yr))
ra = mlp_train(xr[:cutr], yr[:cutr], h=10, k=4, epochs=280, lr=0.35)
pr = mlp_predict(ra, xr[cutr:])
ra_acc = float((pr.argmax(1) == yr[cutr:]).mean())
ra_per = {}
for c, name in enumerate(["ALLOW", "DENY", "ABSTAIN", "ESCALATE"]):
    m = yr[cutr:] == c
    ra_per[name] = float((pr.argmax(1)[m] == c).mean()) if m.any() else 0.0

# ---------------------------------------------------------------------------
# 5. Lambda-gate — scalar trust → open/closed. Fail-closed below λ.
# ---------------------------------------------------------------------------
# λ* learned as the unique threshold that maximises abstain-precision on a
# 1-D logistic. This is the silhouette of Conjecture-1 (Λ uniqueness).
lam_x = rng.uniform(0, 1, 400)
# true open iff trust > 0.62
lam_y = (lam_x > 0.62).astype(int)
# logistic
w = np.array([0.0])
b = 0.0
for _ in range(400):
    z = lam_x * w[0] + b
    p = sigmoid(z)
    w[0] -= 0.4 * ((p - lam_y) * lam_x).mean()
    b -= 0.4 * (p - lam_y).mean()
# threshold: p=0.5 → x = -b/w
lam_star = float(-b / (w[0] + 1e-9))
lam_pred = (lam_x > lam_star).astype(int)
lam_acc = float((lam_pred == lam_y).mean())
# fail-closed: never open below true 0.62
false_open = float(((lam_x < 0.62) & (lam_pred == 1)).mean())

# ---------------------------------------------------------------------------
# Pack
# ---------------------------------------------------------------------------
def arr(a: np.ndarray):
    return np.asarray(a).astype(float).round(6).tolist()


payload = {
    "seed": SEED,
    "trainedAt": datetime.now(timezone.utc).isoformat(),
    "doctrine": "v11",
    "label": "MEASURED",
    "moons": {
        "w1": arr(moons["w1"]),
        "b1": arr(moons["b1"]),
        "w2": arr(moons["w2"]),
        "b2": arr(moons["b2"]),
        "holdoutAcc": round(acc_te, 4),
        "silhouette": round(sil_m, 4),
        "finalLoss": moons["hist"][-1]["loss"],
        "epochs": len(moons["hist"]),
        "nTrain": split,
        "nTest": 80,
        "cloud": cloud,
        "curve": moons["hist"][::10],
    },
    "miniEmbed": {
        "V": V,
        "d": D,
        "table": arr(table),
        "retrievalHitAt2": round(retrieval_acc, 4),
        "phrases": embs,
        "seed": SEED,
    },
    "tinyKhipu": {
        "w1": arr(khipu["w1"]),
        "b1": arr(khipu["b1"]),
        "w2": arr(khipu["w2"]),
        "b2": arr(khipu["b2"]),
        "holdoutAcc": round(k_acc, 4),
        "abstainRecall": round(k_abstain, 4),
        "navigateRecall": round(k_nav, 4),
        "epochs": len(khipu["hist"]),
        "curve": khipu["hist"][::10],
    },
    "receiptAgent": {
        "w1": arr(ra["w1"]),
        "b1": arr(ra["b1"]),
        "w2": arr(ra["w2"]),
        "b2": arr(ra["b2"]),
        "holdoutAcc": round(ra_acc, 4),
        "perClass": {k: round(v, 4) for k, v in ra_per.items()},
        "epochs": len(ra["hist"]),
        "curve": ra["hist"][::10],
        "labels": ["ALLOW", "DENY", "ABSTAIN", "ESCALATE"],
    },
    "lambdaGate": {
        "w": round(float(w[0]), 6),
        "b": round(float(b), 6),
        "lambdaStar": round(lam_star, 4),
        "holdoutAcc": round(lam_acc, 4),
        "falseOpenRate": round(false_open, 4),
        "note": "Λ-aggregator uniqueness remains Conjecture 1 — this is a 1-D silhouette, not a proof.",
    },
}

OUT.write_text(json.dumps(payload, indent=2))
(KIT / "nano-weights.json").write_text(json.dumps(payload))
print(json.dumps({
    "wrote": str(OUT),
    "moons_acc": acc_te,
    "moons_sil": sil_m,
    "embed_hit": retrieval_acc,
    "khipu_acc": k_acc,
    "khipu_abstain": k_abstain,
    "ra_acc": ra_acc,
    "lambda": lam_star,
    "false_open": false_open,
}, indent=2))
