# conformance/ — DSSEv1/PAE receipt conformance suite (Gate 5)

`run_vectors.py --vectors conformance/vectors/ --receipt release/run-manifest.json \
 [--prev-manifest <prev>] --require-all-pass`

Implemented vectors (no full SZL runtime required):
- V01 JSON canonicalization stability
- V02 DSSE PAE byte-length encoding (V11 binary-length malleation regression)
- V03 signature minimal-DER parsing
- V04 prev_hash receipt-chain linkage (fork/replay)
- V05 timestamp monotonicity (rollback)

--require-all-pass exits 1 on any failure — the suite fails closed.
