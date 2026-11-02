# SPDX-License-Identifier: Apache-2.0
"""Accuracy must compare one finite, valid prediction per labelled example."""
from unittest import TestCase, main, mock

import numpy as np

from szl_khipu.train import moons


class MoonsAccuracyTests(TestCase):
    def setUp(self):
        self.weights = {
            "W1": np.zeros((moons.H, moons.IN)),
            "b1": np.zeros(moons.H),
            "W2": np.zeros((moons.OUT, moons.H)),
            "b2": np.zeros(moons.OUT),
        }
        self.weights["W1"][0, 0] = 1
        self.weights["W2"][0, 0] = -1
        self.weights["W2"][1, 0] = 1
        self.features = np.array([[-1., 0.], [1., 0.]])
        self.labels = np.array([0, 1])

    def test_exact_scores_and_single_sample_remain_supported(self):
        self.assertEqual(moons.accuracy(self.weights, self.features, self.labels), 1.0)
        self.assertEqual(moons.accuracy(self.weights, self.features, 1-self.labels), 0.0)
        self.assertEqual(moons.accuracy(self.weights, self.features, [0, 0]), 0.5)
        self.assertEqual(moons.accuracy(self.weights, self.features[0], 0), 1.0)
        self.assertEqual(moons.accuracy(self.weights, self.features[:1], [0]), 1.0)

    def test_labels_cannot_broadcast_or_fabricate_classes(self):
        for labels in (self.labels[:, None], self.labels[None, :], 0,
                       [0], [0, 1, 0], [0, .5], [0, 2], [0, np.nan],
                       [0, np.inf], [0, 1j], ["0", "1"]):
            with self.subTest(labels=repr(labels)):
                with self.assertRaises(ValueError):
                    moons.accuracy(self.weights, self.features, labels)

    def test_empty_malformed_or_nonfinite_features_are_rejected(self):
        examples = (np.empty((0, 2)), [1.], np.ones((2, 3)),
                    np.ones((1, 2, 2)), [[np.nan, 0], [1, 0]],
                    [[np.inf, 0], [1, 0]], [[-np.inf, 0], [1, 0]],
                    [[1j, 0], [1, 0]])
        for features in examples:
            with self.subTest(features=repr(features)):
                with self.assertRaises(ValueError):
                    moons.accuracy(self.weights, features, self.labels)

    def test_corrupt_weights_cannot_receive_perfect_score(self):
        for key in self.weights:
            for bad in (np.nan, np.inf, -np.inf):
                with self.subTest(key=key, bad=bad):
                    weights = {k: v.copy() for k, v in self.weights.items()}
                    weights[key].flat[0] = bad
                    with np.errstate(all="ignore"):
                        with self.assertRaises(ValueError):
                            moons.accuracy(weights, self.features, np.zeros(2))

    def test_wrong_weight_shapes_are_rejected_before_forward(self):
        for key in self.weights:
            weights = {k: v.copy() for k, v in self.weights.items()}
            weights[key] = np.array(0.)
            with self.subTest(key=key), mock.patch.object(moons, "forward") as forward:
                with self.assertRaises(ValueError):
                    moons.accuracy(weights, self.features, self.labels)
                forward.assert_not_called()

    def test_nonfinite_result_from_finite_large_weights_is_rejected(self):
        weights = {k: v.copy() for k, v in self.weights.items()}
        weights["W1"][:] = 0.
        weights["b1"][:] = 1.
        weights["W2"][:] = np.finfo(np.float64).max
        with np.errstate(all="ignore"):
            with self.assertRaises(ValueError):
                moons.accuracy(weights, self.features, np.zeros(2))

    def test_evaluation_does_not_mutate_inputs(self):
        before = {k: v.copy() for k, v in self.weights.items()}
        features = self.features.copy()
        labels = self.labels.copy()
        moons.accuracy(self.weights, self.features, self.labels)
        for name in before:
            np.testing.assert_array_equal(self.weights[name], before[name])
        np.testing.assert_array_equal(self.features, features)
        np.testing.assert_array_equal(self.labels, labels)


if __name__ == "__main__":
    main()
