# TinyKhipu curriculum label repair

The old generator matched formula IDs as substrings. For seed `20260721`,
row 5 asked about `F18`, offered `F1 spare`, and labeled the example
`NAVIGATE` while citing `ABSTAIN other`. There was no offered F18 handle.
Seeds 11, 23 and 37 also contain false positive labels under the same
independent identifier check.

Curriculum labels now require whole formula identifiers. Citation labels
come from the actual matching handle positions. The random draws and example
text stay reproducible; corrected labels make the generated training data a
new source-versioned dataset. Record the source commit and generated-data
hash when using this version. Existing published weights and receipts do not
become results of the corrected curriculum.

This is a label-integrity repair, not a model qualification or promotion.
The legacy `tok_id` encoding and `forward` architecture are unchanged.
The legacy tokenizer still conflates F1 with longer F1-prefixed tokens, and
the decision head still reads the query without the offered handles.
Those limitations require a separately identified architecture/tokenizer
candidate and independent evaluation. The existing format-validity score
is not semantic correctness.

Regression coverage uses an independently written F+digits token oracle
over 8,000 generated rows, concrete prefix counterexamples, exact identifier
boundaries and deterministic replay. No GPU run or Hub publication is
required for these checks.
