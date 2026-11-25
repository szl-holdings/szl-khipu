#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""HJO Loom: exact, independent finite replays of the X^a = Y^b Rogers–Ramanujan results.

Sources (definitions transcribed, not imported):
  * Y. Huang, K. Lau, K. Ono, "Rogers–Ramanujan identities from the geometry of
    X^a=Y^b", arXiv:2609.20567v2 (7 Oct 2026) — eqs. (1.4)–(1.17), Thm 1.1, Cor 1.2.
  * Y. Huang, R. Jiang, A. Oblomkov, "Quot scheme of points on torus knot
    singularities", arXiv:2608.16086v1 — Thm 1.2 (motive of Quot), Thm 1.4.
  * Lean certificate: https://github.com/AxiomMath/HJO (NOT replayed here).

Every check is exact integer / rational arithmetic in the standard library and
reaches the published statement by a route different from the paper's proof:
  V1  Z_{a,b}(q) (gap-poset sum) == P_{a,b}(q) (rho-product), coefficients 0..D.
  V2  F_N(q) == (q;q)_N * C_{c,<=N}(q), with C counted by enumerating cylindric
      partitions as chains of level vectors, coefficients 0..D.
  V3  Published golden values (F_1, F_2 for (4,5); F_2 for (2,3)).
  V4  #order filters of the gap poset == rational Catalan; F_N(1) == Cat^N.
  V5  HJO Thm 1.2: brute-force count of R-submodules of F_q[[T]]^N of colength m
      by echelon enumeration == the N_{a,b;N} formula at L = q (N = 1, 2).
  V6  HJO Thm 1.4: partial groupoid sums of commuting nilpotent pairs with
      A^a = B^b over F_q stay below P_{a,b}(1/q)/(1/q;1/q)_inf (consistency only).
  V7  V5 over every prime power q <= 9 (GF(4), GF(8), GF(9) by table arithmetic).
      On the cases tried, tables that are not a field give the Thm 1.2 values
      too (Z/6 at L = 6; a GF(4) product with x*x = x the q = 4 counts), so V7
      does not test the tables; their own unit tests do.
  V8  Each colength count as a polynomial in q, interpolated exactly from the
      formula. The brute-force counts, interpolated on their own, give the same
      polynomial wherever they number at least its degree + 1; that degree is
      read from the formula's polynomial, not from the enumeration.

These are finite checks of PUBLISHED theorems. They prove nothing new, do not
replay the Lean certificate, and say nothing about historical Andean knowledge.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from itertools import product as _cartesian

SCHEMA = "szl.khipu.hjo-loom/v1"
DOMAIN = b"szl-khipu-hjo-loom-v1\0"
PAPER = "arXiv:2609.20567v2"
HJO_PAPER = "arXiv:2608.16086v1"
LEAN_REPO = "https://github.com/AxiomMath/HJO"
LEAN_REVISION_OBSERVED = "6a58dfa6ab98bd35d841cb2cf8fd9081f62fad03"
MAX_SUM = 13          # a + b bound for interactive requests
MAX_DEGREE = 72
MAX_RANK = 4
FIELDS = (2, 3)                       # interactive requests
CENSUS_FIELDS = (2, 3, 4, 5, 7, 8, 9)  # every prime power q <= 9 (offline census)
# Monic moduli, coefficients low -> high over F_p. A prime field is F_p[x]/(x).
GF_MODULI = {
    4: (2, (1, 1, 1)),     # x^2 + x + 1 over F_2
    8: (2, (1, 1, 0, 1)),  # x^3 + x + 1 over F_2
    9: (3, (1, 0, 1)),     # x^2 + 1 over F_3
}

__all__ = [
    "HjoHold", "GapPoset", "gap_poset", "rational_catalan", "order_filters",
    "z_series", "p_series", "rho", "f_polynomial", "n_bivariate",
    "balanced_profile", "cylindric_series", "quot_formula_counts",
    "quot_formula_polynomials", "quot_bruteforce_counts", "quot_bruteforce_census",
    "GaloisField", "galois_field", "nilpotent_pair_terms", "groupoid_prediction",
    "verify", "seal", "GOLDEN",
]


class HjoHold(ValueError):
    """Fail-closed refusal: invalid input, budget exceeded or mismatch."""


# --------------------------------------------------------------------------
# Exact series / polynomial arithmetic (lists of ints, index = power of q)
# --------------------------------------------------------------------------

def _trim(p: list[int]) -> list[int]:
    while len(p) > 1 and p[-1] == 0:
        p.pop()
    return p


def _mul(x: list[int], y: list[int], limit: int | None = None) -> list[int]:
    """Product; truncated to degree <= limit when given."""
    if limit is None:
        limit = len(x) + len(y) - 2
    out = [0] * (limit + 1)
    for i, xi in enumerate(x):
        if xi == 0 or i > limit:
            continue
        for j, yj in enumerate(y[: limit - i + 1]):
            if yj:
                out[i + j] += xi * yj
    return out


def _times_1mqk(x: list[int], k: int, limit: int | None = None) -> list[int]:
    """x * (1 - q^k)."""
    n = len(x) + k if limit is None else limit + 1
    out = [0] * n
    for i, v in enumerate(x[:n]):
        out[i] += v
        if i + k < n:
            out[i + k] -= v
    return out


def _over_1mqk(x: list[int], k: int, limit: int) -> list[int]:
    """Truncated series x / (1 - q^k) = x * sum q^{kj}."""
    out = list(x[: limit + 1]) + [0] * max(0, limit + 1 - len(x))
    for i in range(k, limit + 1):
        out[i] += out[i - k]
    return out


def _exact_div_1mqk(x: list[int], k: int) -> list[int]:
    """Exact polynomial division by (1 - q^k); refuses a nonzero remainder."""
    y = _trim(list(x))
    n = len(y) - 1
    if n < k:
        if any(y):
            raise HjoHold("NON_EXACT_GAUSSIAN_DIVISION")
        return [0]
    out = [0] * (n - k + 1)
    for j in range(n - k + 1):          # Q_j = y_j + Q_{j-k}
        out[j] = y[j] + (out[j - k] if j >= k else 0)
    for j in range(n - k + 1, n + 1):   # tail: y_j = -Q_{j-k}
        if y[j] + out[j - k] != 0:
            raise HjoHold("NON_EXACT_GAUSSIAN_DIVISION")
    return _trim(out)


def _poch_exponent_series(exps: tuple[tuple[int, int], ...], limit: int) -> list[int]:
    """prod_k (q;q)_k^{e_k} truncated to degree <= limit."""
    return list(_poch_series_cached(exps, limit))


@lru_cache(maxsize=65536)
def _poch_series_cached(exps: tuple[tuple[int, int], ...], limit: int) -> tuple[int, ...]:
    s = [1] + [0] * limit
    for k, e in exps:
        for _ in range(abs(e)):
            for i in range(1, k + 1):
                if i > limit:
                    break
                s = _times_1mqk(s, i, limit) if e > 0 else _over_1mqk(s, i, limit)
    return tuple(s)


@lru_cache(maxsize=65536)
def _poch_poly_cached(exps: tuple[tuple[int, int], ...]) -> tuple[int, ...]:
    """prod_k (q;q)_k^{e_k} as an EXACT polynomial (must divide)."""
    num = [1]
    den: list[int] = []
    for k, e in exps:
        for _ in range(abs(e)):
            if e > 0:
                for i in range(1, k + 1):
                    num = _times_1mqk(num, i)
            else:
                den.extend(range(1, k + 1))
    num = _trim(num)
    for i in sorted(den, reverse=True):
        num = _exact_div_1mqk(num, i)
    return tuple(num)


def _poch(k: int, limit: int | None = None) -> list[int]:
    p = [1]
    for i in range(1, k + 1):
        p = _times_1mqk(p, i, limit)
    return _trim(p) if limit is None else p


def _eval(poly: list[int], x: Fraction) -> Fraction:
    acc = Fraction(0)
    for c in reversed(poly):
        acc = acc * x + c
    return acc


# --------------------------------------------------------------------------
# Gap poset of the numerical semigroup <a, b>
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class GapPoset:
    a: int
    b: int
    d: int
    delta: int
    f: int
    gaps: tuple[int, ...]
    above: tuple[tuple[int, ...], ...]   # indices h with g < h in the order
    kmat: tuple[tuple[int, ...], ...]    # K(h - g) by index (g row, h col)
    shift: tuple[tuple[int, int, int], ...]  # indices of g-a, g-b, g-a-b (or -1)

    def k(self, s: int) -> int:
        return (s >= 0) - (s >= self.a) - (s >= self.b) + (s >= self.d)


def _validate_pair(a, b, *, bound: int = MAX_SUM) -> tuple[int, int]:
    if type(a) is not int or type(b) is not int:
        raise HjoHold("PAIR_NOT_INTEGER")
    if not 1 < a < b or math.gcd(a, b) != 1:
        raise HjoHold("PAIR_NOT_COPRIME_1_LT_A_LT_B")
    if a + b > bound:
        raise HjoHold("PAIR_EXCEEDS_INTERACTIVE_BOUND")
    return a, b


@lru_cache(maxsize=None)
def _gap_poset(a: int, b: int) -> GapPoset:
    d, f = a + b, a * b - a - b
    in_gamma = [False] * (f + d + 2)
    for u in range(0, len(in_gamma) // a + 1):
        for v in range(0, len(in_gamma) // b + 1):
            s = u * a + v * b
            if s < len(in_gamma):
                in_gamma[s] = True
    gaps = tuple(g for g in range(f + 1) if not in_gamma[g])
    delta = (a - 1) * (b - 1) // 2
    if len(gaps) != delta or gaps[-1] != f:
        raise HjoHold("SEMIGROUP_INVARIANT_FAILED")
    idx = {g: i for i, g in enumerate(gaps)}
    above = tuple(
        tuple(j for j, h in enumerate(gaps) if h > g and in_gamma[h - g])
        for g in gaps
    )
    poset = GapPoset(a, b, d, delta, f, gaps, above, (), ())
    kmat = tuple(tuple(poset.k(h - g) for h in gaps) for g in gaps)
    shift = tuple((idx.get(g - a, -1), idx.get(g - b, -1), idx.get(g - d, -1)) for g in gaps)
    return GapPoset(a, b, d, delta, f, gaps, above, kmat, shift)


def gap_poset(a: int, b: int) -> GapPoset:
    a, b = _validate_pair(a, b, bound=40)
    return _gap_poset(a, b)


def rational_catalan(a: int, b: int) -> int:
    return math.comb(a + b, a) // (a + b)


def _cone(poset: GapPoset, top: int):
    """All order-preserving n: G -> {0..top} (n_g <= n_h when g precedes h)."""
    m = len(poset.gaps)
    n = [0] * m
    order = list(range(m - 1, -1, -1))   # descending numeric = reverse linear extension

    def rec(pos: int):
        if pos == m:
            yield tuple(n)
            return
        i = order[pos]
        ub = top
        for j in poset.above[i]:
            if n[j] < ub:
                ub = n[j]
        for v in range(ub + 1):
            n[i] = v
            yield from rec(pos + 1)
        n[i] = 0

    yield from rec(0)


def order_filters(a: int, b: int) -> int:
    return sum(1 for _ in _cone(gap_poset(a, b), 1))


def _q_form(poset: GapPoset, n: tuple[int, ...]) -> int:
    total = 0
    km = poset.kmat
    for i, ni in enumerate(n):
        if ni:
            row = km[i]
            for j, nj in enumerate(n):
                if nj and row[j]:
                    total += row[j] * ni * nj
    return total


def _pg_exponents(poset: GapPoset, n: tuple[int, ...], rank: int | None = None) -> tuple[tuple[int, int], ...]:
    e: Counter[int] = Counter()
    for i, (ia, ib, iab) in enumerate(poset.shift):
        ng = n[i]
        e[ng - (n[iab] if iab >= 0 else 0)] += 1
        e[ng - (n[ia] if ia >= 0 else 0)] -= 1
        e[ng - (n[ib] if ib >= 0 else 0)] -= 1
    if rank is not None:
        e[rank] += 1
        e[rank - n[-1]] -= 1          # gaps[-1] == f
    return tuple(sorted((k, v) for k, v in e.items() if k > 0 and v != 0))


# --------------------------------------------------------------------------
# V1 / V2 objects
# --------------------------------------------------------------------------

def _validate_degree(D) -> int:
    if type(D) is not int or not 0 <= D <= MAX_DEGREE:
        raise HjoHold("DEGREE_OUT_OF_RANGE")
    return D


@lru_cache(maxsize=None)
def _filter_data(a: int, b: int):
    """Order filters with a published guarantee and CHECKED implementation guard.

    Write C(F,G) for the nonsymmetric kernel sum computed by bform below.
    For n = sum_v 1_{F_v}, Q(n + 1_G) - Q(n) equals
    C(G,G) + sum_v [C(F_v,G) + C(G,F_v)].
    Huang, arXiv:2604.13238, Theorem 1.1 gives C(G,G) >= 1 for nonempty
    filters. Theorem 1.2 gives nonnegative cross terms for ALL filter pairs.
    The paper's symmetric B is (C(F,G) + C(G,F))/2, not bform alone.
    Hence Q strictly increases along nonempty filter chains and pruning
    at Q > D is exact. Runtime checks on the nested pairs used by this
    traversal are retained as implementation guards, not novelty claims.
    """
    poset = _gap_poset(a, b)
    m = len(poset.gaps)
    km = poset.kmat
    filters = [tuple(i for i in range(m) if n[i]) for n in _cone(poset, 1)]
    filters = [f for f in filters if f]

    def bform(F, G):
        return sum(km[i][j] for i in F for j in G)

    diag = [bform(F, F) for F in filters]
    sets = [frozenset(F) for F in filters]
    sub = [[j for j, G in enumerate(sets) if G <= F] for F in sets]
    for i, F in enumerate(filters):
        for j in sub[i]:
            if bform(F, filters[j]) + bform(filters[j], F) < 0:
                raise HjoHold("MONOTONE_PRUNING_PRECONDITION_FAILED")
    if any(v < 1 for v in diag):
        raise HjoHold("MONOTONE_PRUNING_PRECONDITION_FAILED")
    return filters, diag, sub


def _cone_below(poset: GapPoset, D: int):
    """Yield (n, Q(n)) for every cone vector with Q(n) <= D, by exact pruning."""
    filters, diag, sub = _filter_data(poset.a, poset.b)
    km = poset.kmat
    m = len(poset.gaps)
    n = [0] * m
    yield tuple(n), 0

    def rec(last: int, qn: int):
        for j in (range(len(filters)) if last < 0 else sub[last]):
            G = filters[j]
            inc = diag[j]
            for g in G:
                row = km[g]
                inc += sum(row[h] * n[h] for h in range(m) if n[h])
                inc += sum(km[h][g] * n[h] for h in range(m) if n[h])
            nq = qn + inc
            if nq > D:
                continue
            for g in G:
                n[g] += 1
            yield tuple(n), nq
            yield from rec(j, nq)
            for g in G:
                n[g] -= 1

    yield from rec(-1, 0)


def z_series(a: int, b: int, D: int) -> list[int]:
    """Z_{a,b}(q) = sum_{n in C} P_G(n) q^{Q(n)} mod q^{D+1}  (paper eq. 1.10)."""
    poset = gap_poset(a, b)
    D = _validate_degree(D)
    out = [0] * (D + 1)
    for n, qn in _cone_below(poset, D):
        if n[-1] * n[-1] > poset.delta * qn:          # (1.11), re-checked live
            raise HjoHold("POSITIVITY_BOUND_VIOLATED")
        term = _poch_exponent_series(_pg_exponents(poset, n), D - qn)
        for k, c in enumerate(term):
            out[qn + k] += c
    return out


def _z_series_bruteforce(a: int, b: int, D: int) -> list[int]:
    """Unpruned reference (slow) used by tests to validate the pruned walk."""
    poset = gap_poset(a, b)
    out = [0] * (D + 1)
    for n in _cone(poset, math.isqrt(poset.delta * D)):
        qn = _q_form(poset, n)
        if qn <= D:
            term = _poch_exponent_series(_pg_exponents(poset, n), D - qn)
            for k, c in enumerate(term):
                out[qn + k] += c
    return out


def rho(a: int, b: int, m: int) -> int:
    d = a + b
    r = (a * m) % d
    return min(a, b, min(r, d - r)) - 1 + (1 if m % d == 0 else 0)


def p_series(a: int, b: int, D: int) -> list[int]:
    """P_{a,b}(q) = prod_{m>=1} (1 - q^m)^{-rho(m)} mod q^{D+1}  (eq. 1.13)."""
    _validate_pair(a, b, bound=40)
    D = _validate_degree(D)
    s = [1] + [0] * D
    for m in range(1, D + 1):
        r = rho(a, b, m)
        if r < 0:
            raise HjoHold("RHO_NEGATIVE")
        for _ in range(r):
            s = _over_1mqk(s, m, D)
    return s


def n_bivariate(a: int, b: int, rank: int) -> dict[int, list[int]]:
    """N_{a,b;N}(q,t) as {t-power |n|: exact polynomial in q}  (eq. 1.9)."""
    poset = gap_poset(a, b)
    if type(rank) is not int or not 0 <= rank <= MAX_RANK:
        raise HjoHold("RANK_OUT_OF_RANGE")
    acc: dict[int, list[int]] = {}
    for n in _cone(poset, rank):
        qn = _q_form(poset, n)
        poly = [0] * qn + list(_poch_poly_cached(_pg_exponents(poset, n, rank)))
        if any(c < 0 for c in poly):
            raise HjoHold("GAUSSIAN_MULTINOMIAL_NOT_POSITIVE")
        size = sum(n)
        cur = acc.setdefault(size, [0])
        if len(cur) < len(poly):
            cur.extend([0] * (len(poly) - len(cur)))
        for k, c in enumerate(poly):
            cur[k] += c
    return {k: _trim(v) for k, v in sorted(acc.items())}


def f_polynomial(a: int, b: int, rank: int) -> list[int]:
    """F_N(q) = N_{a,b;N}(q, 1)  (eq. 1.10)."""
    total = [0]
    for poly in n_bivariate(a, b, rank).values():
        if len(total) < len(poly):
            total.extend([0] * (len(poly) - len(total)))
        for k, c in enumerate(poly):
            total[k] += c
    return _trim(total)


def balanced_profile(a: int, b: int) -> tuple[int, ...]:
    _validate_pair(a, b, bound=40)
    return tuple((i + 1) * b // a - i * b // a for i in range(a))


def _profile_points(c: tuple[int, ...], budget: int) -> list[tuple[int, ...]]:
    """All m in Z_{>=0}^r with m_{i+1} <= m_i + c_i (cyclic) and |m| <= budget."""
    r = len(c)
    pts: list[tuple[int, ...]] = []
    cur = [0] * r

    def rec(i: int, used: int):
        if i == r:
            if cur[0] <= cur[r - 1] + c[r - 1]:
                pts.append(tuple(cur))
            return
        ub = budget - used if i == 0 else min(budget - used, cur[i - 1] + c[i - 1])
        for v in range(ub + 1):
            cur[i] = v
            rec(i + 1, used + v)
        cur[i] = 0

    rec(0, 0)
    return pts


def cylindric_series(c: tuple[int, ...], bound: int, D: int) -> list[int]:
    """Volume generating function of cylindric partitions with profile c and
    entries <= bound, mod q^{D+1}.

    lambda^{(i)}_j >= lambda^{(i+1)}_{j+c_i} (indices mod r) is equivalent, for
    level counts m_i(v) = #{j : lambda^{(i)}_j >= v}, to m_{i+1}(v) <= m_i(v) + c_i;
    rows are partitions iff m(1) >= m(2) >= ... componentwise. Counted directly.
    """
    D = _validate_degree(D)
    if type(bound) is not int or not 0 <= bound <= MAX_RANK:
        raise HjoHold("RANK_OUT_OF_RANGE")
    if not c or any(type(x) is not int or x < 0 for x in c) or sum(c) == 0:
        raise HjoHold("PROFILE_INVALID")
    if bound == 0:
        return [1] + [0] * D
    levels = {v: _profile_points(c, D // v) for v in range(1, bound + 1)}
    # weight[v][m] = series counting chains m = m(v) >= m(v+1) >= ... >= m(bound)
    nxt: dict[tuple[int, ...], list[int]] | None = None
    for v in range(bound, 0, -1):
        cur: dict[tuple[int, ...], list[int]] = {}
        for m in levels[v]:
            s = sum(m)
            if s > D:
                continue
            base = [0] * (D + 1)
            if nxt is None:
                base[s] = 1
            else:
                room = D - s
                for mp, w in nxt.items():
                    if sum(mp) <= min(s, room) and all(x <= y for x, y in zip(mp, m)):
                        for k in range(0, room + 1):
                            if w[k]:
                                base[s + k] += w[k]
            cur[m] = base
        nxt = cur
    out = [0] * (D + 1)
    for w in (nxt or {}).values():
        for k, x in enumerate(w):
            out[k] += x
    return out


# --------------------------------------------------------------------------
# V5: HJO Thm 1.2 point counts — formula vs brute force over F_q
# --------------------------------------------------------------------------

def quot_formula_counts(a: int, b: int, rank: int, q: int, m_max: int) -> list[int]:
    """#Quot_m^R(F_q[[T]]^N) for m = 0..m_max from
    Z(t) = q^{N^2 delta} t^{N delta} N_{a,b;N}(1/q, 1/t) / prod_{i<N} (1 - q^i t)."""
    poset = gap_poset(a, b)
    if type(q) is not int or q not in CENSUS_FIELDS or type(m_max) is not int or not 0 <= m_max <= 12:
        raise HjoHold("FIELD_OR_RANGE_INVALID")
    return _quot_formula_at(n_bivariate(a, b, rank), poset.delta, rank, q, m_max)


def _quot_formula_at(biv: dict[int, list[int]], delta: int, rank: int, L: int, m_max: int) -> list[int]:
    """Coefficients t^0..t^m_max of the Thm 1.2 series at the integer L >= 1.

    At a prime power L this is a point count; at any other L it is only the
    value of a polynomial, which is all the interpolation in V8 needs."""
    x = Fraction(1, L)
    top = rank * delta
    poly_t = [Fraction(0)] * (top + 1)
    for size, poly in biv.items():
        poly_t[top - size] += _eval(poly, x)
    scale = L ** (rank * rank * delta)
    series = [c * scale for c in poly_t[: m_max + 1]] + [Fraction(0)] * max(0, m_max + 1 - len(poly_t))
    for i in range(rank):
        r = L ** i
        for k in range(1, m_max + 1):
            series[k] += r * series[k - 1]
    if any(c.denominator != 1 for c in series):
        raise HjoHold("FORMULA_NOT_INTEGRAL")
    return [int(c) for c in series]


def _interpolate(points: list[tuple[int, int]]) -> list[Fraction]:
    """The unique polynomial of degree < len(points) through the points, as exact
    coefficients low -> high (trailing zeros trimmed). Newton divided differences."""
    xs = [Fraction(x) for x, _ in points]
    if not xs or len(set(xs)) != len(xs):
        raise HjoHold("INTERPOLATION_NODES_INVALID")
    coef = [Fraction(y) for _, y in points]
    n = len(xs)
    for j in range(1, n):
        for i in range(n - 1, j - 1, -1):
            coef[i] = (coef[i] - coef[i - 1]) / (xs[i] - xs[i - j])
    poly = [Fraction(0)]
    for i in range(n - 1, -1, -1):          # Horner on the Newton form
        nxt = [Fraction(0)] * (len(poly) + 1)
        for k, c in enumerate(poly):
            nxt[k + 1] += c
            nxt[k] -= c * xs[i]
        nxt[0] += coef[i]
        poly = nxt
    while len(poly) > 1 and poly[-1] == 0:
        poly.pop()
    return poly


def quot_formula_polynomials(a: int, b: int, rank: int, m_max: int, *, extra: int = 3) -> list[list[int]]:
    """The colength-m coefficient of the Thm 1.2 series as an integer polynomial
    in q (low -> high), for m = 0..m_max, recovered by exact interpolation.

    That coefficient is sum_j u_j(L) h_{m-j}(1, L, ..., L^{N-1}) with
    u_j(L) = L^{N^2 delta} n_{N delta - j}(1/L), where n_s is the t^s part of
    N_{a,b;N}. If no n_s has degree above N^2 delta (checked here), it is a
    polynomial of degree at most B_m = N^2 delta + (N-1) m, so B_m + 1 values fix
    it. It is interpolated through B_{m_max} + 1 + extra values at L = 2, 3, ...
    and must come out with degree <= B_m: the surplus points confirm the degree.
    """
    poset = gap_poset(a, b)
    if type(rank) is not int or not 1 <= rank <= MAX_RANK:
        raise HjoHold("RANK_OUT_OF_RANGE")
    if type(m_max) is not int or not 0 <= m_max <= 12 or type(extra) is not int or not 1 <= extra <= 8:
        raise HjoHold("COLENGTH_RANGE_INVALID")
    biv = n_bivariate(a, b, rank)
    square = rank * rank * poset.delta
    if max(len(poly) - 1 for poly in biv.values()) > square:
        raise HjoHold("FORMULA_DEGREE_PRECONDITION_FAILED")
    nodes = range(2, square + (rank - 1) * m_max + 3 + extra)
    values = [_quot_formula_at(biv, poset.delta, rank, L, m_max) for L in nodes]
    out = []
    for m in range(m_max + 1):
        poly = _interpolate([(L, v[m]) for L, v in zip(nodes, values)])
        if len(poly) - 1 > square + (rank - 1) * m or any(c.denominator != 1 for c in poly):
            raise HjoHold("FORMULA_NOT_A_POLYNOMIAL_WITHIN_BOUND")
        out.append([int(c) for c in poly])
    return out


@dataclass(frozen=True)
class GaloisField:
    """GF(q) as lookup tables on the codes 0..q-1. Code e stands for the
    polynomial sum_i d_i x^i over F_p, d_i the base-p digits of e, taken modulo
    the monic `modulus`; for a prime q the tables are plain arithmetic mod q."""
    q: int
    p: int
    modulus: tuple[int, ...]
    add: tuple[tuple[int, ...], ...]
    sub: tuple[tuple[int, ...], ...]
    mul: tuple[tuple[int, ...], ...]
    inv: tuple[int, ...]               # inv[0] = 0 is a placeholder


def galois_field(q: int) -> GaloisField:
    if type(q) is not int or q not in CENSUS_FIELDS:
        raise HjoHold("FIELD_ORDER_UNSUPPORTED")
    return _galois_field(q)


@lru_cache(maxsize=None)
def _galois_field(q: int) -> GaloisField:
    p, modulus = GF_MODULI.get(q, (q, (0, 1)))
    k = len(modulus) - 1
    if p ** k != q or modulus[-1] != 1:
        raise HjoHold("FIELD_MODULUS_INVALID")
    digits = [tuple((e // p ** i) % p for i in range(k)) for e in range(q)]
    code = {d: e for e, d in enumerate(digits)}

    def times(u: int, v: int) -> int:
        prod = [0] * (2 * k - 1)
        for i, x in enumerate(digits[u]):
            for j, y in enumerate(digits[v]):
                prod[i + j] = (prod[i + j] + x * y) % p
        for top in range(2 * k - 2, k - 1, -1):
            c = prod[top]
            if c:
                for i, mc in enumerate(modulus):
                    prod[top - k + i] = (prod[top - k + i] - c * mc) % p
        return code[tuple(prod[:k])]

    def digitwise(sign: int) -> tuple[tuple[int, ...], ...]:
        return tuple(tuple(code[tuple((x + sign * y) % p for x, y in zip(digits[u], digits[v]))]
                           for v in range(q)) for u in range(q))

    mul = tuple(tuple(times(u, v) for v in range(q)) for u in range(q))
    inv = [0] * q
    for u in range(1, q):
        units = [v for v in range(1, q) if mul[u][v] == 1]
        if len(units) != 1:          # only a reducible modulus leaves a non-unit
            raise HjoHold("FIELD_MODULUS_REDUCIBLE")
        inv[u] = units[0]
    return GaloisField(q, p, modulus, digitwise(1), digitwise(-1), mul, tuple(inv))


def _solve_affine(rows: list[list[int]], rhs: list[int], nvars: int, field: GaloisField):
    """All solutions x in GF(q)^nvars of rows @ x = rhs (Gaussian elimination)."""
    sub, mul, inv = field.sub, field.mul, field.inv
    mat = [list(r) + [v] for r, v in zip(rows, rhs)]
    pivots: list[int] = []
    r = 0
    for col in range(nvars):
        piv = next((i for i in range(r, len(mat)) if mat[i][col]), None)
        if piv is None:
            continue
        mat[r], mat[piv] = mat[piv], mat[r]
        scale = mul[inv[mat[r][col]]]
        mat[r] = [scale[v] for v in mat[r]]
        for i in range(len(mat)):
            if i != r and mat[i][col]:
                fct = mul[mat[i][col]]
                mat[i] = [sub[vi][fct[vr]] for vi, vr in zip(mat[i], mat[r])]
        pivots.append(col)
        r += 1
    for i in range(r, len(mat)):
        if mat[i][-1]:
            return
    free = [c for c in range(nvars) if c not in pivots]
    for values in _cartesian(range(field.q), repeat=len(free)):
        x = [0] * nvars
        for c, v in zip(free, values):
            x[c] = v
        for i, col in enumerate(pivots):
            acc = mat[i][-1]
            for c in free:
                acc = sub[acc][mul[mat[i][c]][x[c]]]
            x[col] = acc
        yield x


def quot_colength_limit(delta: int, rank: int, field: int, requested: int) -> int:
    """Interactive colength ceiling chosen from measured CPU cost (2 vCPU Space)."""
    if type(requested) is not int or requested < 0:
        raise HjoHold("COLENGTH_RANGE_INVALID")
    if rank == 1:
        cap = 4 if delta <= 6 else 3
    else:
        cap = (3 if delta <= 2 else 2) if field == 2 else (2 if delta <= 2 else 1)
        if delta >= 6:
            cap = 1
    return min(requested, cap)


def quot_bruteforce_counts(a: int, b: int, rank: int, q: int, m_max: int, *, budget: int = 400_000) -> list[int]:
    """Count R = F_q[[T^a,T^b]]-submodules of F_q[[T]]^N of colength m, m = 0..m_max.

    Every such submodule contains T^{m+c} F_q[[T]]^N (c = conductor = (a-1)(b-1)), so
    we enumerate subspaces of (F_q[T]/T^K)^N, K = m + c, in reduced echelon form by
    descending basis position; T^a, T^b-stability of a new basis vector is a LINEAR
    condition in its free coordinates given the higher part, so every solution is
    enumerated explicitly. No formula from the papers is used.
    """
    poset = gap_poset(a, b)
    if type(q) is not int or q not in FIELDS or type(rank) is not int or not 1 <= rank <= 2:
        raise HjoHold("FIELD_OR_RANK_INVALID")
    if type(m_max) is not int or not 0 <= m_max <= 8:
        raise HjoHold("COLENGTH_RANGE_INVALID")
    field = _galois_field(q)
    work = [0]
    return [_echelon_count(a, b, rank, field, m, 2 * poset.delta, work, budget)
            for m in range(m_max + 1)]


def quot_bruteforce_census(a: int, b: int, rank: int, q: int, colength_ceiling: int, *, budget: int) -> dict:
    """Offline census over GF(q), q any prime power <= 9: the counts of
    quot_bruteforce_counts for colengths 0, 1, ... up to colength_ceiling, stopping
    early at the first colength that would take the series past `budget` steps.

    That colength's partial count is discarded, never returned. `cumulative_work`
    gives, after each colength returned, the steps spent so far (the unit of
    `budget`); `work_steps` is its last entry.
    """
    poset = gap_poset(a, b)
    if type(q) is not int or q not in CENSUS_FIELDS or type(rank) is not int or not 1 <= rank <= 2:
        raise HjoHold("FIELD_OR_RANK_INVALID")
    if type(colength_ceiling) is not int or not 0 <= colength_ceiling <= 8:
        raise HjoHold("COLENGTH_RANGE_INVALID")
    if type(budget) is not int or budget < 1:
        raise HjoHold("BUDGET_INVALID")
    field = _galois_field(q)
    work = [0]
    counts: list[int] = []
    cumulative: list[int] = []
    stop = "COLENGTH_CEILING"
    for m in range(colength_ceiling + 1):
        try:
            counts.append(_echelon_count(a, b, rank, field, m, 2 * poset.delta, work, budget))
        except HjoHold as exc:
            if str(exc) != "BRUTE_FORCE_BUDGET_EXCEEDED":
                raise
            stop = "WORK_CAP"
            break
        cumulative.append(work[0])
    return {"counts": counts, "cumulative_work": cumulative,
            "work_steps": cumulative[-1] if cumulative else 0, "stop": stop}


def _echelon_count(a: int, b: int, rank: int, field: GaloisField, m: int, conductor: int,
                   work: list[int], budget: int) -> int:
    """#subspaces of (GF(q)[T]/T^K)^N, K = m + conductor, of codimension m that are
    stable under T^a and T^b. work[0] is shared by every colength of one series."""
    K = m + conductor
    dim = rank * K
    shifts = (a * rank, b * rank)
    sub, mul = field.sub, field.mul
    neg = sub[0]
    basis: dict[int, list[int]] = {}
    nonlead: list[int] = []
    total = [0]

    def reduce(vec: list[int]) -> list[int]:
        v = list(vec)
        for lead in sorted(basis):
            c = v[lead]
            if c:
                w = basis[lead]
                scale = mul[c]
                for i in range(lead, dim):
                    if w[i]:
                        v[i] = sub[v[i]][scale[w[i]]]
        return v

    def shifted(vec: list[int], s: int) -> list[int]:
        out = [0] * dim
        for i in range(dim - s):
            out[i + s] = vec[i]
        return out

    def rec(p: int, codim: int):
        work[0] += 1
        if work[0] > budget:
            raise HjoHold("BRUTE_FORCE_BUDGET_EXCEEDED")
        if codim > m:
            return
        if p < 0:
            if codim == m:
                total[0] += 1
            return
        # option A: p is not a pivot position
        nonlead.append(p)
        rec(p - 1, codim + 1)
        nonlead.pop()
        # option B: p is the pivot of w_p = e_p + sum_{j in nonlead, j > p} x_j e_j
        free = [j for j in nonlead if j > p]
        e_p = [0] * dim
        e_p[p] = 1
        rows: list[list[int]] = []
        rhs: list[int] = []
        for s in shifts:
            r0 = reduce(shifted(e_p, s))
            cols = [reduce(shifted([1 if i == j else 0 for i in range(dim)], s)) for j in free]
            for i in range(dim):
                if r0[i] or any(col[i] for col in cols):
                    rows.append([col[i] for col in cols])
                    rhs.append(neg[r0[i]])
        for x in _solve_affine(rows, rhs, len(free), field):
            w = list(e_p)
            for j, xv in zip(free, x):
                w[j] = xv
            basis[p] = w
            rec(p - 1, codim)
            del basis[p]

    rec(dim - 1, 0)
    return total[0]


# --------------------------------------------------------------------------
# V6: HJO Thm 1.4 — commuting nilpotent pairs with A^a = B^b over F_q
# --------------------------------------------------------------------------

def _partitions(n: int, maxpart: int | None = None):
    if maxpart is None:
        maxpart = n
    if n == 0:
        yield ()
        return
    for k in range(min(n, maxpart), 0, -1):
        for rest in _partitions(n - k, k):
            yield (k,) + rest


def _matmul(x, y, q):
    n = len(x)
    return tuple(
        tuple(sum(x[i][k] * y[k][j] for k in range(n)) % q for j in range(n))
        for i in range(n)
    )


def _matpow(x, e, q):
    n = len(x)
    out = tuple(tuple(1 if i == j else 0 for j in range(n)) for i in range(n))
    for _ in range(e):
        out = _matmul(out, x, q)
    return out


def _rank_mod(rows: list[list[int]], q: int) -> int:
    mat = [list(r) for r in rows]
    rank = 0
    cols = len(mat[0]) if mat else 0
    for c in range(cols):
        piv = next((i for i in range(rank, len(mat)) if mat[i][c] % q), None)
        if piv is None:
            continue
        mat[rank], mat[piv] = mat[piv], mat[rank]
        inv = pow(mat[rank][c], q - 2, q)
        mat[rank] = [(v * inv) % q for v in mat[rank]]
        for i in range(len(mat)):
            if i != rank and mat[i][c] % q:
                f = mat[i][c]
                mat[i] = [(vi - f * vr) % q for vi, vr in zip(mat[i], mat[rank])]
        rank += 1
    return rank


def nilpotent_pair_terms(a: int, b: int, q: int, n_max: int) -> list[Fraction]:
    """|NC_n^{a,b}(F_q)| / |GL_n(F_q)| for n = 0..n_max by orbit-stabilizer:
    sum over Jordan types J of #{B in C(J): B nilpotent, B^b = J^a} / |Aut(J)|."""
    _validate_pair(a, b)
    if q not in FIELDS or type(n_max) is not int or not 0 <= n_max <= (4 if q == 2 else 3):
        raise HjoHold("FIELD_OR_SIZE_INVALID")
    terms = [Fraction(1)]
    for n in range(1, n_max + 1):
        acc = Fraction(0)
        for lam in _partitions(n):
            J = [[0] * n for _ in range(n)]
            start = 0
            for part in lam:
                for i in range(part - 1):
                    J[start + i][start + i + 1] = 1
                start += part
            J = tuple(tuple(r) for r in J)
            # centralizer basis: solve J X - X J = 0 over F_q
            eqs = []
            for i in range(n):
                for j in range(n):
                    row = [0] * (n * n)
                    for k in range(n):
                        row[k * n + j] += J[i][k]
                        row[i * n + k] -= J[k][j]
                    eqs.append([v % q for v in row])
            basis = _nullspace(eqs, n * n, q)
            ja = _matpow(J, a, q)
            ok = aut = 0
            zero = tuple(tuple(0 for _ in range(n)) for _ in range(n))
            for coeffs in _cartesian(range(q), repeat=len(basis)):
                flat = [0] * (n * n)
                for c, vec in zip(coeffs, basis):
                    if c:
                        for t in range(n * n):
                            flat[t] = (flat[t] + c * vec[t]) % q
                B = tuple(tuple(flat[i * n:(i + 1) * n]) for i in range(n))
                if _rank_mod([list(r) for r in B], q) == n:
                    aut += 1
                    continue
                if _matpow(B, n, q) == zero and _matpow(B, b, q) == ja:
                    ok += 1
            acc += Fraction(ok, aut)
        terms.append(acc)
    return terms


def _nullspace(rows: list[list[int]], nvars: int, q: int) -> list[list[int]]:
    mat = [list(r) for r in rows]
    pivots = []
    r = 0
    for col in range(nvars):
        piv = next((i for i in range(r, len(mat)) if mat[i][col] % q), None)
        if piv is None:
            continue
        mat[r], mat[piv] = mat[piv], mat[r]
        inv = pow(mat[r][col], q - 2, q)
        mat[r] = [(v * inv) % q for v in mat[r]]
        for i in range(len(mat)):
            if i != r and mat[i][col] % q:
                f = mat[i][col]
                mat[i] = [(vi - f * vr) % q for vi, vr in zip(mat[i], mat[r])]
        pivots.append(col)
        r += 1
    free = [c for c in range(nvars) if c not in pivots]
    basis = []
    for fcol in free:
        vec = [0] * nvars
        vec[fcol] = 1
        for i, pcol in enumerate(pivots):
            vec[pcol] = (-mat[i][fcol]) % q
        basis.append(vec)
    return basis


def groupoid_prediction(a: int, b: int, q: int, D: int = 60) -> float:
    """P_{a,b}(1/q) / (1/q;1/q)_inf, the Thm 1.4 + Cor 1.2 limit (float, tail < q^-D)."""
    coeffs = p_series(a, b, D)
    x = 1.0 / q
    p_val = sum(c * x ** k for k, c in enumerate(coeffs))
    euler = 1.0
    for i in range(1, 200):
        euler *= 1.0 - x ** i
    return p_val / euler


# --------------------------------------------------------------------------
# Published golden values (transcribed from arXiv:2609.20567v2 §1.2 and §10)
# --------------------------------------------------------------------------

GOLDEN = {
    "F_2(2,3)": [1, 1, 1, 0, 1],
    "F_1(4,5)": [1, 3, 3, 3, 2, 1, 1],
    "F_2(4,5)": [1, 3, 6, 9, 13, 14, 17, 16, 17, 15, 15, 12, 13, 9, 9, 6, 6, 4, 4, 2, 2, 1, 1, 0, 1],
    "filters(4,5)": 14,
    "F_2(1)(4,5)": 196,
    "gaps(4,5)": [1, 2, 3, 6, 7, 11],
    "profile(4,5)": [1, 1, 1, 2],
    "profile(5,7)": [1, 1, 2, 1, 2],
}


# --------------------------------------------------------------------------
# Orchestration + sealed receipt
# --------------------------------------------------------------------------

def _canonical(record: dict) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def seal(record: dict) -> dict:
    body = {k: v for k, v in record.items() if k != "sha256"}
    return {**body, "sha256": hashlib.sha256(DOMAIN + _canonical(body)).hexdigest()}


def verify(a: int, b: int, *, degree: int = 24, rank: int = 2, field: int = 2,
           quot_m: int = 3, nil_n: int = 3, include_finite_field: bool = True,
           budget: int = 150_000) -> dict:
    """Run V1–V6 for one coprime pair; raises HjoHold on any mismatch."""
    a, b = _validate_pair(a, b)
    poset = gap_poset(a, b)
    degree = _validate_degree(degree)
    if type(rank) is not int or not 1 <= rank <= 3:
        raise HjoHold("RANK_OUT_OF_RANGE")
    checks: list[dict] = []

    z = z_series(a, b, degree)
    p = p_series(a, b, degree)
    checks.append({"id": "V1", "statement": "Z_{a,b} == P_{a,b} (Cor 1.2)", "degree": degree,
                   "status": "MATCH" if z == p else "MISMATCH"})
    if z != p:
        raise HjoHold("V1_MISMATCH")

    c = balanced_profile(a, b)
    fN = f_polynomial(a, b, rank)
    deg_f = len(fN) - 1
    D2 = min(MAX_DEGREE, max(degree, deg_f + 4))
    cyl = cylindric_series(c, rank, D2)
    lhs = (fN + [0] * (D2 + 1))[: D2 + 1]
    rhs = _mul(_poch(rank), cyl, D2)
    checks.append({"id": "V2", "statement": "F_N == (q;q)_N C_{c,<=N} (Thm 1.1)", "rank": rank,
                   "degree": D2, "deg_F_N": deg_f, "status": "MATCH" if lhs == rhs else "MISMATCH"})
    if lhs != rhs:
        raise HjoHold("V2_MISMATCH")

    cat = rational_catalan(a, b)
    filters = order_filters(a, b)
    f_at_1 = sum(fN)
    v4 = filters == cat and f_at_1 == cat ** rank
    checks.append({"id": "V4", "statement": "#filters == Cat(a,b); F_N(1) == Cat^N",
                   "catalan": cat, "filters": filters, "F_N(1)": f_at_1,
                   "status": "MATCH" if v4 else "MISMATCH"})
    if not v4:
        raise HjoHold("V4_MISMATCH")

    if (a, b) == (4, 5) or (a, b) == (2, 3):
        golden_ok = True
        if (a, b) == (4, 5):
            golden_ok = (f_polynomial(4, 5, 1) == GOLDEN["F_1(4,5)"]
                         and f_polynomial(4, 5, 2) == GOLDEN["F_2(4,5)"]
                         and list(poset.gaps) == GOLDEN["gaps(4,5)"]
                         and list(c) == GOLDEN["profile(4,5)"])
        else:
            golden_ok = f_polynomial(2, 3, 2) == GOLDEN["F_2(2,3)"]
        checks.append({"id": "V3", "statement": "published golden values reproduced",
                       "status": "MATCH" if golden_ok else "MISMATCH"})
        if not golden_ok:
            raise HjoHold("V3_GOLDEN_MISMATCH")

    if include_finite_field:
        if field not in FIELDS:
            raise HjoHold("FIELD_INVALID")
        for N in (1, 2):
            mm = quot_colength_limit(poset.delta, N, field, quot_m)
            formula = quot_formula_counts(a, b, N, field, mm)
            row = {"id": f"V5.N{N}", "statement": f"#Quot_m(F_{field}[[T]]^{N}) brute force == HJO Thm 1.2",
                   "field": field, "colength_max": mm, "formula": formula}
            try:
                brute = quot_bruteforce_counts(a, b, N, field, mm, budget=budget)
            except HjoHold as exc:
                if str(exc) != "BRUTE_FORCE_BUDGET_EXCEEDED":
                    raise
                checks.append({**row, "bruteforce": None, "status": "NOT_RUN_BUDGET"})
                continue
            checks.append({**row, "bruteforce": brute,
                           "status": "MATCH" if formula == brute else "MISMATCH"})
            if formula != brute:
                raise HjoHold("V5_MISMATCH")
        nmax = min(nil_n, 4 if field == 2 else 3)
        terms = nilpotent_pair_terms(a, b, field, nmax)
        partial = sum(terms)
        limit = groupoid_prediction(a, b, field)
        consistent = float(partial) < limit
        checks.append({"id": "V6", "statement": "groupoid partial sum < Thm 1.4 limit (consistency only)",
                       "field": field, "n_max": nmax,
                       "terms": [f"{t.numerator}/{t.denominator}" for t in terms],
                       "partial_sum": round(float(partial), 9), "predicted_limit": round(limit, 9),
                       "status": "CONSISTENT" if consistent else "INCONSISTENT"})
        if not consistent:
            raise HjoHold("V6_INCONSISTENT")

    record = {
        "schema": SCHEMA, "pair": [a, b], "d": poset.d, "delta": poset.delta, "f": poset.f,
        "gaps": list(poset.gaps), "profile": list(c), "z_coefficients": z,
        "F_N": fN, "checks": checks,
        "sources": {"paper": PAPER, "hjo": HJO_PAPER, "lean_repo": LEAN_REPO,
                    "lean_revision_observed": LEAN_REVISION_OBSERVED},
        "lean_certificate_replayed": False,
        "new_theorem_proved": False,
        "finite_check_only": True,
        "historical_claim": "NOT_ESTABLISHED",
        "signature_verified": False,
    }
    return seal(record)


# --------------------------------------------------------------------------
# Geometry helpers for the 3D scene (illustrative objects, exact data)
# --------------------------------------------------------------------------

def cover_relations(a: int, b: int) -> list[tuple[int, int]]:
    """Cover relations g < h of the gap poset (h - g in {a, b}, both gaps)."""
    poset = gap_poset(a, b)
    gs = set(poset.gaps)
    return [(g, g + s) for g in poset.gaps for s in (a, b) if g + s in gs]


def sample_cylindric(c: tuple[int, ...], bound: int, volume: int, seed: int = 0) -> list[list[int]]:
    """One cylindric partition (rows as partitions) with entries <= bound and the
    given volume, chosen deterministically from the exhaustive list by seed."""
    if type(volume) is not int or not 0 <= volume <= 24 or type(bound) is not int or not 1 <= bound <= 4:
        raise HjoHold("SAMPLE_RANGE_INVALID")
    pts = _profile_points(tuple(c), volume)
    found: list[tuple[tuple[int, ...], ...]] = []

    def rec(chain: list[tuple[int, ...]], left: int):
        if len(found) >= 20_000:
            return
        if left == 0:
            found.append(tuple(chain))
            return
        if len(chain) == bound:
            return
        prev = chain[-1] if chain else None
        for m in pts:
            s = sum(m)
            if 0 < s <= left and (prev is None or all(x <= y for x, y in zip(m, prev))):
                chain.append(m)
                rec(chain, left - s)
                chain.pop()

    rec([], volume)
    if not found:
        raise HjoHold("NO_CYLINDRIC_PARTITION_OF_VOLUME")
    chain = found[seed % len(found)]
    rows = []
    for i in range(len(c)):
        depth = max((m[i] for m in chain), default=0)
        rows.append([sum(1 for m in chain if m[i] >= j) for j in range(1, depth + 1)])
    return rows
