# Khipu Sequence Scout v1 — bounded symbolic CPU training

Status: measured modern mathematical control, not a neural model, ancient Khipu decipherment, or a newly proved identity.

## Scientific grounding

- Huang, Lau and Ono (2026), Rogers–Ramanujan identities from the geometry of X^a=Y^b, arXiv:2609.20567v2: https://arxiv.org/abs/2609.20567v2
- Lau, Lee and Ono (2026), Formalized q-series: https://arxiv.org/abs/2607.01544
- Axiom HJO Lean formalization: https://github.com/AxiomMath/HJO — NOT independently replayed by this experiment.
- Medrano and Khosla (2024), How Can Data Science Contribute to Understanding the Khipu Code?: https://www.cambridge.org/core/journals/latin-american-antiquity/article/abs/how-can-data-science-contribute-to-understanding-the-khipu-code/E2D0E68A0515F3F9582A23C63693F4CE
- Open Khipu Repository: https://github.com/khipulab/open-khipu-repository ; DOI https://doi.org/10.5281/zenodo.18025748 — no archaeological records, sensitive data, museum pictures, cultural narratives, or training labels were imported.
- FitzPatrick (2026), Knot Tricks, Latin American Antiquity: historical cord knots are not automatically HJO algebraic torus knots.

## What was actually learned

Python standard-library symbolic parameter fitter, NOT neural-network weights. It searches a fixed set of 1,573 modular-product hypotheses: modulus 2 through 12, 1–4 positive residue classes, excluding residue zero. It fits to exact gap-partition coefficients of degrees 0–32 inclusive, and chooses a lowest-modulus and then shortest-residue description. Equivalent alternatives are disclosed. Only after selection does it evaluate degrees 33–128 using separate partition recurrences. These are authored synthetic controls, not independent data.

| Case | Selected residue model | Fitted hypothesis matches | Held-out exact matches | Frozen last-training-value baseline |
| --- | --- | --- | --- | --- |
| RR1 | modulo 5, residues 1 and 4 | 2 / 1573 | 96 / 96 | 0 / 96 |
| RR2 | modulo 5, residues 2 and 3 | 2 / 1573 | 96 / 96 | 0 / 96 |

The baseline is deliberately weak, not a competitive neural benchmark. This rediscovery is NOT a new Ramanujan theorem and it says nothing about historical Inka knowledge.

Falsification: changing one training count at n=6 yields HOLD_NO_CANDIDATE (no model). Modifying fitted parameters without a new digest yields TRAINED_MODEL_DIGEST_MISMATCH. An invalid model with a recomputed digest still fails held-out comparison. Missing and malformed values hold.

## Receipts and checks

Code: research/rr_discovery/learner.py. Artifact: research/rr_discovery/receipts/sequence_scout_v1.json. Canonical experiment digest:

f96b63b64e25ebae0910b2c143d570b2c044c0f432cb42e2893a8f433c9b3057

This unkeyed SHA-256 is integrity evidence, not a signature, identity or scientific qualification.

Commands from repository root:

    python research/rr_discovery/learner.py --check research/rr_discovery/receipts/sequence_scout_v1.json
    python -m unittest discover -s tests -p test_rr_sequence_scout.py -v

Optional --write PATH creates one new receipt exclusively; it never overwrites. Protected-main publisher stages only declared public sources and hashes, checks the receipt against a fresh run and validates the immutable Hub revision and live /discover endpoint before deployment claims.

TRAINING: exact symbolic parameter fit, synthetic inputs only.
ARTIFACT_VERIFIED: immutable source/byte readback, separate gate.
EVALUATED: 96/96 finite synthetic degrees per identity; not independently sealed.
DEPLOYED: only after live source-bound Space and /discover API check.
QUALIFIED: NOT ASSESSED (no archaeological, theorem, or neural generalization).

## Research beyond this control

Future tests of archaeological arithmetic and cord features require lawful access, stewardship, Indigenous/Andean participation, held-out whole artifacts and sites, provenance-aware negative controls, and explicit missing-data semantics. The mathematically separate HJO (a,b) q-series needs faithful definitions, source-pinned formal hypotheses and independent theorem checking; this finite classical experiment makes no claim about those extended cases.

## Conjecture Crucible — bounded finite falsification (new independent route)

The independent Python module `research/rr_discovery/falsifier.py` is separate from the trainer. It is a **user-proposed hypothesis checker, not a model**, and tests only the two classical Rogers–Ramanujan partition identities. It provides three exact finite arithmetic routes: a q-series sum using Pochhammer coefficients, a gap-partition recurrence, and the proposed modular-product coefficients. The two reference methods must agree before a report is issued.

Public user inputs are bounded to modulus 2..12, 1..4 strictly increasing positive residue classes (never residue zero) and finite degree 1..256. Unparseable, ambiguous, duplicated or out-of-bounds parameters return HOLD. The first detected mismatch returns an exact integer counterexample and, for small degrees, explicit examples of both partition collections. A match to degree 256 is only `FINITE_MATCH_NOT_A_PROOF` and does not imply any identity for all integers.

For the RR1 false proposal modulo 5 with residues 1,3, the first mismatch is **n=3**, where the actual gap count is 1 (partition [3]) while the proposed product count is 2 ([3] and [1,1,1]). For true classical RR1 residues 1,4 and RR2 residues 2,3, all 257 coefficients through n=256 agree across the three exact programs. These are mathematical controls, not novelty, trained neural weights, archaeological interpretation, Lean replay or an HJO general-family reproduction.

Run offline:
    python research/rr_discovery/falsifier.py --case RR1 --modulus 5 --residues 1,3 --limit 256
    python -m unittest discover -s tests -p test_rr_conjecture_crucible.py -v

The existing protected-main publisher only admits the canonical, byte-hashed `falsifier.py` with all other allowlisted Space files and SOURCE.json. The public Space exposes an explicitly clicked `/falsify` endpoint sharing its capped one-process CPU lane; it emits a domain-separated SHA-256 receipt, **not a signature**. Rights, source claims and conservative HJO/archaeological boundaries remain unchanged.
