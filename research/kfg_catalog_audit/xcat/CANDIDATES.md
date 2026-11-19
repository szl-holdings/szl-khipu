# Denominator-first conditional Khipu concordance

Bounded research replay, 2026-11-19. No training, remote changes, or archive mutation.

## Reproduce

Use Python 3.9+ and the standard library. Follow the public pinned download
instructions in [the adjacent README](README.md), including the optional
`okr_khipu.py` download. Use the adjacent `compare.py` for the shared input
hashes and SQL parser. For the frozen positive comparison, use the adjacent
`result.json` (or an exact copy).

```
python -B candidate_concordance.py /path/to/pinned/inputs > evidence.json
python -B summarize.py evidence.json result.json > summary.json
KHIPU_XCAT_INPUTS=/path/to/pinned/inputs python -B -m unittest -v test_candidates.py
```

The candidate replay does NOT read either relation export. The separate summary
step cross-checks the frozen positive result only AFTER the denominator exists.
All data/enumerator inputs are digest checked before execution. Module import
performs no data I/O. Normal and optimized Python produce identical ledgers.

Sources:
- KFG SQL and catalog: https://github.com/khipufieldguide/data-science-khipu-article/tree/a89c5dc1b8e412e3d0203719f76d5902563ab736/data
- SZL corpus and enumerator: [immutable public GitHub source](https://github.com/szl-holdings/szl-khipu/tree/9d62dec25f6ff6fd69a73bc74a7b714f8dcb2187); byte-identical to the original replay pins.
- Historical provenance: [Proof Loom publication](https://huggingface.co/spaces/SZLHOLDINGS/khipu-proof-loom/tree/c947def2fe0eae460c304d5ce0b7eb8e2881d9a5) (may require Hugging Face access; not used for public downloads).
- Underlying OKR commit: 4039ca51f4de661d80d0160596309c983a62a9c7.
- All exact input SHA256 values are included in evidence/summary JSON.

## Denominator and conservative structural join

The native all-corpus R2 enumeration counts 1,812 candidate unions of one to
three groups, restricted to known targets. On the 557 shared internal-ID AND
OKR-name objects it counts 1,652. Restricting to exactly one adjacent pendant
group with at least two cords gives 390 known-target candidates. The replay
extends the SAME structural touch rule to unknown targets, adding 22 for 412
candidates across 30 objects. It verifies its entire known-target candidate set
against native `_Structure.r2`, before inspecting arithmetic.

The KFG join requires the same target cord and the identical COMPLETE summand
cord set, a singleton target cluster, same primary, appropriate SQL top/pendant
roles, unique cluster ordinal ordering, and immediate adjacency in that ordering.
A top role is cord level -1 OR group class T/TPA; pendant groups must be level1
and not top/marker classes. Native OKR adjacency ignores intervening marker/top
clusters, while this strict KFG test does not. This is intentionally a narrower
intersection, not a claim that either catalog's native algorithm is wrong.

412 candidates partition into 385 strict shared candidates across 28 objects,
12 group-membership mismatches and 15 nonadjacent-cluster cases. Every excluded
row is retained with status; no missing export is assigned a negative label.
527 shared objects have no candidates in this narrow domain, not negative labels.

Of the 385 strict candidates:
- 276 have known arithmetic in both recorded sources.
- 197 are eligible in both (positive target and at least two positive summands):
  46 exact in both and 151 unequal in both.
- 79 known rows fail eligibility in both. They are not added to the eligible
  nonexact denominator; the broad exact-relation-false count is 151+79=230.
- 109 are unknown in BOTH. Unknown values are never zero. Knotless intact cords
  are zero under the declared rule; knotless broken/cut cords, or any missing/
  nonpositive knot contribution, are unknown. Knotted broken cords retain their
  recorded values; this does not assert preservation of lost knots.
- Value vectors agree on 270/276 known rows. Six differing vectors across KH0323,
  KH0389 and KH0405 leave equality classifications unchanged. These are source/
  field-value differences, not automatically transcription errors: OKR uses its
  published knot contribution convention and KFG uses knot_value_decimal.

Conservative joint-exact bounds are [46,155]/385 = [11.95%,40.26%]. These are
conditional finite-denominator bounds, not confidence intervals or population
prevalence. All unresolved cases are unknown on both sides. The upper bound is
intentionally loose: partial sums/known targets could further constrain cases.
Rows are correlated within artifacts; do not treat 385 rows as independent draws.
The summary includes all 30 contributing artifact partitions and exactness tables.

## Frozen-positive cross-check, performed afterwards

All 39 previously shared positives survive. Seven of eight SZL-only positives
survive, for 46 total. KH0068 target3038851 has equal recorded value2 and the
same complete summand group, but KFG marker cluster1015274 (cord3038850) lies
between target cluster1015275 and summand cluster1015273. Its immediate KFG
cluster adjacency therefore fails and the full row remains in the exclusion ledger.

This is recorded-source concordance conditional on an OKR-origin candidate
universe. Shared source material means it is not independent replication. It is
not a KFG algorithm rerun, sensitivity/precision measurement, catalog-wide
prevalence estimate, narrative decipherment, or model-performance improvement.

## Artifacts

`evidence.json` is the full deterministic ledger (~600KB). `summary.json` is the
compact publication candidate (~52KB), including its SHA256, all exclusions,
known disagreements, artifact partitions, and frozen-positive cross-check.
`SHA256SUMS` records final artifact hashes. Neither output replaces existing data.
