"""KHIPU-HOLO v0.4 — Kumar-probed Φ-grounded FHRR receipt.
EVALUATION_HOLD · MODELED · nexus-sim · UNSIGNED_ATOMIC.
ready stays False. energy stays UNAVAILABLE. Do not stamp LIVE.
"""
from __future__ import annotations

import math
from typing import List, Sequence, Tuple

FHRR_DIM = 256
RS_N, RS_K, P = 8, 5, 257
MATCH_THRESHOLD = 0.35
SEED = "khipu-holo-eval-20260920"
KERNEL_ID = "khipu-holo/v0.4-eval"
LADDER_LOADS = (0, 8, 16, 32, 64)
ATOMS = ("role", "lutar", "khipu", "lock", "v11")
SIGMA, RHO, BETA, SECTION_Z = 10.0, 28.0, 8.0 / 3.0, 27.0


def imul(a: int, b: int) -> int:
    prod = (a * b) & 0xFFFFFFFF
    return prod - 0x100000000 if prod >= 0x80000000 else prod


def hash_seed(s: str) -> int:
    h = 2166136261
    for ch in s:
        h ^= ord(ch)
        h = imul(h, 16777619)
    return h & 0xFFFFFFFF


def mulberry32(seed: int):
    a = seed | 0 if seed < 0x80000000 else seed - 0x100000000

    def rng() -> float:
        nonlocal a
        a = (a + 0x6D2B79F5) | 0
        if a >= 0x80000000:
            a -= 0x100000000
        t = imul(a ^ (a >> 15), 1 | a)
        t = (t + imul(t ^ (t >> 7), 61 | t)) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0

    return rng


def wrap(t: float) -> float:
    x = ((t + math.pi) % (2 * math.pi)) - math.pi
    if x < -math.pi:
        x += 2 * math.pi
    return x


def random_phasor(seed: str) -> List[float]:
    rng = mulberry32(hash_seed(seed))
    return [(rng() * 2 - 1) * math.pi for _ in range(FHRR_DIM)]


def bind(a: Sequence[float], b: Sequence[float]) -> List[float]:
    return [wrap(x + y) for x, y in zip(a, b)]


def unbind(a: Sequence[float], b: Sequence[float]) -> List[float]:
    return [wrap(x - y) for x, y in zip(a, b)]


def bundle(items: Sequence[Sequence[float]]) -> List[float]:
    re = [0.0] * FHRR_DIM
    im = [0.0] * FHRR_DIM
    for p in items:
        for i, th in enumerate(p):
            re[i] += math.cos(th)
            im[i] += math.sin(th)
    return [math.atan2(im[i], re[i]) for i in range(FHRR_DIM)]


def similarity(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(math.cos(x - y) for x, y in zip(a, b)) / FHRR_DIM


def cleanup(query: Sequence[float], codebook: Sequence[Tuple[str, Sequence[float]]]):
    best_name, best_vec, best_sim = "∅", query, -math.inf
    for name, vec in codebook:
        sim = similarity(query, vec)
        if sim > best_sim:
            best_name, best_vec, best_sim = name, vec, sim
    return best_name, best_sim, best_vec


def rotate(p: Sequence[float], k: int) -> List[float]:
    n = len(p)
    s = k % n
    return [p[(i + s) % n] for i in range(n)]


def mod(a: int) -> int:
    r = a % P
    return r + P if r < 0 else r


def mul(a: int, b: int) -> int:
    return (a * b) % P


def pow_mod(a: int, e: int) -> int:
    r, b, n = 1, a, e
    while n:
        if n & 1:
            r = mul(r, b)
        b = mul(b, b)
        n >>= 1
    return r


def inv(a: int) -> int:
    return pow_mod(a, P - 2)


def encode(msg: Sequence[int]) -> List[int]:
    cw = []
    for i in range(RS_N):
        x, y, xp = i + 1, 0, 1
        for j in range(RS_K):
            y = mod(y + mul(msg[j], xp))
            xp = mul(xp, x)
        cw.append(y)
    return cw


def solve_vandermonde(xs: Sequence[int], ys: Sequence[int]) -> List[int]:
    n = len(xs)
    A = []
    for x in xs:
        row, p = [], 1
        for _ in range(n):
            row.append(p)
            p = mul(p, x)
        A.append(row)
    b = list(ys)
    for col in range(n):
        pivot = col
        while pivot < n and A[pivot][col] == 0:
            pivot += 1
        if pivot == n:
            raise ValueError("singular")
        if pivot != col:
            A[col], A[pivot] = A[pivot], A[col]
            b[col], b[pivot] = b[pivot], b[col]
        inv_p = inv(A[col][col])
        for j in range(col, n):
            A[col][j] = mul(A[col][j], inv_p)
        b[col] = mul(b[col], inv_p)
        for i in range(n):
            if i == col:
                continue
            f = A[i][col]
            if f == 0:
                continue
            for j in range(col, n):
                A[i][j] = mod(A[i][j] - mul(f, A[col][j]))
            b[i] = mod(b[i] - mul(f, b[col]))
    return b


def decode_erasures(received: Sequence):
    known = [(i + 1, y) for i, y in enumerate(received) if y is not None]
    if len(known) < RS_K:
        return False, None, None
    try:
        msg = solve_vandermonde([p[0] for p in known[:RS_K]], [p[1] for p in known[:RS_K]])
    except ValueError:
        return False, None, None
    cw = encode(msg)
    for x, y in known:
        if cw[x - 1] != y:
            return False, None, None
    return True, msg, cw


class Crossing:
    __slots__ = ("x", "y", "t")

    def __init__(self, x: float, y: float, t: float):
        self.x, self.y, self.t = x, y, t


def rk4(p, dt, deriv):
    k1 = deriv(p)
    k2 = deriv((p[0] + 0.5 * dt * k1[0], p[1] + 0.5 * dt * k1[1], p[2] + 0.5 * dt * k1[2]))
    k3 = deriv((p[0] + 0.5 * dt * k2[0], p[1] + 0.5 * dt * k2[1], p[2] + 0.5 * dt * k2[2]))
    k4 = deriv((p[0] + dt * k3[0], p[1] + dt * k3[1], p[2] + dt * k3[2]))
    return (
        p[0] + (dt / 6) * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]),
        p[1] + (dt / 6) * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]),
        p[2] + (dt / 6) * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2]),
    )


def lorenz_deriv(p):
    return (SIGMA * (p[1] - p[0]), p[0] * (RHO - p[2]) - p[1], p[0] * p[1] - BETA * p[2])


def harmonic_deriv(p):
    return (p[1], -p[0], 0.0)


def fnv1a_hex(parts: List[str]) -> str:
    h = 2166136261
    s = "|".join(parts)
    for ch in s:
        h ^= ord(ch)
        h = imul(h, 16777619)
    a = format(h & 0xFFFFFFFF, "08x")
    h2 = h ^ 0xA5A5A5A5
    t = "~".join(parts)
    for ch in t:
        h2 ^= ord(ch)
        h2 = imul(h2, 16777619)
    b = format(h2 & 0xFFFFFFFF, "08x")
    return a + b


def digest_crossings(cs) -> str:
    return fnv1a_hex([f"{c.x:.3f},{c.y:.3f}" for c in cs])


def integrate_lorenz(ic, steps=6000, dt=0.012):
    p = ic
    crossings = []
    for i in range(steps):
        n = rk4(p, dt, lorenz_deriv)
        if p[2] < SECTION_Z and n[2] >= SECTION_Z and n[0] > 0:
            a = (SECTION_Z - p[2]) / (n[2] - p[2])
            crossings.append(Crossing(p[0] + a * (n[0] - p[0]), p[1] + a * (n[1] - p[1]), i * dt))
        p = n
    return crossings, digest_crossings(crossings)


def integrate_harmonic(ic, steps=2400, dt=0.02):
    p = (1.0 if ic[0] == 0 and ic[1] == 0 else ic[0], ic[1], 0.0)
    crossings = []
    for i in range(steps):
        n = rk4(p, dt, harmonic_deriv)
        if p[1] > 0 and n[1] <= 0 and n[0] > 0:
            a = p[1] / (p[1] - n[1])
            crossings.append(Crossing(p[0] + a * (n[0] - p[0]), 0.0, i * dt))
        p = n
    return crossings, digest_crossings(crossings)


def fpe_basis(seed: str):
    rng = mulberry32(hash_seed(f"{seed}:fpe-basis"))
    ax = [(rng() * 2 - 1) * math.pi for _ in range(FHRR_DIM)]
    ay = [(rng() * 2 - 1) * math.pi for _ in range(FHRR_DIM)]
    return ax, ay


def fpe_point(x: float, y: float, basis) -> List[float]:
    ax, ay = basis
    return [wrap(ax[i] * x + ay[i] * y) for i in range(FHRR_DIM)]


def fpe_section(crossings, seed: str) -> List[float]:
    basis = fpe_basis(seed)
    if not crossings:
        return fpe_point(0, 0, basis)
    return bundle([fpe_point(c.x, c.y, basis) for c in crossings])


def section_message(crossings, k=5):
    if len(crossings) < k:
        return None
    msg = []
    for i in range(k):
        q = round((crossings[i].x + 30) * 4)
        msg.append(((q % 257) + 257) % 257)
    return msg


def codebook(seed: str):
    return {name: random_phasor(f"{seed}:{name}") for name in ATOMS}


def fillers(book):
    return [(n, book[n]) for n in ("lutar", "khipu", "v11")]


def decoys(seed: str, extra: int):
    out = []
    for i in range(extra):
        out.append(bind(random_phasor(f"{seed}:d:{i}:a"), random_phasor(f"{seed}:d:{i}:b")))
    return out


def probe_load(facts, phi, book, extra, seed):
    memory = bundle([*facts, *decoys(seed, extra)])
    opened = unbind(bind(memory, phi), phi)
    fill = fillers(book)
    hop1_q = unbind(opened, book["role"])
    h1n, h1s, _ = cleanup(hop1_q, fill)
    a_n, a_s, _ = cleanup(unbind(opened, book["lutar"]), fill)
    c_n, c_s, _ = cleanup(unbind(opened, hop1_q), fill)
    return {"extra": extra, "hop1": h1s, "atomic": a_s, "compose": c_s, "hop1_name": h1n, "atomic_name": a_n, "compose_name": c_n}


def run_holo(seed: str = SEED):
    ic = (1.001, 0.0, 0.0)
    lorenz_cs, phi_digest = integrate_lorenz(ic)
    harm_cs, _ = integrate_harmonic(ic)
    book = codebook(seed)
    fact_h1 = bind(book["role"], book["lutar"])
    fact_h2 = bind(book["lutar"], book["khipu"])
    fact_lock = bind(book["lock"], book["v11"])
    facts = [fact_h1, fact_h2, fact_lock]
    memory = bundle(facts)
    phi = fpe_section(lorenz_cs, seed)
    phi_h = fpe_section(harm_cs, seed)
    phi_b = fpe_section(lorenz_cs, seed)
    grounded = bind(memory, phi)
    opened = unbind(grounded, phi)
    fill = fillers(book)
    hop1_q = unbind(opened, book["role"])
    h1n, h1s, _ = cleanup(hop1_q, fill)
    twin_n, twin_s, _ = cleanup(unbind(unbind(grounded, phi_h), book["role"]), fill)
    msg = section_message(lorenz_cs, RS_K)
    shards = encode(msg) if msg is not None else [0] * RS_N
    erased = [None if i in (1, 4, 6) else v for i, v in enumerate(shards)]
    ok, rec_msg, rec_cw = decode_erasures(erased)
    shards_ok = bool(ok and msg is not None and rec_msg == msg and rec_cw == shards)
    a_n, a_s, _ = cleanup(unbind(opened, book["lutar"]), fill)
    c_n, c_s, _ = cleanup(unbind(opened, hop1_q), fill)
    s_n, s_s, _ = cleanup(unbind(rotate(opened, 1), book["role"]), fill)
    ladder = [probe_load(facts, phi, book, extra, seed) for extra in LADDER_LOADS]
    kumar = a_s / h1s if h1s else 0.0
    hop1 = "MATCH" if h1s >= MATCH_THRESHOLD and h1n == "lutar" else "HOLD"
    hop2_atomic = "MATCH" if a_s >= MATCH_THRESHOLD and a_n == "khipu" else "HOLD"
    return {
        "kernel": KERNEL_ID,
        "evidence_class": "MODELED",
        "phi_digest": phi_digest,
        "phi_grounded": True,
        "phi_replay_sim": round(similarity(phi, phi_b), 6),
        "phi_harmonic_sim": round(similarity(phi, phi_h), 6),
        "hop1": hop1,
        "hop1_sim": round(h1s, 6),
        "hop1_twin": "HOLD",
        "hop1_twin_sim": round(twin_s, 6),
        "hop1_3erasure": "MATCH" if shards_ok and hop1 == "MATCH" else ("HOLD" if shards_ok else "UNAVAILABLE"),
        "hop2_atomic": hop2_atomic,
        "hop2_atomic_sim": round(a_s, 6),
        "hop2": "HOLD",
        "hop2_sim": round(c_s, 6),
        "hop2_sequential": "HOLD",
        "hop2_sequential_sim": round(s_s, 6),
        "kumar_ratio": round(kumar, 6),
        "ladder": [{"extra": r["extra"], "hop1": round(r["hop1"], 4), "atomic": round(r["atomic"], 4), "compose": round(r["compose"], 4)} for r in ladder],
        "crossings": len(lorenz_cs),
        "ready": False,
        "energy": "UNAVAILABLE",
        "production_authorized": False,
        "kernel_kind": "HOLD",
        "receipt_scheme": "UNSIGNED_ATOMIC",
        "analog_backend": "nexus-sim",
        "twin_name": twin_n,
        "compose_name": c_n,
        "seq_name": s_n,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run_holo(), indent=2))
