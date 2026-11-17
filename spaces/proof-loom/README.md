---
title: Khipu Proof Loom 3D
emoji: 🪢
colorFrom: blue
colorTo: yellow
sdk: gradio
sdk_version: 6.32.0
python_version: '3.11'
app_file: app.py
pinned: false
license: apache-2.0
short_description: Real khipu arithmetic and X^a=Y^b theorems, exact in 3D
---

# Khipu Proof Loom — pure-Python exact research lab

Authoritative source: [szl-holdings/szl-khipu](https://github.com/szl-holdings/szl-khipu).
Application source is Python only; Gradio packages the browser-side WebGL viewer.
Two kinds of knots are studied side by side and are **never conflated**.

## 1. Ancestral arithmetic — real Inka-style khipus

619 khipu records from the [Open Khipu Repository](https://github.com/khipulab/open-khipu-repository)
(`data/khipu.db` @ `4039ca51f4de`, MIT, [doi:10.5281/zenodo.18025748](https://doi.org/10.5281/zenodo.18025748))
are rebuilt as 3D digital twins from their recorded positions, lengths, colours and knots.
Knot values use the Locke decimal reading; missing or damaged values are never read as zero.
Four exact sum relations are searched with rules fixed before any corpus count, and each is
tested against a within-khipu permutation null (1,000 permutations, seed 1981).

MEASURED on the pinned records: **top cords equal the exact sum of the pendant groups beneath
them 54 times, against 4.96 expected by chance (10.9×, p ≤ 0.001)** — robust to a stricter
null, to dropping the strongest khipu and to excluding Incahuasi. Subsidiary sums are carried by
one khipu, in-group sum cords mostly by Incahuasi, and sums of other groups are at chance level;
the app shows all four honestly. This is arithmetic structure consistent with Ascher & Ascher
(1981). It is **not** a decipherment of khipu narrative and makes no claim about non-numeric
khipu content.

## 2. HJO Loom — the 2026 X^a = Y^b Rogers–Ramanujan theorems

Exact integer replays, from the papers' definitions, of
[Huang–Lau–Ono, arXiv:2609.20567](https://arxiv.org/abs/2609.20567) and
[Huang–Jiang–Oblomkov, arXiv:2608.16086](https://arxiv.org/abs/2608.16086):
Z<sub>a,b</sub> = P<sub>a,b</sub>; the finite identity F<sub>N</sub> = (q;q)<sub>N</sub>C<sub>c,≤N</sub>
with cylindric partitions counted directly; the rational-Catalan filter count; and a brute-force
census of R-submodules of F<sub>q</sub>[[T]]<sup>N</sup> (q = 2, 3; ranks 1 and 2) that matches
the HJO motive formula at every colength tested. A sealed certificate covers all 17 coprime
pairs with a + b ≤ 13. These are finite checks of published theorems: nothing new is proved,
the [AxiomMath/HJO](https://github.com/AxiomMath/HJO) Lean certificate is **not** replayed here,
and no historical link between torus knots and khipu knots is asserted.

## 3. Classic Proof Loom

The original Rogers–Ramanujan finite witness and the optional, default-OFF Sequence Scout
(1,573-hypothesis symbolic CPU fit; synthetic coefficients; not neural training).

## Resource and admission envelope

- One shared CPU execution lane (`concurrency_limit=1`) for all four expensive callbacks
  (`khipu`, `hjo`, `recompute`, `discover`); the public queue admits at most 32 pending items.
  Brute-force counts stop at a fixed work budget and report `NOT_RUN_BUDGET` — never a match.
- Every source and data file is SHA-256 pinned in `SOURCE.json` and re-checked at boot; the
  corpus, relations report and certificate are verified again on load.
- Gradio request-cache objects older than two hours are cleaned hourly
  (`delete_cache=(3600, 7200)`). Generated GLB scenes are content-addressed, read back before
  serving, and live in process-lifetime temporary directories.
- Each run is appended to a session-local SHA-256 hash chain. It is unsigned: digest integrity
  is not a signature, identity or scientific qualification.
- The public API is callable without login. Queue bounds are not identity-aware rate limiting.

## Licences

Application code: Apache-2.0 (SZL Holdings). OKR data: MIT, "Copyright (c) 2022 Open Khipu
Repository Team" — see `LICENSE-OKR.txt`. Mathematics: cited papers above.

This app does **not** train or query neural/LLM weights, prove infinite identities, replay the
external Lean formalization, decipher khipus, or claim production or scientific qualification.
