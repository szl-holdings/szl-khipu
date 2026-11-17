# Khipu — research-derived modern cord reconciliation (not an ancient cryptographic claim)

**Status:** first-party mathematical research and finite software verification. **No model training, artifact promotion, production authority, new historic decipherment, independent archival attestation, or theorem-kernel admission.** This material preserves the distinction between source scholarship, modern mathematical synthesis and engineering results.

## What Andean khipus establish

Khipu (also spelled quipu) means **knot** in Quechua. They are three-dimensional records made with primary, pendant and often subsidiary cords. Some surviving numeric records employ base-10 place values, with unit values at the pendant's lower end and tens/hundreds in higher registers. Figure-eight knots typically represent one in the units register, long knots 2–9 in that register, and overhand-knot groups indicate higher decimal places. A missing knot within a well-identified numeric register can signify zero, but missing or damaged physical cords cannot be automatically equated to zero. Some top cords encode sums, **not all archaeological cords are sums**. The **September 2026 Khipu Field Guide** analysis by Ashok Khosla and Agustín Da Fieno Delucchi proposes further equality/parenthesis interpretations and multi-level summation structures; those proposed interpretations must not be presented as universally established decipherment or as inventions by SZL. Spin/ply, knots, attachment and color can also have nonnumeric meaning, much of which remains an active research area. A present-day symbolic token list cannot reconstruct a damaged museum object or decipher narrative meaning.

**Attribution and primary research:** NIST, *Standardizing an Empire* (Jeffrey Splitstoser); Smarthistory *The Inka khipu*; Institut national des langues et civilisations orientales, *Quechua oral numeration and its writing in quipus*; Leland Locke (1923); Marcia and Robert Ascher; Gary Urton; Jon Clindaniel; Manuel Medrano; Ashok Khosla and the Khipu Field Guide (including September 2026 equality/equation work); Sabine Hyland for collaborative study of Collata khipus; **Open Khipu Repository (OKR)**, DOI `10.5281/zenodo.18025748`, version 2.1.0 archived (not imported here). The OKR's latest corpus and rights, data contributors, naming and community governance should be consulted before future archaeological data work. This prototype uses **only synthetic counts**, not OKR data or Indigenous community records.

Ancestral inspiration deserves precise recognition: we are adapting the **verified organizational ideas** of positional registers and some aggregate cords, *not* claiming that an ancient khipukamayuq used modular fingerprints, SHA-256, zero-knowledge proofs or SZL's modern formula. Any future public cultural product should involve relevant Andean scholars and contemporary Quechua-speaking and other Andean communities, with their own agency and attribution. This code cannot establish anyone's personal ancestry.

## New SZL research construction — Khipu Cord Reconciliation and Challenge (KCRC-v1)

For a **declared, ordered and complete** sequence of non-negative integer child-cord counts, `x=(x_0,...,x_{n-1})`, declared top-cord total `T`, prime `p=2^61-1`, and a challenge `r` in `F_p`, define:

\[
\boxed{\operatorname{KCRC}(x,T,r) = \left(\, T=\sum_{i=0}^{n-1}x_i,\quad W_r(x)=\sum_{i=0}^{n-1}x_i r^i\bmod p\,\right)}
\]

This is a *modern combination*: the first component takes inspiration from documented numeric khipu accounting; the second is a standard polynomial fingerprint used as a bounded cross-ledger diagnostic. The formula itself does not constitute a new theorem, and its use of the word khipu attributes inspiration rather than inventing an Inka encoding.

When a **reference sequence is fixed before the challenger selects `r`**, values lie in `F_p`, the two candidate sequences share the same ordered identities and length `n<p`, and they differ as vectors, their difference defines a nonzero polynomial of degree at most `n-1`. A nonzero polynomial over a field has at most its degree many roots, so

\[
\boxed{\Pr_{r\leftarrow F_p}[W_r(x)=W_r(y)\;\mid\;x\ne y\text{ fixed before }r] \le \frac{n-1}{p}.}
\]

This is a familiar finite-field root bound (Schwartz–Zippel in one variable), not a unique scientific discovery. With `n=2`, `x=(40,50)` and `y=(41,49)`, both sum to 90, yet `W_r(x)-W_r(y)=r-1`; choosing `r=1` makes the fingerprints collide. Therefore **hash/byte mismatch always prevails**, even when a polynomial witness matches.

### Trust gates that cannot be skipped

- **Identity and coverage:** all cord identifiers must be distinct, ordered and expected; no unknown children, missing denominator or default counts. Counts are nonnegative bounded integers; a numeric zero differs from an absent record.
- **Source pin:** `source_revision` is a 40-hex *declaration*. A matching string does not prove that Git or Hugging Face served those bytes. `rights_class` is also a caller-declared value, **not legal approval**.
- **Conservation:** an aggregate equality is necessary for this schema, not sufficient for truth. Different per-cord values can preserve a total.
- **Independent commitment:** the expected SHA-256 must have been retained independently from the candidate, with source/tenant/units bound. The software cannot prove independent custody from a supplied hex string.
- **Challenge timing:** the probability bound requires nonadaptive comparison, a field-uniform challenge chosen after commitment, and fixed-order vector semantics. If an adversary sees `r` before choosing `y`, the claimed false-accept rate does not apply. This prototype accepts caller-supplied `r` only as a test input and does not claim secure challenge generation.
- **No authorization:** all outcomes remain advisory, never valid model weights, signed receipts, cryptographic attestations, clinical results, autonomous actions or proof of recovered historical knowledge.

### Fit with SZL software

`szl-holdings/szl-khipu` already owns the real advisory Λ gate, receipt software, YARQA NumPy kernel, TinyKhipu silhouette and source-bindings; its README explicitly separates that software from the separately trained `SZL-Khipu-1.5B`, R2 and GGUF artifacts. `szl-holdings/khipu-consensus` already owns the DSSE/3-of-4 *protocol* (with safety/liveness unproved). The new formula **does not replace either**; it is intentionally staged in `research/khipu_math/`, outside the automatically mirrored `szl_khipu/` source and outside `lutar-lean`'s locked formula registry. In the future, an owner could use this as an additional **optional arithmetic preflight** before Khipu receipts are signed, but would first need authenticated sources, independent witness custody, exact revision readback and compatibility tests.

The correct new evidence states are `RECONCILED_FIXED_REFERENCE` and `DENY_REFERENCE_OR_CONSERVATION_MISMATCH`, not `PROVEN`, `QUALIFIED`, `PRODUCTION_READY` or `INCA_DECIPHERED`.

## Tusi is not automatically an Inka term

If **Tusi** refers to the **Ṭūsī couple**, that is a mathematical result associated with Nasir al-Din al-Ṭūsī in medieval Persian astronomy: coupled circular motions can generate linear oscillation. It is historically and mathematically valuable, **but it is not an Inka/khipu formula**. We should not conflate the traditions. If the user has a different Quechua or family usage of *tusi*, its spelling and source would need separate verification before attaching cultural meaning.

## Reproducibility

```bash
# From the szl-khipu repository root; pure Python 3.11+.
python -m unittest discover -s tests -p 'test_khipu_cord_research.py' -v
# Offline JSON receipt; exact trusted SHA supplied by an independent custodian:
python -m research.khipu_math.audit_cli \
  --reference /path/to/reference.json --candidate /path/to/observed.json \
  --expected-reference-sha256 <independently-pinned-64-hex> \
  --challenge 7 --out /new/private/receipt.json
```

All test data are synthesized in source. Software readback can be checked by SHA-256. The optional `PUBLIC_RIGHTS_DECLARED` class is **declarative only**, not permission to ingest archaeological records or train on them. The `research/` module is **not** a decoder of a specific museum khipu.

### Source links (read-only research)

- NIST https://www.nist.gov/nist-museum/standardizing-empire
- Smarthistory https://smarthistory.org/inka-khipu/
- INALCO https://www.inalco.fr/en/quechua-oral-numeration-and-its-writing-quipus
- Open Khipu Repository https://github.com/khipulab/open-khipu-repository
- OKR citation DOI https://doi.org/10.5281/zenodo.18025748
- Khipu Field Guide (2026 work on additional equality and sum constructs) https://www.khipufieldguide.com/notebook/analyses/equal_sums.html
- Ṭūsī scholarship https://www.iranicaonline.org/articles/tusi-nasir-al-din-mathematician-astronomer/
