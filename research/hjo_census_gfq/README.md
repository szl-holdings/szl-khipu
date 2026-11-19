<!-- SPDX-License-Identifier: Apache-2.0
(c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173 -->

# HJO Thm 1.2 census over GF(2), GF(3), GF(4), GF(5), GF(7), GF(8), GF(9)

Status: **MEASURED finite check of a published theorem.** This adds a new, separate artifact
(`hjo_census_gfq_v1.json`). It does **not** modify `../hjo_loom/hjo_certificate_v1.json`,
`szl_khipu/hjo_loom.py`, or any Theorem 1.2 statement or claim in this repository.

## What it does

For R = F<sub>q</sub>[[T<sup>a</sup>, T<sup>b</sup>]] it counts R-submodules of F<sub>q</sub>[[T]]<sup>N</sup>
of colength m by the same reduced-echelon brute force as V5 in `../hjo_loom/` (see its
[METHOD.md](../hjo_loom/METHOD.md)). The difference is that arithmetic goes through explicit
tables for GF(q), so the prime powers 4, 8 and 9 are covered too: F<sub>2</sub>[x]/(x²+x+1),
F<sub>2</sub>[x]/(x³+x+1) and F<sub>3</sub>[x]/(x²+1). Field axioms are asserted when the
tables are built.

Each count is then compared with Huang–Jiang–Oblomkov Thm 1.2 ([arXiv:2608.16086v1](https://arxiv.org/abs/2608.16086)),
whose motive is computed **symbolically as an integer polynomial in L** from the HLO cone sum
(`hjo_loom.n_bivariate`) and evaluated at L = q. The counts are also interpolated as polynomials in q:

- over the five new fields q = 4, 5, 7, 8, 9, which determines a polynomial only when its degree is ≤ 4;
- over all seven fields q = 2…9, which determines it only when its degree is ≤ 6.

A row whose Thm 1.2 polynomial has a higher degree is flagged `UNDERDETERMINED`. For such a row
the evidence is only the pointwise equality at every field.

## Rerun

```
python3 research/hjo_census_gfq/build_census.py --check-quick research/hjo_census_gfq/hjo_census_gfq_v1.json
python3 research/hjo_census_gfq/build_census.py --check research/hjo_census_gfq/hjo_census_gfq_v1.json --jobs 8   # full, ~1 h on 8 vCPU
python3 -m pytest tests/test_hjo_census_gfq.py
```

Standard library only (the tests also run under `python3 -m unittest`).

## Limits

Finitely many coefficients and fields. Agreement is evidence, not proof. The theorem is proved
in the cited paper, and nothing here is a new theorem. Interpolation recovers a polynomial only
inside the degree bound stated above. The degree bound itself comes from Thm 1.2, so the
recovered polynomials are a consistency check, not an independent derivation of the degree.
