# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""ReceiptAgent surrogate: 24-d MLP 24-16-8-4.

rule_check is GROUND TRUTH (kernel wins). The MLP is advisory.
Classes: ALLOW / WARN / BLOCKED / ESCALATE.
"""

from __future__ import annotations

from typing import Any

import numpy as np

FEATURE_DIM = 24
HIDDEN = (16, 8)
N_CLASSES = 4
LABELS: tuple[str, ...] = ("ALLOW", "WARN", "BLOCKED", "ESCALATE")
ALLOW, WARN, BLOCKED, ESCALATE = 0, 1, 2, 3


def rule_check(z: np.ndarray) -> int:
    """Kernel ground truth. The MLP does not override this."""
    z = np.asarray(z, dtype=np.float64).ravel()
    if z.size != FEATURE_DIM:
        return BLOCKED
    lam = float(z[0])
    any_zero = float(z[1]) > 0.5
    chain_ok = float(z[2]) > 0.5
    digest_ok = float(z[3]) > 0.5
    finite = float(z[4]) > 0.5
    pin_ok = float(z[5]) > 0.5
    bound_ok = float(z[7]) > 0.5
    hard_deny = float(z[8]) > 0.5
    allow = float(z[9]) > 0.5
    yuyay_min = float(z[13])
    if hard_deny or (not finite) or (not digest_ok):
        return BLOCKED
    if not allow:
        return BLOCKED
    if any_zero or lam < 0.5:
        return BLOCKED
    if (not chain_ok) or (not pin_ok):
        return ESCALATE
    if (not bound_ok) or yuyay_min < 0.9:
        return WARN
    return ALLOW


def _sample_for_label(rng: np.random.Generator, label: int) -> np.ndarray:
    z = np.zeros(FEATURE_DIM, dtype=np.float64)
    z[0] = rng.uniform(0.55, 1.0)
    z[1] = 0.0  # any_zero
    z[2] = 1.0  # chain_ok
    z[3] = 1.0  # digest_ok
    z[4] = 1.0  # finite
    z[5] = 1.0  # pin_ok
    z[6] = rng.uniform(0.0, 1.0)  # bound_ratio (unused by kernel)
    z[7] = 1.0  # bound_ok
    z[8] = 0.0  # hard_deny
    z[9] = 1.0  # explicit_allow
    z[13] = rng.uniform(0.92, 1.0)  # yuyay_min
    if label == ALLOW:
        pass
    elif label == WARN:
        if rng.random() < 0.5:
            z[7] = 0.0
        else:
            z[13] = rng.uniform(0.70, 0.88)
    elif label == BLOCKED:
        pick = int(rng.integers(0, 4))
        if pick == 0:
            z[8] = 1.0
        elif pick == 1:
            z[9] = 0.0
        elif pick == 2:
            z[1] = 1.0
        else:
            z[0] = rng.uniform(0.0, 0.45)
    elif label == ESCALATE:
        if rng.random() < 0.5:
            z[2] = 0.0
        else:
            z[5] = 0.0
    return z


def synth_features(n: int = 400, seed: int = 7) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(int(seed))
    per = max(n // N_CLASSES, 1)
    xs: list[np.ndarray] = []
    ys: list[int] = []
    for lab in range(N_CLASSES):
        for _ in range(per):
            z = _sample_for_label(rng, lab)
            y = rule_check(z)
            xs.append(z)
            ys.append(y)
    X = np.stack(xs, axis=0)
    y = np.asarray(ys, dtype=np.int64)
    perm = rng.permutation(X.shape[0])
    return X[perm], y[perm]


def init_weights(seed: int) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(int(seed))

    def xavier(fan_in: int, fan_out: int) -> np.ndarray:
        s = np.sqrt(2.0 / fan_in)
        return rng.normal(0.0, s, size=(fan_out, fan_in))

    return {
        "W1": xavier(FEATURE_DIM, HIDDEN[0]),
        "b1": np.zeros(HIDDEN[0]),
        "W2": xavier(HIDDEN[0], HIDDEN[1]),
        "b2": np.zeros(HIDDEN[1]),
        "W3": xavier(HIDDEN[1], N_CLASSES),
        "b3": np.zeros(N_CLASSES),
    }


def _relu(a: np.ndarray) -> np.ndarray:
    return np.maximum(a, 0.0)


def _softmax(logits: np.ndarray) -> np.ndarray:
    m = logits.max(axis=-1, keepdims=True)
    e = np.exp(logits - m)
    return e / e.sum(axis=-1, keepdims=True)


def forward_batch(w: dict[str, np.ndarray], X: np.ndarray) -> dict[str, np.ndarray]:
    h1 = X @ w["W1"].T + w["b1"]
    a1 = _relu(h1)
    h2 = a1 @ w["W2"].T + w["b2"]
    a2 = _relu(h2)
    logits = a2 @ w["W3"].T + w["b3"]
    p = _softmax(logits)
    return {"h1": h1, "a1": a1, "h2": h2, "a2": a2, "logits": logits, "p": p}


def predict(w: dict[str, np.ndarray], X: np.ndarray) -> np.ndarray:
    X = np.asarray(X, dtype=np.float64)
    if X.ndim == 1:
        X = X[None, :]
        squeeze = True
    else:
        squeeze = False
    pred = np.argmax(forward_batch(w, X)["p"], axis=1)
    return pred[0] if squeeze else pred


def _step(
    w: dict[str, np.ndarray],
    X: np.ndarray,
    y: np.ndarray,
    lr: float,
) -> float:
    f = forward_batch(w, X)
    n = X.shape[0]
    p = f["p"]
    loss = float(-np.log(np.clip(p[np.arange(n), y], 1e-9, 1.0)).mean())
    dlog = p.copy()
    dlog[np.arange(n), y] -= 1.0
    dlog /= n
    gW3 = dlog.T @ f["a2"]
    gb3 = dlog.sum(axis=0)
    da2 = dlog @ w["W3"]
    dh2 = da2 * (f["h2"] > 0)
    gW2 = dh2.T @ f["a1"]
    gb2 = dh2.sum(axis=0)
    da1 = dh2 @ w["W2"]
    dh1 = da1 * (f["h1"] > 0)
    gW1 = dh1.T @ X
    gb1 = dh1.sum(axis=0)
    w["W3"] -= lr * gW3
    w["b3"] -= lr * gb3
    w["W2"] -= lr * gW2
    w["b2"] -= lr * gb2
    w["W1"] -= lr * gW1
    w["b1"] -= lr * gb1
    return loss


def agree(w: dict[str, np.ndarray], X: np.ndarray, y: np.ndarray) -> float:
    """Held-out agreement with rule_check (kernel)."""
    pred = predict(w, X)
    kernel = np.array([rule_check(row) for row in X], dtype=np.int64)
    # y should already be kernel labels; use kernel explicitly.
    return float(np.mean(pred == kernel))


def train(
    seed: int = 7,
    max_steps: int = 600,
    target_agree: float = 0.90,
    lr: float = 0.08,
    batch: int = 10_000,
) -> tuple[dict[str, np.ndarray], dict[str, float]]:
    X, y = synth_features(800, seed)
    n = X.shape[0]
    split = int(0.75 * n)
    Xtr, ytr = X[:split], y[:split]
    Xho, yho = X[split:], y[split:]
    rng = np.random.default_rng(int(seed) + 1)
    best_w: dict[str, np.ndarray] | None = None
    best_agree = -1.0
    used_steps = 0
    for attempt in range(4):
        w = init_weights(seed + 19 * attempt)
        lr_i = lr
        for step in range(int(max_steps)):
            if batch >= Xtr.shape[0]:
                _step(w, Xtr, ytr, lr_i)
            else:
                idx = rng.integers(0, Xtr.shape[0], size=batch)
                _step(w, Xtr[idx], ytr[idx], lr_i)
            used_steps = step + 1 + attempt * int(max_steps)
            if step % 15 == 0 or step == max_steps - 1:
                held = agree(w, Xho, yho)
                if held > best_agree:
                    best_agree = held
                    best_w = {k: v.copy() for k, v in w.items()}
                if held >= target_agree:
                    return w, {
                        "agree": held,
                        "steps": float(used_steps),
                        "n_held": float(Xho.shape[0]),
                        "kernel_wins": 1.0,
                    }
            if step > 0 and step % 120 == 0:
                lr_i *= 0.8
    assert best_w is not None
    held = agree(best_w, Xho, yho)
    return best_w, {
        "agree": held,
        "steps": float(used_steps),
        "n_held": float(Xho.shape[0]),
        "kernel_wins": 1.0,
    }


def decide(features: np.ndarray, weights: dict[str, np.ndarray] | None = None) -> dict[str, Any]:
    """Kernel always wins. Surrogate is advisory."""
    kernel = int(rule_check(features))
    model = int(predict(weights, features)) if weights is not None else kernel
    return {
        "kernel": LABELS[kernel],
        "surrogate": LABELS[model],
        "agree": kernel == model,
        "advisory": True,
        "decision": LABELS[kernel],
    }


def save_npz(path: str, weights: dict[str, np.ndarray]) -> None:
    np.savez(path, **weights)


def load_npz(path: str) -> dict[str, np.ndarray]:
    data = np.load(path)
    return {k: np.asarray(data[k], dtype=np.float64) for k in data.files}
