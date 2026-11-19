# SPDX-License-Identifier: Apache-2.0
"""HJO Thm 1.2 census over GF(q), q in {2,3,4,5,7,8,9} -- research extension (2026-11-19).

Extends szl_khipu/hjo_loom.py:quot_bruteforce_counts (prime q only) to prime-power fields via
explicit add/mul tables. Brute force shares nothing with the formula except (a,b).
The formula side (HJO Thm 1.2 motive) is computed SYMBOLICALLY as an integer polynomial in L,
using hjo_loom.n_bivariate (HLO eq. 1.9), then evaluated at L=q.
Standard library only; loads hjo_loom.py by file path.
"""
from __future__ import annotations
import importlib.util, sys, json, time
from fractions import Fraction
from itertools import product
from pathlib import Path

KHIPU = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("hjo_loom", KHIPU / "szl_khipu/hjo_loom.py")
h = importlib.util.module_from_spec(_spec); sys.modules.setdefault("hjo_loom", h); _spec.loader.exec_module(h)

# ---------------- finite fields GF(p^k) as tables ----------------
IRRED = {4: (2, [1, 1, 1]), 8: (2, [1, 1, 0, 1]), 9: (3, [1, 0, 1])}  # low->high coeffs: x^2+x+1, x^3+x+1, x^2+1

class GF:
    def __init__(self, q: int):
        self.q = q
        if q in IRRED:
            p, f = IRRED[q]; k = len(f) - 1
        else:
            assert all(q % d for d in range(2, q)), q
            p, k, f = q, 1, None
        self.p, self.k = p, k
        def to_v(x): return [(x // p**i) % p for i in range(k)]
        def to_i(v): return sum(c * p**i for i, c in enumerate(v))
        def pmul(u, v):
            r = [0] * (2 * k - 1)
            for i, a in enumerate(u):
                for j, b in enumerate(v):
                    r[i + j] = (r[i + j] + a * b) % p
            if f is not None:
                for d in range(len(r) - 1, k - 1, -1):  # reduce by monic f
                    c = r[d]
                    if c:
                        for i in range(k + 1):
                            r[d - k + i] = (r[d - k + i] - c * f[i]) % p
            return r[:k]
        R = range(q)
        self.add = [[to_i([(a + b) % p for a, b in zip(to_v(x), to_v(y))]) for y in R] for x in R]
        self.neg = [to_i([(-a) % p for a in to_v(x)]) for x in R]
        self.sub = [[self.add[x][self.neg[y]] for y in R] for x in R]
        self.mul = [[to_i(pmul(to_v(x), to_v(y))) for y in R] for x in R]
        self.inv = [None] + [next(y for y in R if self.mul[x][y] == 1) for x in range(1, q)]
        # field axioms sanity (fail closed)
        for x in R:
            for y in R:
                assert self.mul[x][y] == self.mul[y][x] and self.add[x][y] == self.add[y][x]
                for z in R:
                    assert self.mul[x][self.add[y][z]] == self.add[self.mul[x][y]][self.mul[x][z]]
                    assert self.mul[self.mul[x][y]][z] == self.mul[x][self.mul[y][z]]
        assert sum(1 for x in range(1, q) if all(pow_(self, x, e) != 1 for e in range(1, q - 1))) >= 1  # has a generator

def pow_(F, x, e):
    r = 1
    for _ in range(e):
        r = F.mul[r][x]
    return r

class Budget(Exception):
    pass

def solve_affine(F, rows, rhs, nvars):
    sub, mul, inv = F.sub, F.mul, F.inv
    mat = [list(r) + [v] for r, v in zip(rows, rhs)]
    pivots = []; r = 0
    for col in range(nvars):
        piv = next((i for i in range(r, len(mat)) if mat[i][col]), None)
        if piv is None:
            continue
        mat[r], mat[piv] = mat[piv], mat[r]
        iv = inv[mat[r][col]]
        mat[r] = [mul[v][iv] for v in mat[r]]
        for i in range(len(mat)):
            if i != r and mat[i][col]:
                fct = mat[i][col]
                mat[i] = [sub[vi][mul[fct][vr]] for vi, vr in zip(mat[i], mat[r])]
        pivots.append(col); r += 1
    for i in range(r, len(mat)):
        if mat[i][-1]:
            return
    free = [c for c in range(nvars) if c not in pivots]
    for values in product(range(F.q), repeat=len(free)):
        x = [0] * nvars
        for c, v in zip(free, values):
            x[c] = v
        for i, col in enumerate(pivots):
            acc = mat[i][-1]
            for c in free:
                if mat[i][c] and x[c]:
                    acc = sub[acc][mul[mat[i][c]][x[c]]]
            x[col] = acc
        yield x

def brute_counts(a, b, rank, q, m_max, budget=10**9):
    """#R-submodules of F_q[[T]]^N of colength m (same echelon algorithm as hjo_loom, any GF(q))."""
    F = GF(q); sub, mul, neg = F.sub, F.mul, F.neg
    poset = h.gap_poset(a, b)
    conductor = 2 * poset.delta
    counts = []; work = [0]
    for m in range(m_max + 1):
        K = m + conductor; dim = rank * K
        shifts = (a * rank, b * rank)
        basis = {}; nonlead = []; total = [0]
        def reduce(vec):
            v = list(vec)
            for lead in sorted(basis):
                c = v[lead]
                if c:
                    w = basis[lead]
                    for i in range(lead, dim):
                        if w[i]:
                            v[i] = sub[v[i]][mul[c][w[i]]]
            return v
        def shifted(vec, s):
            out = [0] * dim
            for i in range(dim - s):
                out[i + s] = vec[i]
            return out
        def rec(p, codim):
            work[0] += 1
            if work[0] > budget:
                raise Budget("BRUTE_FORCE_BUDGET_EXCEEDED")
            if codim > m:
                return
            if p < 0:
                if codim == m:
                    total[0] += 1
                return
            nonlead.append(p); rec(p - 1, codim + 1); nonlead.pop()
            free = [j for j in nonlead if j > p]
            e_p = [0] * dim; e_p[p] = 1
            rows, rhs = [], []
            for s in shifts:
                r0 = reduce(shifted(e_p, s))
                cols = [reduce(shifted([1 if i == j else 0 for i in range(dim)], s)) for j in free]
                for i in range(dim):
                    if r0[i] or any(col[i] for col in cols):
                        rows.append([col[i] for col in cols]); rhs.append(neg[r0[i]])
            for x in solve_affine(F, rows, rhs, len(free)):
                w = list(e_p)
                for j, xv in zip(free, x):
                    w[j] = xv
                basis[p] = w; rec(p - 1, codim); del basis[p]
        rec(dim - 1, 0)
        counts.append(total[0])
    return counts, work[0]

# ---------------- HJO Thm 1.2, symbolic in L ----------------
def padd(x, y):
    n = max(len(x), len(y)); return h._trim([(x[i] if i < len(x) else 0) + (y[i] if i < len(y) else 0) for i in range(n)])

def thm12_polys(a, b, rank, m_max):
    """Coefficient of t^m in Z(t) = L^{N^2 d} t^{N d} N_{a,b;N}(1/L,1/t) / prod_{i<N}(1 - L^i t), as int polys in L."""
    d = h.gap_poset(a, b).delta
    biv = h.n_bivariate(a, b, rank)
    top = rank * d; S = rank * rank * d
    coeff = [[0] for _ in range(max(top, m_max) + 1)]
    for size, poly in biv.items():
        if len(poly) - 1 > S:
            raise ValueError("NOT_POLYNOMIAL_IN_L")
        rev = [0] * (S + 1)
        for k, c in enumerate(poly):
            rev[S - k] += c
        coeff[top - size] = padd(coeff[top - size], rev)
    series = [list(c) for c in coeff[: m_max + 1]]
    for i in range(rank):
        for k in range(1, m_max + 1):  # series[k] += L^i * series[k-1]
            series[k] = padd(series[k], [0] * i + series[k - 1])
    return [h._trim(s) for s in series]

def peval(poly, x):
    return sum(c * x**k for k, c in enumerate(poly))

def interpolate(xs, ys):
    """Unique polynomial of degree < len(xs) through the points, exact rational coefficients (low->high)."""
    n = len(xs); coeffs = [Fraction(0)] * n
    for i in range(n):
        basis = [Fraction(1)]; den = Fraction(1)
        for j in range(n):
            if j == i: continue
            basis = [Fraction(0)] + basis
            for k in range(len(basis) - 1):
                basis[k] -= xs[j] * basis[k + 1]
            den *= xs[i] - xs[j]
        for k in range(n):
            coeffs[k] += ys[i] * basis[k] / den
    while len(coeffs) > 1 and coeffs[-1] == 0:
        coeffs.pop()
    return coeffs
