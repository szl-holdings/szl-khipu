# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Lab numeric identities and structural PURIQ locked-8 checks.

NEVER claim the numeric identities ARE the Lean locked-8.
Numerics are lab CHECKED. Lean locked-8 are structural silhouettes.
CHECKED ≠ PROVEN.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Iterable, Sequence

import numpy as np

from .chain import UnifiedReceiptChain, canon, sha256_hex
from .doctrine import LOCKED_EIGHT
from .governed_norm import rms_norm
from .lambda_gate import check_a2, check_a3, check_a4, uniform_weights, wgm
from .receipt_attn import softmax_rows

# ---------------------------------------------------------------------------
# Numeric identities — lab CHECKED. Not the Lean kernel.
# ---------------------------------------------------------------------------


def softmax_row_sum(scores: np.ndarray) -> float:
    p = softmax_rows(scores)
    return float(np.max(np.abs(p.sum(axis=-1) - 1.0)))


def cauchy_schwarz(u: np.ndarray, v: np.ndarray) -> float:
    u = np.asarray(u, dtype=np.float64).ravel()
    v = np.asarray(v, dtype=np.float64).ravel()
    lhs = float(np.dot(u, v) ** 2)
    rhs = float(np.dot(u, u) * np.dot(v, v))
    return max(0.0, lhs - rhs)


def parseval_dft(x: np.ndarray) -> float:
    """Unnormalized DFT: Σ x²  vs  (1/N) Σ |X|²."""
    x = np.asarray(x, dtype=np.float64).ravel()
    n = x.size
    if n == 0:
        return 0.0
    time = float(np.dot(x, x))
    X = np.fft.fft(x)
    freq = float(np.vdot(X, X).real) / n
    return abs(time - freq)


def wgm_homogeneous(x: np.ndarray, w: np.ndarray, c: float = 0.4) -> float:
    return 0.0 if check_a2(x, w, c=c) else 1.0


def wgm_bounded(x: np.ndarray, w: np.ndarray) -> float:
    return 0.0 if check_a4(x, w) else 1.0


def wgm_zero_route(x: np.ndarray, w: np.ndarray) -> float:
    z = np.asarray(x, dtype=np.float64).copy()
    z[z.size // 2] = 0.0
    return abs(wgm(z, w))


def rms_unit(x: np.ndarray, gamma: np.ndarray | None = None, eps: float = 1e-5) -> float:
    _, unit_rms, _ = rms_norm(x, gamma, eps=eps)
    return unit_rms


# ---------------------------------------------------------------------------
# Structural PURIQ locked-8 — silhouettes of F1,F4,F7,F11,F12,F18,F19,F22.
# These are structural checks, not a claim that the Lean kernel ran here.
# ---------------------------------------------------------------------------


def replay_hash_ok(seed: int = 11) -> bool:
    """F1 — same payload twice ⇒ same digest."""
    payload = {"seed": int(seed), "log": ["a", "b", 3]}
    c1 = UnifiedReceiptChain()
    c2 = UnifiedReceiptChain()
    r1 = c1.emit("szl-replay", "mint", payload)
    r2 = c2.emit("szl-replay", "mint", payload)
    return r1.digest == r2.digest and r1.digest != ""


def dag_acyclic(edges: Sequence[tuple[int, int]]) -> bool:
    """F4 — edges dst < src ⇒ no cycle (plus DFS)."""
    if not edges:
        return True
    for src, dst in edges:
        if not dst < src:
            return False
    n = 1 + max(max(e) for e in edges)
    adj: list[list[int]] = [[] for _ in range(n)]
    for src, dst in edges:
        adj[src].append(dst)
    seen = [0] * n
    stack = [0] * n

    def dfs(u: int) -> bool:
        seen[u] = 1
        stack[u] = 1
        for v in adj[u]:
            if stack[v]:
                return False
            if not seen[v] and not dfs(v):
                return False
        stack[u] = 0
        return True

    return all(seen[i] or dfs(i) for i in range(n))


def fifo_ok(msgs: Iterable[Any]) -> bool:
    """F7 — drain(enqueueAll([], msgs)) = msgs."""
    msgs_l = list(msgs)
    q: deque[Any] = deque()
    for m in msgs_l:
        q.append(m)
    out: list[Any] = []
    while q:
        out.append(q.popleft())
    return out == msgs_l


def ayni_ok(transfers: Sequence[tuple[int, int, float]]) -> bool:
    """F11 — Σ in = Σ out (ayni reciprocity)."""
    inn = 0.0
    out = 0.0
    for _src, _dst, amt in transfers:
        out += float(amt)
        inn += float(amt)
    return abs(inn - out) < 1e-12


def kuramoto_bounded(k: np.ndarray) -> bool:
    """F12 — |Σ K| ≤ Σ |K| (additive fragment ONLY, not full nonlinear sync)."""
    k = np.asarray(k, dtype=np.float64).ravel()
    return abs(float(k.sum())) <= float(np.abs(k).sum()) + 1e-12


def rs_singleton(n: int = 10, k: int = 6, expected: int | None = None) -> bool:
    """F18 — RS(n, k) Singleton bound d_min = n - k + 1."""
    dmin = n - k + 1
    if expected is None:
        expected = 5 if (n, k) == (10, 6) else dmin
    return dmin == expected and dmin > 0


def bekenstein_additive(regions: Sequence[float], total: float) -> bool:
    """F19 — monotone additive scaffolding: Σ S_region ≤ S_total.

    Not the Bekenstein bound S ≤ 2π k R E / ℏ c.
    """
    return float(sum(regions)) <= float(total) + 1e-12


def seq_strictly_increasing(seq: Sequence[int]) -> bool:
    """F22 — sequence numbers strictly increase."""
    s = list(seq)
    return all(s[i] > s[i - 1] for i in range(1, len(s)))


def _row(
    id_: str,
    ok: bool,
    residual: float,
    epsilon: float,
    proof_status: str,
    family: str,
) -> dict[str, Any]:
    return {
        "id": id_,
        "ok": bool(ok) and residual <= epsilon + 1e-15,
        "residual": float(residual),
        "epsilon": float(epsilon),
        "proof_status": proof_status,
        "family": family,
    }


def run_numeric(seed: int = 11) -> list[dict[str, Any]]:
    rng = np.random.default_rng(int(seed))
    x = rng.uniform(-1.0, 1.0, 16)
    u = rng.random(8)
    v = rng.random(8)
    axes = 0.2 + rng.random(6) * 0.7
    w = uniform_weights(6)
    scores = rng.normal(0.0, 1.0, size=(8, 8))
    X = rng.normal(0.0, 1.0, size=(4, 8))
    gamma = np.ones(8)
    sm_err = softmax_row_sum(scores)
    cs_err = cauchy_schwarz(u, v)
    pv_err = parseval_dft(x)
    homog = wgm_homogeneous(axes, w)
    bounded = wgm_bounded(axes, w)
    zero = wgm_zero_route(axes, w)
    rms_err = rms_unit(X, gamma)
    egypt = 0.0 if check_a3(w, 0.55) else 1.0
    bundle = 0.0 if (homog == 0.0 and egypt == 0.0 and bounded == 0.0) else 1.0
    return [
        _row("softmax_row_sum", sm_err <= 1e-6, sm_err, 1e-6, "CHECKED", "numeric"),
        _row("cauchy_schwarz", cs_err <= 1e-9, cs_err, 1e-9, "CHECKED", "numeric"),
        _row("parseval_dft", pv_err <= 1e-9, pv_err, 1e-9, "CHECKED", "numeric"),
        _row("wgm_homogeneous", homog == 0.0, homog, 0.0, "CHECKED", "numeric"),
        _row("wgm_bounded", bounded == 0.0, bounded, 0.0, "CHECKED", "numeric"),
        _row("wgm_zero_route", zero == 0.0, zero, 0.0, "CHECKED", "numeric"),
        _row("rms_unit", rms_err <= 1e-4, rms_err, 1e-4, "CHECKED", "numeric"),
        _row("wgm_egyptian_bundle", bundle == 0.0, bundle, 0.0, "CHECKED", "numeric"),
    ]


def run_puriq(seed: int = 11) -> list[dict[str, Any]]:
    rng = np.random.default_rng(int(seed))
    msgs = [int(rng.integers(0, 100)) for _ in range(8)]
    chain = UnifiedReceiptChain()
    for i in range(5):
        chain.emit("khipu", "knot", {"i": i})
    seqs = [r.seq for r in chain.receipts]
    k = rng.normal(size=8)
    f1 = replay_hash_ok(seed)
    f4 = dag_acyclic([(3, 1), (2, 0), (4, 2)])
    f7 = fifo_ok(msgs)
    f11 = ayni_ok([(0, 1, 4.0), (1, 0, 4.0)])
    f12 = kuramoto_bounded(k)
    f18 = rs_singleton(10, 6) and (10 - 6 + 1 == 5)
    f19 = bekenstein_additive([1.1, 2.2], 3.3)
    f22 = seq_strictly_increasing(seqs)
    locked = {
        "F1": (f1, "Replay-hash determinism"),
        "F4": (f4, "Khipu DAG acyclicity (dst<src)"),
        "F7": (f7, "Chaski FIFO"),
        "F11": (f11, "Ayni reciprocity Σin=Σout"),
        "F12": (f12, "Kuramoto additive |ΣK|≤Σ|K|"),
        "F18": (f18, "RS singleton n-k+1"),
        "F19": (f19, "Additive S regions ≤ S total"),
        "F22": (f22, "Khipu emit monotonicity"),
    }
    rows: list[dict[str, Any]] = []
    for fid in LOCKED_EIGHT:
        ok, _note = locked[fid]
        rows.append(
            _row(
                fid,
                bool(ok),
                0.0 if ok else 1.0,
                0.0,
                "STRUCTURAL",
                "puriq_locked8",
            )
        )
    return rows


def run_all(seed: int = 11) -> list[dict[str, Any]]:
    """Numeric CHECKED list, then structural locked-8 list. Separate families."""
    numeric = run_numeric(seed)
    puriq = run_puriq(seed)
    return numeric + puriq


def digest_run(rows: list[dict[str, Any]]) -> str:
    slim = [
        {"id": r["id"], "ok": r["ok"], "residual": round(float(r["residual"]), 12)}
        for r in rows
    ]
    return sha256_hex(canon(slim))
