# SPDX-License-Identifier: Apache-2.0
"""Behavior and memory-shape contract for output-only canal attention."""
from __future__ import annotations

import unittest
from unittest.mock import patch

import numpy as np

from szl_khipu import yarqa_attn_output
from szl_khipu.yarqa import canal_bounds, yarqa_attn


def dense_masked(q, k, v, canals):
    bounds = canal_bounds(len(q), canals)
    ids = np.searchsorted(bounds[1:], np.arange(len(q)), side="right")
    scores = q @ k.T / np.sqrt(q.shape[1])
    scores[ids[:, None] != ids[None, :]] = -np.inf
    weights = np.exp(scores - scores.max(axis=1, keepdims=True))
    weights /= weights.sum(axis=1, keepdims=True)
    return weights @ v


class OutputOnlyTests(unittest.TestCase):
    def inputs(self, size=17, seed=9):
        rng = np.random.default_rng(seed)
        return (rng.normal(size=(size, 7)), rng.normal(size=(size, 7)),
                rng.normal(size=(size, 5)))

    def test_matches_legacy_and_exact_mask_for_uneven_canals(self):
        for size in (2, 17, 65):
            q, k, v = self.inputs(size)
            for canals in (1, 2, size):
                for rows in (1, 8, 1000):
                    with self.subTest(size=size, canals=canals, rows=rows):
                        actual = yarqa_attn_output(q, k, v, canals, query_block_size=rows)
                        np.testing.assert_allclose(actual, dense_masked(q, k, v, canals),
                                                   rtol=1e-12, atol=1e-12)
                        np.testing.assert_allclose(actual, yarqa_attn(q, k, v, canals).out,
                                                   rtol=1e-12, atol=1e-12)

    def test_unrelated_canal_perturbation_cannot_change_first_canal(self):
        q, k, v = self.inputs(17)
        original = yarqa_attn_output(q, k, v, 3)
        boundary = canal_bounds(17, 3)[1]
        k[boundary:] *= 100
        v[boundary:] += 100
        actual = yarqa_attn_output(q, k, v, 3)
        np.testing.assert_array_equal(actual[:boundary], original[:boundary])

    def test_one_token_canals_return_values_and_do_not_mutate_inputs(self):
        q, k, v = self.inputs(17)
        copies = [a.copy() for a in (q, k, v)]
        np.testing.assert_array_equal(yarqa_attn_output(q, k, v, 17), v)
        for actual, expected in zip((q, k, v), copies):
            np.testing.assert_array_equal(actual, expected)

    def test_singleton_empty_and_noncontiguous_inputs(self):
        for size in (0, 1):
            q, k, v = self.inputs(size)
            actual = yarqa_attn_output(q, k, v, 1)
            np.testing.assert_array_equal(actual, v)
            self.assertIsNot(actual, v)
        q, k, v = self.inputs(20)
        np.testing.assert_allclose(yarqa_attn_output(q[::2], k[::2], v[::2], 3),
                                   dense_masked(q[::2], k[::2], v[::2], 3), atol=1e-12)

    def test_rejects_invalid_controls_and_empty_groups(self):
        q, k, v = self.inputs(3)
        for value in (0, -1, 1.5, "2", True, np.bool_(False)):
            for name in ("n_canals", "query_block_size"):
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    controls = {"n_canals": 1, "query_block_size": 2, name: value}
                    yarqa_attn_output(q, k, v, **controls)
        with self.assertRaisesRegex(ValueError, "empty canals"):
            yarqa_attn_output(q, k, v, 4)
        with self.assertRaisesRegex(ValueError, "empty canals"):
            yarqa_attn_output(q[:0], k[:0], v[:0], 2)

    def test_rejects_bad_shapes_nonfinite_and_score_overflow(self):
        q, k, v = self.inputs()
        for args in ((q[0], k, v), (q, k[:-1], v), (q, k[:, :-1], v),
                     (q, k, v[:-1]), (q[:, :0], k[:, :0], v), (q, k, v[:, :0])):
            with self.subTest(shapes=[a.shape for a in args]), self.assertRaises(ValueError):
                yarqa_attn_output(*args, 1)
        for bad in (np.nan, np.inf, -np.inf):
            broken = q.copy()
            broken[0, 0] = bad
            with self.assertRaises(ValueError):
                yarqa_attn_output(broken, k, v, 1)
        for index in range(3):
            inputs = [q, k, v]
            inputs[index] = inputs[index].astype(complex) + 1j
            with self.assertRaisesRegex(ValueError, "real-valued"):
                yarqa_attn_output(*inputs, 1)
        with self.assertRaisesRegex(ValueError, "overflowed"):
            yarqa_attn_output(np.full_like(q, 1e308), np.full_like(k, 1e308), v, 1)

    def test_score_tiles_never_have_full_sequence_square_shape(self):
        q, k, v = self.inputs(17)
        real_matmul = np.matmul
        products = []

        def observe(a, b):
            products.append((a.shape, b.shape))
            return real_matmul(a, b)

        with patch("szl_khipu.yarqa.np.matmul", side_effect=observe):
            yarqa_attn_output(q, k, v, 1, query_block_size=1000)
        score_shapes = [(a[0], b[1]) for a, b in products if a[1] == 7]
        self.assertTrue(score_shapes)
        self.assertTrue(all(rows <= 8 and cols == 17 for rows, cols in score_shapes))
        self.assertNotIn((17, 17), score_shapes)

    def test_directional_derivative_matches_dense_reference(self):
        # NumPy has no autograd; this checks finite-difference sensitivity of
        # the operation, not an unsupported backward/gradient implementation.
        q, k, v = self.inputs(7)
        rng = np.random.default_rng(8)
        directions = [rng.normal(size=a.shape) for a in (q, k, v)]
        epsilon = 1e-5
        plus = [a + epsilon * d for a, d in zip((q, k, v), directions)]
        minus = [a - epsilon * d for a, d in zip((q, k, v), directions)]
        actual = (yarqa_attn_output(*plus, 3) - yarqa_attn_output(*minus, 3)) / (2 * epsilon)
        expected = (dense_masked(*plus, 3) - dense_masked(*minus, 3)) / (2 * epsilon)
        np.testing.assert_allclose(actual, expected, rtol=1e-7, atol=1e-9)


if __name__ == "__main__":
    unittest.main()
