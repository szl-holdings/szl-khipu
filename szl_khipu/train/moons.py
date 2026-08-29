# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Two-moons 2-8-2 tanh-softmax SGD. Tiny live trainer, not a foundation model."""

from __future__ import annotations

import numpy as np

IN, H, OUT = 2, 8, 2


def two_moons(n: int = 200, seed: int = 7, noise: float = 0.08) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(int(seed))
    half = n // 2
    t0 = np.pi * rng.random(half)
    x0 = np.cos(t0) + rng.normal(0.0, noise, half)
    y0 = np.sin(t0) + rng.normal(0.0, noise, half)
    t1 = np.pi * rng.random(n - half)
    x1 = 1.0 - np.cos(t1) + rng.normal(0.0, noise, n - half)
    y1 = 0.5 - np.sin(t1) + rng.normal(0.0, noise, n - half)
    X = np.stack(
        [np.concatenate([x0, x1]), np.concatenate([y0, y1])],
        axis=1,
    )
    y = np.concatenate(
        [np.zeros(half, dtype=np.int64), np.ones(n - half, dtype=np.int64)]
    )
    perm = rng.permutation(n)
    return X[perm], y[perm]


def init_weights(seed: int) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(int(seed))

    def fill(fan_in: int, fan_out: int) -> np.ndarray:
        s = np.sqrt(2.0 / fan_in)
        return rng.normal(0.0, s, size=(fan_out, fan_in))

    return {
        "W1": fill(IN, H),
        "b1": np.zeros(H),
        "W2": fill(H, OUT),
        "b2": np.zeros(OUT),
    }


def _softmax(logits: np.ndarray) -> np.ndarray:
    m = logits.max(axis=-1, keepdims=True)
    e = np.exp(logits - m)
    return e / e.sum(axis=-1, keepdims=True)


def forward(w: dict[str, np.ndarray], X: np.ndarray) -> dict[str, np.ndarray]:
    X = np.asarray(X, dtype=np.float64)
    if X.ndim == 1:
        X = X[None, :]
    h = X @ w["W1"].T + w["b1"]
    ht = np.tanh(h)
    logits = ht @ w["W2"].T + w["b2"]
    p = _softmax(logits)
    return {"h": h, "ht": ht, "logits": logits, "p": p}


def _step(w: dict[str, np.ndarray], X: np.ndarray, y: np.ndarray, lr: float) -> float:
    f = forward(w, X)
    n = X.shape[0]
    p = f["p"]
    loss = float(-np.log(np.clip(p[np.arange(n), y], 1e-9, 1.0)).mean())
    dlog = p.copy()
    dlog[np.arange(n), y] -= 1.0
    dlog /= n
    gW2 = dlog.T @ f["ht"]
    gb2 = dlog.sum(axis=0)
    dht = dlog @ w["W2"]
    dh = dht * (1.0 - f["ht"] ** 2)
    gW1 = dh.T @ X
    gb1 = dh.sum(axis=0)
    w["W2"] -= lr * gW2
    w["b2"] -= lr * gb2
    w["W1"] -= lr * gW1
    w["b1"] -= lr * gb1
    return loss


def accuracy(w: dict[str, np.ndarray], X: np.ndarray, y: np.ndarray) -> float:
    pred = np.argmax(forward(w, X)["p"], axis=1)
    return float(np.mean(pred == y))


def train(
    seed: int = 7,
    steps: int = 400,
    n: int = 200,
    lr: float = 0.15,
    batch: int = 32,
) -> tuple[dict[str, np.ndarray], dict[str, float]]:
    X, y = two_moons(n, seed)
    w = init_weights(seed)
    rng = np.random.default_rng(int(seed) + 3)
    loss = 0.0
    for _ in range(int(steps)):
        idx = rng.integers(0, X.shape[0], size=batch)
        loss = _step(w, X[idx], y[idx], lr)
    acc = accuracy(w, X, y)
    return w, {"acc": acc, "loss": float(loss), "n": float(n)}


def save_npz(path: str, weights: dict[str, np.ndarray]) -> None:
    np.savez(path, **weights)


def load_npz(path: str) -> dict[str, np.ndarray]:
    data = np.load(path)
    return {k: np.asarray(data[k], dtype=np.float64) for k in data.files}


def predict(w: dict[str, np.ndarray], X: np.ndarray) -> np.ndarray:
    return np.argmax(forward(w, X)["p"], axis=1)
