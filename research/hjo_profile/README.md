# Khipu HJO Cylindric Lab — pinned finite definition study

**Experimental mathematical research, not a theorem proof, Lean replay, trained model, or archaeological analysis.** Source of truth for SZL code: `szl-holdings/szl-khipu`. The HJO definitions remain the work of their original authors.

## Exact external mathematical source and independent readback

- Yifeng Huang, Kenny Lau, Ken Ono, *Rogers–Ramanujan identities from the geometry of X^a=Y^b*, arXiv:2609.20567v2, October 7, 2026. https://arxiv.org/abs/2609.20567v2
- Axiom Math HJO formalization, immutable source revision: `https://github.com/AxiomMath/HJO/tree/6a58dfa6ab98bd35d841cb2cf8fd9081f62fad03`. Apache-2.0 repository.
- Original human-authored `Challenge/Basic.lean` exactly at that revision. Git blob SHA-1 `f641f5432891737d7b8ad6b0bf21a663dcf32901`; file SHA-256 `dc96a4b2f1bdeda0027968924ba480f8fc0e29e34eb56fb6cfbdbce2e235b48e` (5,784 bytes). Read directly at the pinned revision on owner BETTERWITHAGE; Git blob and SHA-256 independently verified.
- The file names formal definitions `HJO.Cylindric.profile`, `IsCylindric`, `BoundedBy` and `boundedGF`, as well as theorem *statements* `thm_finite` and `thm_main`. It contains FIVE `sorry` proof placeholders **by design as a comparator challenge template**. **These are not proofs.** Its actual solution and the comparator are separate. The published project README reports a successful upstream comparator on October 7; SZL has **not** run that comparator, or independently checked its imports or trusted axioms.
- Upstream Lean toolchain `leanprover/lean4:v4.34.0-rc1`, with pinned Mathlib and QSeriesLib dependencies. These external dependencies are **not** vendored, executed on the public Space, claimed as SZL-authored, or imported into private training without rights review.

## Exact bounded computation implemented here

Python standard-library module: `research/hjo_profile/cylindric.py`.

For coprime `1 < a < b`, the profile is exactly `c(i) = floor((i+1)b/a) - floor(ib/a)` for `0 <= i < a`. We check `sum c = b`, periodicity of the formula by `a`, and every profile entry either `floor(b/a)` or `ceil(b/a)`.

Rows `l(i,j)` are weakly decreasing finite-support sequences of natural entries. We enforce the actual source inequality `l(i+1,j+c_i) <= l(i,j)` on the cylinder, with row index periodic modulo `a` and maximum entry `N`. We count exact volume-weighted configurations for degrees `0..D`. These are **truncated coefficients of the cylindric `boundedGF` definition only**; there is no claim to have calculated the rank-N HJO polynomial `poly(a,b,N)`.

Two separate finite methods cross-check every coefficient: a pruned exhaustive row-tuple enumerator, and a weighted cyclic transfer-matrix enumerator. Their edge-check implementations are independent. If either disagrees, the evaluator **HOLDs** with the first degree. Bounded inputs: `2<=a<=4`, `a<b<=9`, `gcd(a,b)=1`, `0<=N<=3`, and `0<=D<=8`. This is small but exact: no implicit asymptotic extrapolation.

Measured examples on owner machine:

| Parameters | Source-derived profile | Exact coefficients by volume 0..D |
| --- | --- | --- |
| a=2, b=3, N=1, D=4 | [1,2] | [1,2,2,2,2] |
| a=3, b=5, N=2, D=6 | [1,2,2] | [1,3,8,14,25,36,52] |
| a=4, b=7, N=3, D=8 | [1,2,2,2] | [1,4,13,33,75,152,288,508,854] |

Both methods and negative controls are unit tested. This is **not externally independently replicated**, and the HJO finite identity is **not evaluated**: neither `HJO.Finite.poly` nor a full formal `boundedGF` theorem is computed.

## Publication and next necessary gates

The official Python Gradio Space includes an opt-in, closed-by-default `/hjo_profile` research panel with the profile and finite coefficient bars; returns a digest-bound, unsigned JSON receipt. The publisher includes only the exact reviewed `cylindric.py` bytes in its existing GitHub main-to-HF manifest (seven files in total), checks a queued `/hjo_profile` callback, the running source marker and immutable Hub bytes. It shares the original one-worker CPU queue with existing 3D, learner and falsifier tools. No GPU job, internet call, external Lean code execution, model weights, archaeological content, extra replicas or private files.

Future HJO rank-N comparison requires faithful implementation of `HJO.Finite.poly` (gap vectors, cone, Q, multiplicands, Gaussian multinomials), trusted source-bound test vectors, *independent* math review, and an opt-in sandboxed Lean toolchain/comparator replay. The source `Challenge/Basic.lean` alone is an **unsafe proof oracle** because it intentionally contains `sorry`. Preserve theorem assumptions and don't rewrite these generalized identities as classical modulo-five cases. Open archaeological questions require separately governed source rights and Andean research collaboration.

Proof states remain `FINITE_DEFINITION_CONTROL` and `HJO_EQUALITY_NOT_TESTED`; not `PROVED`, not new discovery and not proof of ancient Inca mathematical encoding.
