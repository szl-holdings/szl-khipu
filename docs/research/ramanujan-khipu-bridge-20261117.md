# Khipu × Ramanujan: a bounded research bridge (2026-11-17)

**Status: source-only research experiment.** This is not a decipherment, an
independent proof of the infinite Rogers--Ramanujan identities, a trained model,
or a release/qualification claim. It does not change any production Khipu
package API, receipt writer, scheduler, model, or evaluation baseline.

## Scientific origins: two different kinds of knots

The October 29, 2026 Scientific American article describes an **algebraic
geometry and knot theory** result, not an archaeological result:

- Huang, Jiang and Oblomkov's torus-knot singularity research:
  https://arxiv.org/abs/2608.16086
- Huang, Lau and Ono's theorem for every coprime 1 < a < b:
  https://arxiv.org/abs/2609.20567v2
- The authors' Lean formalization: https://github.com/AxiomMath/HJO
  (reference checked at main 6a58dfa6ab98bd35d841cb2cf8fd9081f62fad03).
  The paper's v2 states the formalization is **unconditional**; do not
  silently substitute the older v1 abstract which said conditional.
- The classical Rogers--Ramanujan partition identities count partitions
  with gaps >= 2 versus parts in residues (1,4) or (2,3) modulo 5.

A torus knot arising as the link of a plane curve singularity is not
automatically the same mathematical object as a physical knot on an
archaeological cord. A similarity in the word "knot" is not a proof.
No mapping between Inka khipu signs and HJO torus-knot identities is claimed.

There *is* an independent archaeological knot-theory precedent:

- Mackinley FitzPatrick, "Knot Tricks: What Mathematical Knot Theory Can
  Reveal about the Structure of Khipu Knot Encoding", Latin American
  Antiquity, March 30, 2026:
  https://www.cambridge.org/core/journals/latin-american-antiquity/article/abs/knot-tricks-what-mathematical-knot-theory-can-reveal-about-the-structure-of-khipu-knot-encoding/41EA129948DF7555A99F4B11E57C30F5
  The abstract treats actual khipu knot forms, ambiguity and possible
  flexible encoding; it does not equate them with Ramanujan identities.

## Existing leaders and reproducible datasets

Mathematics: Yifeng Huang, Ruofan Jiang, Alexei Oblomkov, Kenny Lau,
Ken Ono, Peter Paule; earlier foundational work by Leonard Rogers,
Srinivasa Ramanujan, Basil Gordon and George Andrews.

Andean material-record research: Mackinley FitzPatrick, Manuel Medrano,
Ashok Khosla, Jon Clindaniel, Carrie Brezine, Sabine Hyland, Marcia and
Robert Ascher, and the Open Khipu Repository advisory collaborators.
Credit the original khipukamayuqs and Andean knowledge holders first.

Open Khipu Repository (OKR): https://github.com/khipulab/open-khipu-repository
- Versioned dataset record: https://doi.org/10.5281/zenodo.18025748
- Repository master examined at 4039ca51f4de661d80d0160596309c983a62a9c7.
- The archive's own documentation says much of the semantic code remains
  undeciphered and explicitly discusses unequal access and Indigenous
  participation. Do not claim an ancient algorithm from modern simulations.
- Additional independent curation and data-science methods:
  https://www.khipufieldguide.com/ and
  https://doi.org/10.5281/zenodo.10472429
- Critical alternative interpretation of a colonial census/khipu match:
  https://doi.org/10.1215/00141801-11266328 (2024).

## Implemented *finite* control

Run from repository root with Python 3.11+:

    python -m unittest discover -s tests -p 'test_ramanujan_khipu_witness.py' -v
    python frontier/ramanujan_khipu_witness.py --n 128

The standard-library-only runner independently computes:

1. Exact partition coefficients via a gap-at-least-two recurrence.
2. Exact coefficients of modular-class unrestricted partitions via a
   separate coin-change generating-function recurrence.
3. The two classical identities, separately, for degrees 0 through 128.

It emits 258 bounded exact coefficient observations (2 x 129), along with a
lossless **modern digital cord sketch** that stores decimal-place digits,
and a reproducible SHA-256 of canonical output. The digital cord is an
engineering metaphor, not a historically reconstructed encoding.
An absent observation is never silently turned into zero. The hash is
not a signature or independent attestation.

The reference run completed 12 offline unit tests, including wrong-residue
negative control, tampered coefficient/cord controls, type and limit
refusals and CLI fail-closed behavior. For n = 6, RR1 gives 3 and RR2 gives
2 by both independent methods. The output manifest at bound 128 has
SHA-256 8cc1b46bf92e5d9dcbdda52725c634f34539e4d65aa5ad2eb83e02f5906bf09c
for the version tested locally; source-only GitHub publication and remote
CI remain separate gates. Rerun from the reviewed Git revision before
using this digest as a reproduction claim.

**This finite agreement does not establish either infinite identity.**
The cited Axiom Lean repository is an external proof source, not a proof
reproduced, modified, or formally certified by SZL in this experiment.

## Independent research hypothesis and admission gates

Question H1: do well-documented knot form, cord hierarchy, attachment
orientation, and place-value relations predict held-out administrative
constraints better than provenance-preserving null models?

1. **Source gate:** obtain permitted OKR/Khipu Field Guide records at immutable
   revisions, record KH identifiers, collection/site, object condition,
   recorder, permissions, photographs and independent scholarly
   interpretation. Do not import unpublished ceremonial/sensitive data.
2. **Measurement gate:** define typed fields for knot form and orientation,
   primary/pendant/subsidiary hierarchy, position, spin/ply, fiber/color,
   uncertainty and damage. Preserve missing/unknown rather than interpreting
   every gap as zero. Do not silently repair discrepancies among transcribers.
3. **Independent checks:** reproduce known decimal-place and sum constraints
   where archaeologists already support them; quantify valid records /
   attempted records / excluded records and per-source disagreement.
   Counterexamples are retained rather than overwritten.
4. **Falsification gate:** compare to site- and recorder-preserving
   permutation nulls, and a non-topological baseline. Separate individual
   khipus or archaeological contexts across train/validation/test; never
   split cords of the same artifact across folds. Report sample sizes,
   effect sizes, uncertainty, and historical alternatives, not accuracy
   alone. Stop claims if no robust held-out advantage exists.
5. **Formal gate:** separately encode proven decoding/accounting lemmas
   in Lean with imported theorem inventory, no unacknowledged axioms/sorries,
   pinned Lean/Mathlib revisions, and replay on an independent runner.
   Axiom's HJO proof does **not** certify any claim about archaeological
   khipus or SZL's models.
6. **Publication gate:** invite Andean and Quechua-speaking scholarship and
   institutions with substantive review/credit; separate machine-checkable
   facts, proposed modern computational abstractions, and contested
   interpretations. Require rights review before redistribution.

## Claim ledger

| Claim | Status |
| --- | --- |
| Khipus are sophisticated historical Andean information records | Supported by established scholarship |
| Two classical partition identities match for coefficients 0..128 | FINITE_MATCH (local experiment only) |
| Infinite HJO theorem | External published preprint and Lean formalization; not rerun here |
| Modern digital cord is identical to historical knot grammar | NOT CLAIMED |
| Ancient khipus encoded Rogers--Ramanujan identities | NO EVIDENCE |
| SZL Khipu model has mathematically proven reasoning/quality | NOT ESTABLISHED |
| Archaeological H1 wins on held-out artifacts | NOT TESTED |

The goal is evidence-based recognition of Andean mathematical engineering
without confusing a meaningful research analogy with a historical proof.
