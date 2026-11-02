# Moons accuracy input contract

`moons.accuracy` requires a nonempty finite matrix of two real features
per example, one binary label per example, and finite arrays with the
two-moons model's existing 2–8–2 shapes. A single feature row and scalar
label remain accepted. Column/row matrices of labels, wrong lengths,
fractional labels, unknown classes, nonfinite values and complex values
raise `ValueError`; they are not scores.

This prevents two concrete errors in the previous scorer:

- Two perfectly classified rows with labels shaped `(2, 1)` broadcast
  against predictions shaped `(2,)`, silently reporting 0.5 instead of
  rejecting the malformed labels.
- NaN-corrupted output weights can yield all-NaN probabilities.
  NumPy's argmax then selects index zero, allowing a perfect 1.0 score
  when the labels are all zero. Invalid output probabilities now fail.

Finite inputs can still overflow during inference; the final probability
matrix is also checked. No parameter or input is modified by the scorer.

The model architecture, forward pass, optimizer, generator and saved-weight
format are unchanged. The legacy `train(...)[1]["acc"]` metric still
measures training-set accuracy; this validation repair does not convert it
into unseen evaluation or establish model quality. No model promotion,
publication, GPU run or live-runtime change is part of this repair.
