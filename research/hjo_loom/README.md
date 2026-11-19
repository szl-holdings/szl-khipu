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

## Limits

- Finite ranges only. Agreement on finitely many coefficients is evidence, not proof; the
  theorems are proved in the cited papers and formalized at
  [AxiomMath/HJO](https://github.com/AxiomMath/HJO) (revision observed `6a58dfa6`, not replayed).
- V6 compares partial sums of a convergent series with its predicted limit; it can only detect
  gross inconsistency.
- 2026-11-18 correction (Y. Huang, personal communication): the monotone-pruning precondition
  above was previously described as possibly-open; it is proved — Theorem 1.2 of
  [arXiv:2604.13238](https://arxiv.org/abs/2604.13238), stronger form, no containment hypothesis.
- The torus knots of this mathematics are algebraic objects. Nothing here links them to the
  physical knots of khipus; the OKR work in `../okr_corpus/` is a separate study.
