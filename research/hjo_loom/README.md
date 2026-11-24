<!-- SPDX-License-Identifier: Apache-2.0
(c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173 -->

# HJO Loom — exact finite replays of the X^a = Y^b Rogers–Ramanujan theorems

Status: **MEASURED finite checks of published theorems.** Nothing here proves a new theorem,
replays the Lean certificate, or says anything about historical Andean knowledge.

A one-page account of the method, including how to rerun it, is in [METHOD.md](METHOD.md).

## What is checked, and by which independent route

Definitions are transcribed from Huang–Lau–Ono, *Rogers–Ramanujan identities from the geometry
of X^a = Y^b*, [arXiv:2609.20567v2](https://arxiv.org/abs/2609.20567) (eqs. 1.4–1.17), and
Huang–Jiang–Oblomkov, *Quot scheme of points on torus knot singularities*,
[arXiv:2608.16086v1](https://arxiv.org/abs/2608.16086). All arithmetic is exact (Python `int` /
`Fraction`), standard library only (`szl_khipu/hjo_loom.py`).

| Id | Statement | Independent route used here |
| --- | --- | --- |
| V1 | Z<sub>a,b</sub>(q) = P<sub>a,b</sub>(q) (HLO Cor 1.2; HJO Conj 1.7) | Sum over the order-preserving cone of the gap poset vs. the ρ-product, coefficientwise |
| V2 | F<sub>N</sub>(q) = (q;q)<sub>N</sub> C<sub>c,≤N</sub>(q) (HLO Thm 1.1) | Cylindric partitions counted **directly** (see below), not via the paper's q-difference equation |
| V3 | Published values: F<sub>1</sub>, F<sub>2</sub> for (4,5) (§10), F<sub>2</sub> for (2,3) (§1.2), profiles | Reproduced from the definitions |
| V4 | #order filters = rational Catalan; F<sub>N</sub>(1) = Cat(a,b)<sup>N</sup> | Direct enumeration |
| V5 | #Quot<sub>m</sub><sup>R</sup>(F<sub>q</sub>[[T]]<sup>N</sup>) = coefficient of the HJO Thm 1.2 motive at L = q | **Brute-force enumeration of submodules over F<sub>2</sub>, F<sub>3</sub>** |
| V6 | Groupoid volume of commuting nilpotent pairs with A<sup>a</sup> = B<sup>b</sup> (HJO Thm 1.4) | Orbit–stabilizer enumeration; partial sums only — **consistency, not verification** |
| V7 | V5 over GF(4), GF(5), GF(7), GF(8), GF(9) as well as F<sub>2</sub>, F<sub>3</sub> | The V5 enumeration at five more values of q (v2 certificate); it does not test the GF(p<sup>k</sup>) tables (see V7 below) |
| V8 | Each colength count is a polynomial in q (HJO Thm 1.2) | Exact interpolation of the formula at integer L; the brute-force counts, interpolated separately, give its coefficients once its degree is known |

### Three implementation facts that make this exact and fast

1. **Level-vector bijection (V2).** For a cylindric partition with profile c and entries ≤ N, put
   m<sub>i</sub>(v) = #{j : λ<sup>(i)</sup><sub>j</sub> ≥ v}. Then
   λ<sup>(i)</sup><sub>j</sub> ≥ λ<sup>(i+1)</sup><sub>j+c<sub>i</sub></sub> for all j iff
   m<sub>i+1</sub>(v) ≤ m<sub>i</sub>(v) + c<sub>i</sub> for all v, and rows are partitions iff
   m(1) ≥ m(2) ≥ … componentwise. So C<sub>c,≤N</sub> is a weighted count of descending chains of N
   lattice points in a cyclic polyhedron — enumerated directly.
2. **Monotone pruning (V1), published guarantee plus runtime checks.** Write
   C(F,G) = Σ<sub>i∈F,j∈G</sub> K(j−i), the implementation's `bform`.
   Each cone vector is a sum of indicators of descending nonempty order filters, and
   Q(n + 1<sub>G</sub>) − Q(n) = C(G,G) + Σ<sub>v</sub> [C(F<sub>v</sub>,G) + C(G,F<sub>v</sub>)].
   These inequalities are **established mathematics, not a new conjecture or discovery here**:
   Huang, *A quadratic form generalization of rational dinv*,
   [arXiv:2604.13238](https://arxiv.org/abs/2604.13238), Theorem 1.2 identifies the
   symmetric form on any two filters with a cross-dinv count, so the cross terms are
   nonnegative for **all** filter pairs, not just nested ones. Its D = E case is the
   Theorem 1.1 identity C(G,G) = Q(1<sub>G</sub>) = dinv(G), which is at least 1 for a
   nonempty filter. These statements are as formalized in
   [AxiomMath/quadratic-dinv](https://github.com/AxiomMath/quadratic-dinv)
   (`RationalDinv.bilinForm_eq_crossDinv`, statement marked author-verified) and
   [AxiomMath/HJO](https://github.com/AxiomMath/HJO) (`one_le_q_indicator`); both were read
   here, not replayed, and the theorem numbering is the author's. Our earlier framing of this precondition as
   possibly open was wrong, corrected by the author (personal communication, 2026-11-18).
   The paper's symmetric form is
   B(F,G) = [C(F,G) + C(G,F)] / 2, so the implementation's cross term is 2B(F,G).
   Thus Q increases strictly along chains and pruning at Q > D is exact.
   The engine retains its per-pair checks and fails closed with
   `MONOTONE_PRUNING_PRECONDITION_FAILED`; those checks protect the implementation,
   not establish the theorem. Tests compare pruned and unpruned enumeration.
   Theorem 1.3 also gives the cone bound ||n||∞ ≤ √(D|G|) when Q(n) ≤ D; the symmetrised
   form of Q is *not* positive definite for a ≥ 4, and ambient-space positive definiteness
   is not needed.
3. **Linear echelon enumeration (V5).** Every R-submodule of colength m contains
   T<sup>m+c</sup>F<sub>q</sub>[[T]]<sup>N</sup> (c = conductor), so it is a subspace of
   (F<sub>q</sub>[T]/T<sup>m+c</sup>)<sup>N</sup>. Building its reduced echelon basis from the
   highest position down, T<sup>a</sup>- and T<sup>b</sup>-stability of each new basis vector is a
   *linear* condition on its free coordinates given the higher part, so every submodule is
   produced exactly once by Gaussian elimination. No formula from the papers is used. Work is
   capped; a capped run reports `NOT_RUN_BUDGET`, never a match.

## Sealed certificate

`hjo_certificate_v1.json` (sha256 `9849e9b1cefdcb0ad67544cf0895f14e37cc62c93c089051b6541a76d0e7a4e7`,
domain-separated SHA-256 seal; unsigned) records, for all 17 coprime pairs with a + b ≤ 13:
V1 through q<sup>40</sup>; 43 V2/V4 rows (ranks 1–3 where δ ≤ 6, else 1–2), each checked through
deg F<sub>N</sub> + 4; V3; and the V5 census below. Build time on this container: 104 s.

```
python research/hjo_loom/build_certificate.py --check research/hjo_loom/hjo_certificate_v1.json
```

Standard library only: the builder loads `szl_khipu/hjo_loom.py` by file path.

### V5 census — brute-force submodule counts, all equal to HJO Thm 1.2 at L = q

| (a,b) | N | q | colength 0, 1, 2, … |
| --- | --- | --- | --- |
| (2,3) | 1 | 2 | 1, 3, 3, 3, 3, 3, 3 |
| (2,3) | 2 | 2 | 1, 15, 59, 147, 323 |
| (2,3) | 2 | 3 | 1, 40, 238, 832 |
| (2,5) | 2 | 3 | 1, 40, 1210, 7636 |
| (3,4) | 2 | 2 | 1, 63, 747, 3843 |
| (3,4) | 2 | 3 | 1, 364, 11983, 102244 |
| (3,5) | 2 | 2 | 1, 63, 1131, 9603 |
| (4,5) | 1 | 2 | 1, 15, 43, 99, 147 |
| (4,5) | 1 | 3 | 1, 40, 157, 508 |
| (5,6) | 1 | 2 | 1, 31, 171, 515 |

(Full table, 24 rows, in the certificate.) HJO prove Thm 1.2 for every coprime pair; these
rows are an independent finite-field replay of it, and the rank-2 rows exercise its high-rank
regime. Separately, the V1 rows with a ≥ 4 are the product identities first settled by HLO
(cases a ≤ 3 were known earlier).

## Sealed certificate v2 — V7 census over every prime power q ≤ 9, V8 counts as polynomials in q

Status: **MEASURED finite checks, run on 2026-11-19**; evidence, not proof. HJO Thm 1.2
already covers every finite field, nothing here is a new theorem, and the brute force and the
formula are two routes in one codebase, not independent replication.

`hjo_certificate_v2.json` (schema `szl.khipu.hjo-certificate/v2`, seal
`bd7b4197b81939c4d6aca29f919c01f5f8dc2d72756623ea75a005cf34c8bc2b`, domain-separated
SHA-256; unsigned) extends the V5 census to
GF(4), GF(5), GF(7), GF(8) and GF(9), with GF(4) = F<sub>2</sub>[x]/(x<sup>2</sup>+x+1),
GF(8) = F<sub>2</sub>[x]/(x<sup>3</sup>+x+1) and GF(9) = F<sub>3</sub>[x]/(x<sup>2</sup>+1).
Method, caps and wall time: [METHOD.md](METHOD.md#addendum-v2-2026-11-19-every-prime-power-q--9-and-the-counts-as-polynomials-in-q).

```
python research/hjo_loom/build_certificate.py --v2 --jobs 4 --check research/hjo_loom/hjo_certificate_v2.json
```

### V7 — colengths whose brute-force count equals HJO Thm 1.2 at L = q

Each of the 112 series runs colength 0, 1, 2, … under a cap of 3,000,000 recursion steps for
the whole series, up to colength 8. A range ending below 8 means the next colength was
abandoned at the cap; no partial count is recorded. Every listed colength agrees with the
formula. Of the 643 colength counts compared, 112 are colength 0, where both sides are 1 by
construction, so 531 are non-trivial; (4,5) with N = 2 compares nothing else at q = 5, 7, 8
and 9.

| (a,b) | N | q = 2 | q = 3 | q = 4 | q = 5 | q = 7 | q = 8 | q = 9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| (2,3) | 1 | 0–8 | 0–8 | 0–8 | 0–8 | 0–8 | 0–8 | 0–8 |
| (2,3) | 2 | 0–8 | 0–7 | 0–6 | 0–5 | 0–4 | 0–3 | 0–3 |
| (2,5) | 1 | 0–8 | 0–8 | 0–8 | 0–8 | 0–8 | 0–8 | 0–8 |
| (2,5) | 2 | 0–8 | 0–5 | 0–3 | 0–3 | 0–2 | 0–2 | 0–1 |
| (3,4) | 1 | 0–8 | 0–8 | 0–8 | 0–8 | 0–8 | 0–8 | 0–8 |
| (3,4) | 2 | 0–5 | 0–3 | 0–2 | 0–1 | 0–1 | 0–1 | 0–1 |
| (3,5) | 1 | 0–8 | 0–8 | 0–8 | 0–8 | 0–8 | 0–8 | 0–8 |
| (3,5) | 2 | 0–4 | 0–2 | 0–1 | 0–1 | 0–1 | 0–1 | 0–1 |
| (2,7) | 1 | 0–8 | 0–8 | 0–8 | 0–8 | 0–8 | 0–8 | 0–8 |
| (2,7) | 2 | 0–6 | 0–3 | 0–2 | 0–2 | 0–2 | 0–1 | 0–1 |
| (4,5) | 1 | 0–8 | 0–8 | 0–8 | 0–7 | 0–4 | 0–4 | 0–3 |
| (4,5) | 2 | 0–2 | 0–1 | 0–1 | 0–0 | 0–0 | 0–0 | 0–0 |
| (3,7) | 1 | 0–8 | 0–8 | 0–8 | 0–8 | 0–5 | 0–4 | 0–4 |
| (3,7) | 2 | 0–3 | 0–1 | 0–1 | 0–1 | 0–1 | 0–1 | 0–1 |
| (4,7) | 1 | 0–8 | 0–7 | 0–4 | 0–3 | 0–2 | 0–2 | 0–2 |
| (5,6) | 1 | 0–8 | 0–5 | 0–3 | 0–2 | 0–1 | 0–1 | 0–1 |

For example, over GF(9) the rank-2 series of (2,3) has 820, 14,752 and 140,140 submodules of
colength 1 to 3, and over GF(8) the rank-1 series of (4,5) has 585, 5,257, 42,633 and 79,497
of colength 1 to 4.

**What V7 does not test.** On the cases tried, the counts do not depend on whether the tables
form a field. Over Z/6, which has zero divisors, the same recursion returns the Thm 1.2
polynomial evaluated at 6 (1, 259, 3103 for (2,3) with N = 2 at colengths 0–2), and with a
GF(4) product in which x·x = x, which is not associative, it returns the q = 4 counts of (3,4)
with N = 1 in the same number of steps. So V7 at q = 4, 8 and 9 checks the enumeration against
the formula at more values of q, but its agreement there is not evidence that the
GF(p<sup>k</sup>) tables are right; that rests on the unit tests of the tables and of the
linear solver. Both runs are kept in `tests/test_hjo_loom.py` as negative controls.

### V8 — the counts as polynomials in q, and how far the brute-force points fix them

The formula's colength-m count is interpolated exactly at integer L = 2, 3, … (with at least
three points beyond the degree bound N²δ + (N−1)m). Separately, the brute-force counts at the
prime powers that reached colength m are interpolated on their own. **RECOVERED**: at least
degree + 1 brute-force points, the degree being that of the formula's polynomial, and their
interpolant equals that polynomial coefficient by coefficient. **UNDERDETERMINED**: fewer
points than degree + 1. Of 124 rows, 75 are RECOVERED (16 of them the constant 1 at colength
0, so 59 beyond colength 0) and 49 UNDERDETERMINED.

Given V7, a RECOVERED row is what uniqueness of interpolation predicts, and it shows that,
given the degree of the formula's polynomial, the brute-force points determine its
coefficients. It does not show that the enumeration fixes the polynomial by itself. Given only
the bound N²δ + (N−1)m, which comes from the form of Thm 1.2, the points fix the polynomial
when there are at least bound + 1 of them: 57 of the 75 RECOVERED rows (49 beyond colength 0).
The other 18 (10 beyond colength 0) are marked †: for each, the formula's polynomial plus the
product of (q − q<sub>i</sub>) over its brute-force fields q<sub>i</sub> stays within the bound
and takes the same values at those fields.

| (a,b) | N | RECOVERED: colength (degree); † fewer points than the bound + 1 | UNDERDETERMINED: colength (degree; brute-force points) |
| --- | --- | --- | --- |
| (2,3) | 1 | 0 (0), 1 (1), 2 (1), 3 (1), 4 (1), 5 (1), 6 (1), 7 (1), 8 (1) | — |
| (2,3) | 2 | 0 (0), 1 (3), 2 (4), 3 (5)† | 4 (6; 5), 5 (7; 4), 6 (8; 3), 7 (9; 2), 8 (10; 1) |
| (2,5) | 1 | 0 (0), 1 (1), 2 (2), 3 (2), 4 (2), 5 (2), 6 (2), 7 (2), 8 (2) | — |
| (2,5) | 2 | 0 (0)†, 1 (3)† | 2 (6; 6), 3 (7; 4), 4 (8; 2), 5 (9; 2), 6 (10; 1), 7 (11; 1), 8 (12; 1) |
| (3,4) | 1 | 0 (0), 1 (2), 2 (2), 3 (3), 4 (3), 5 (3), 6 (3), 7 (3), 8 (3) | — |
| (3,4) | 2 | 0 (0)†, 1 (5)† | 2 (8; 3), 3 (9; 2), 4 (11; 1), 5 (12; 1) |
| (3,5) | 1 | 0 (0), 1 (2), 2 (3), 3 (3), 4 (4), 5 (4), 6 (4), 7 (4), 8 (4) | — |
| (3,5) | 2 | 0 (0)†, 1 (5)† | 2 (8; 2), 3 (11; 1), 4 (12; 1) |
| (2,7) | 1 | 0 (0), 1 (1), 2 (2), 3 (3), 4 (3), 5 (3), 6 (3), 7 (3), 8 (3) | — |
| (2,7) | 2 | 0 (0)†, 1 (3)† | 2 (6; 5), 3 (9; 2), 4 (10; 1), 5 (11; 1), 6 (12; 1) |
| (4,5) | 1 | 0 (0), 1 (3), 2 (4), 3 (5), 4 (5)† | 5 (5; 4), 6 (6; 4), 7 (6; 4), 8 (6; 3) |
| (4,5) | 2 | 0 (0)† | 1 (7; 3), 2 (12; 1) |
| (3,7) | 1 | 0 (0), 1 (2), 2 (4), 3 (4), 4 (5) | 5 (5; 5), 6 (6; 4), 7 (6; 4), 8 (6; 4) |
| (3,7) | 2 | 0 (0)†, 1 (5)† | 2 (10; 1), 3 (13; 1) |
| (4,7) | 1 | 0 (0)†, 1 (3)†, 2 (5)† | 3 (6; 4), 4 (7; 3), 5 (7; 2), 6 (8; 2), 7 (8; 2), 8 (8; 1) |
| (5,6) | 1 | 0 (0)†, 1 (4)† | 2 (6; 4), 3 (7; 3), 4 (8; 2), 5 (8; 2), 6 (9; 1), 7 (9; 1), 8 (9; 1) |

Recovered polynomials of degree 4 or more, coefficients from the certificate (extra checks
count the points beyond the formula's degree + 1; † as above):

| (a,b) | N | colength | count as a polynomial in q | brute-force points | extra checks |
| --- | --- | --- | --- | --- | --- |
| (2,3) | 2 | 2 | 1 + q + 2q<sup>2</sup> + 2q<sup>3</sup> + 2q<sup>4</sup> | 7 | 2 |
| (2,3) | 2 | 3† | 1 + q + 2q<sup>2</sup> + 3q<sup>3</sup> + 3q<sup>4</sup> + 2q<sup>5</sup> | 7 | 1 |
| (3,4) | 2 | 1† | 1 + q + q<sup>2</sup> + q<sup>3</sup> + q<sup>4</sup> + q<sup>5</sup> | 7 | 1 |
| (3,5) | 1 | 4 to 8, each | 1 + q + 2q<sup>2</sup> + 2q<sup>3</sup> + q<sup>4</sup> | 7 | 2 |
| (3,5) | 2 | 1† | 1 + q + q<sup>2</sup> + q<sup>3</sup> + q<sup>4</sup> + q<sup>5</sup> | 7 | 1 |
| (4,5) | 1 | 2 | 1 + q + 2q<sup>2</sup> + 2q<sup>3</sup> + q<sup>4</sup> | 7 | 2 |
| (4,5) | 1 | 3 | 1 + q + 2q<sup>2</sup> + 3q<sup>3</sup> + 2q<sup>4</sup> + q<sup>5</sup> | 7 | 1 |
| (4,5) | 1 | 4† | 1 + q + 2q<sup>2</sup> + 3q<sup>3</sup> + 3q<sup>4</sup> + 2q<sup>5</sup> | 6 | 0 |
| (3,7) | 1 | 2 | 1 + q + 2q<sup>2</sup> + q<sup>3</sup> + q<sup>4</sup> | 7 | 2 |
| (3,7) | 1 | 3 | 1 + q + 2q<sup>2</sup> + 2q<sup>3</sup> + 2q<sup>4</sup> | 7 | 2 |
| (3,7) | 1 | 4 | 1 + q + 2q<sup>2</sup> + 2q<sup>3</sup> + 3q<sup>4</sup> + q<sup>5</sup> | 7 | 1 |
| (3,7) | 2 | 1† | 1 + q + q<sup>2</sup> + q<sup>3</sup> + q<sup>4</sup> + q<sup>5</sup> | 7 | 1 |
| (4,7) | 1 | 2† | 1 + q + 2q<sup>2</sup> + 2q<sup>3</sup> + 2q<sup>4</sup> + q<sup>5</sup> | 7 | 1 |
| (5,6) | 1 | 1† | 1 + q + q<sup>2</sup> + q<sup>3</sup> + q<sup>4</sup> | 7 | 2 |

A row with 0 extra checks, such as (4,5) with N = 1 at colength 4, has exactly degree + 1
brute-force points: given the formula's degree the polynomial is determined, but no spare
point tests it, and its 6 points are one short of the bound 6 + 1.

## Limits

- Finite ranges only. Agreement on finitely many coefficients is evidence, not proof; the
  theorems are proved in the cited papers and formalized at
  [AxiomMath/HJO](https://github.com/AxiomMath/HJO) (revision observed `6a58dfa6`, not replayed).
- V7 and V8 stop at q ≤ 9, colength 8 and a fixed work cap. With seven fields, a count of
  degree 7 or more in q can never be RECOVERED from brute force here, whatever the cap, and
  no count whose bound N²δ + (N−1)m is 7 or more can be fixed by its points without the
  formula's degree.
- V7 does not test the GF(p<sup>k</sup>) tables (see V7 above). The full `--v2 --check`
  replay is not run in CI; the test file replays a cheap subset of V7 from scratch and
  rebuilds all of V8 from the sealed V7 rows.
- V6 compares partial sums of a convergent series with its predicted limit; it can only detect
  gross inconsistency.
- 2026-11-18 correction (Y. Huang, personal communication): the monotone-pruning precondition
  above was previously described as possibly-open; it is proved — Theorem 1.2 of
  [arXiv:2604.13238](https://arxiv.org/abs/2604.13238), stronger form, no containment hypothesis.
- The torus knots of this mathematics are algebraic objects. Nothing here links them to the
  physical knots of khipus; the OKR work in `../okr_corpus/` is a separate study.
