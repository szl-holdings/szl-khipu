# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Kernel silhouettes — fail-closed unit tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from szl_khipu.blocked import deny_by_default
from szl_khipu.block_kv import PagedCache, block_kv_gather
from szl_khipu.chain import ZERO, UnifiedReceiptChain, canon, sha256_hex
from szl_khipu.doctrine import DOCTRINE, YUYAY_AXES, YUYAY_FLOORS, proven_trust
from szl_khipu.formulas import ayni_ok, fifo_ok, run_all
from szl_khipu.lambda_gate import check_a3, evaluate_lambda, lambda_gate, uniform_weights, wgm
from szl_khipu.maskmod import future_mass, maskmod_attn
from szl_khipu.ouroboros import OUROBOROS_SELFCHECK, loop_tax
from szl_khipu.receipt_attn import tiled_attn
from szl_khipu.yarqa import yarqa_attn
from szl_khipu.anatomy import evaluate_anatomy, anatomy_metrics, WILLAY_CLASSIFIERS


class LambdaTests(unittest.TestCase):
    def test_zero_route(self) -> None:
        w = uniform_weights(4)
        self.assertEqual(wgm([0.9, 0.9, 0.0, 0.9], w), 0.0)

    def test_a3_egyptian(self) -> None:
        w = uniform_weights(13)
        self.assertTrue(check_a3(w, 0.7))
        self.assertLess(abs(wgm(np.full(13, 0.7), w) - 0.7), 1e-9)

    def test_nonfinite_zero_routes(self) -> None:
        w = uniform_weights(3)
        self.assertEqual(wgm([0.5, float("nan"), 0.5], w), 0.0)

    def test_weights_must_sum_to_one(self) -> None:
        self.assertEqual(wgm([0.5, 0.5], [0.3, 0.3]), 0.0)

    def test_lambda_gate_advisory(self) -> None:
        axes = list(YUYAY_FLOORS)
        g = lambda_gate(axes, threshold=0.5)
        self.assertTrue(g["advisory"])
        self.assertGreaterEqual(g["score"], 0.5)
        self.assertTrue(g["passed"])
        self.assertFalse(proven_trust)


class AttnTests(unittest.TestCase):
    def test_tiled_residual(self) -> None:
        rng = np.random.default_rng(11)
        Q = rng.normal(0, 0.5, size=(8, 4))
        K = rng.normal(0, 0.5, size=(8, 4))
        V = rng.normal(0, 0.5, size=(8, 4))
        _out, _p, residual = tiled_attn(Q, K, V, br=4, bc=4)
        self.assertLess(residual, 1e-5)

    def test_yarqa_leak(self) -> None:
        rng = np.random.default_rng(3)
        Q = rng.normal(0, 0.4, size=(12, 4))
        K = rng.normal(0, 0.4, size=(12, 4))
        V = rng.normal(0, 0.4, size=(12, 4))
        _out, probs, leaked = yarqa_attn(Q, K, V, n_canals=3)
        self.assertLess(leaked, 1e-12)
        self.assertTrue(np.allclose(probs.sum(axis=1), 1.0))

    def test_causal_future_mass(self) -> None:
        rng = np.random.default_rng(2)
        Q = rng.normal(0, 0.4, size=(8, 4))
        K = rng.normal(0, 0.4, size=(8, 4))
        V = rng.normal(0, 0.4, size=(8, 4))
        _o, probs, fm = maskmod_attn(Q, K, V, kind="causal")
        self.assertLess(fm, 1e-12)
        self.assertLess(future_mass(probs), 1e-12)


class OuroborosBlockedTests(unittest.TestCase):
    def test_selfcheck_numbers(self) -> None:
        s = OUROBOROS_SELFCHECK
        self.assertEqual(s["modelMs"], 1120)
        self.assertEqual(s["peakAttemptMs"], 900)
        self.assertEqual(s["overheadMs"], 180)
        self.assertEqual(s["serializationTaxMs"], 220)
        self.assertEqual(s["deadHopMs"], 220)
        self.assertEqual(s["honesty"]["modelMs"], "MEASURED")
        self.assertEqual(s["honesty"]["serializationTaxMs"], "DERIVED")

    def test_loop_tax_converged(self) -> None:
        t = loop_tax(
            [{"ok": False, "ms": 220}, {"ok": True, "ms": 900}],
            1300,
            4,
        )
        self.assertEqual(t["exit"], "converged")

    def test_blocked_output_is_none(self) -> None:
        d = deny_by_default(False, False, True)
        self.assertTrue(d["blocked"])
        self.assertIsNone(d["output"])
        hard = deny_by_default(True, True, True)
        self.assertTrue(hard["blocked"])
        self.assertIsNone(hard["output"])
        veto = deny_by_default(True, False, False)
        self.assertTrue(veto["blocked"])
        self.assertIsNone(veto["output"])
        self.assertEqual(veto["dominant"], "ADVISORY_LAMBDA")


class PuriqTests(unittest.TestCase):
    def test_f7_fifo(self) -> None:
        self.assertTrue(fifo_ok([3, 1, 4, 1, 5]))

    def test_f11_ayni(self) -> None:
        self.assertTrue(ayni_ok([(0, 1, 2.0), (1, 2, 2.0)]))

    def test_run_all_separates_families(self) -> None:
        rows = run_all(11)
        numeric = [r for r in rows if r["family"] == "numeric"]
        locked = [r for r in rows if r["family"] == "puriq_locked8"]
        self.assertTrue(all(r["proof_status"] == "CHECKED" for r in numeric))
        self.assertTrue(all(r["proof_status"] == "STRUCTURAL" for r in locked))
        self.assertEqual({r["id"] for r in locked}, set(DOCTRINE["lockedIds"]))  # type: ignore[arg-type]
        self.assertTrue(all(r["ok"] for r in rows))


class ChainNormBlockTests(unittest.TestCase):
    def test_chain_verify(self) -> None:
        c = UnifiedReceiptChain()
        c.emit("szl-lambda-gate", "lambda_gate", {"score": 0.91})
        c.emit("szl-receipt-attn", "tile", {"n": 8})
        ok, depth, br = c.verify()
        self.assertTrue(ok)
        self.assertEqual(depth, 2)
        self.assertEqual(br, -1)
        self.assertEqual(len(ZERO), 64)

    def test_canon_sorted(self) -> None:
        self.assertEqual(canon({"b": 1, "a": 2}), '{"a":2,"b":1}')
        self.assertEqual(sha256_hex("abc"), sha256_hex("abc"))

    def test_block_witness_swap_changes_gather(self) -> None:
        pages = np.arange(12, dtype=np.float64).reshape(4, 3)
        table = np.array([0, 1, 2, 3])
        g0 = block_kv_gather(pages, table)
        cache = PagedCache(pages, table)
        w = cache.swap(0, 3)
        self.assertTrue(w.changed)
        g1 = cache.gather()
        self.assertFalse(np.array_equal(g0, g1))

    def test_evaluate_lambda_zero_blocks(self) -> None:
        ev = evaluate_lambda([0.9, 0.9, 0.0, 0.9])
        self.assertTrue(ev["blocked"])
        self.assertEqual(ev["value"], 0.0)

    def test_doctrine_locked(self) -> None:
        self.assertEqual(DOCTRINE["version"], "v11 LOCKED")
        self.assertEqual(DOCTRINE["kernelCommit"], "c7c0ba17")
        self.assertEqual(len(YUYAY_AXES), 13)
        self.assertEqual(YUYAY_FLOORS[:2], (0.95, 0.95))


class AnatomyTests(unittest.TestCase):
    def test_default_five_live(self) -> None:
        ev = evaluate_anatomy(seed=11)
        self.assertEqual(ev.live_count, 5)
        self.assertFalse(ev.blocked)
        self.assertEqual(ev.locked_proven, 8)
        self.assertEqual(ev.conjecture_1, "OPEN")
        self.assertEqual(ev.energy, "UNAVAILABLE")
        self.assertIsNone(ev.energy_j)
        self.assertFalse(ev.proven_trust)
        self.assertTrue(ev.lambda_advisory)
        self.assertEqual(len(WILLAY_CLASSIFIERS), 5)
        m = anatomy_metrics(ev)
        self.assertEqual(m["blocked"], 0.0)
        self.assertEqual(m["liveCount"], 5.0)

    def test_zero_heart_fail_closes(self) -> None:
        ev = evaluate_anatomy(zero_heart=True, seed=11)
        heart = next(o for o in ev.organs if o["id"] == "heart")
        self.assertEqual(heart["status"], "DOWN")
        self.assertTrue(ev.blocked)
        self.assertLess(ev.live_count, 5)

    def test_leak_canal_fail_closes_brain(self) -> None:
        ev = evaluate_anatomy(leak_canal=True, seed=11)
        brain = next(o for o in ev.organs if o["id"] == "brain")
        self.assertEqual(brain["status"], "DOWN")
        self.assertTrue(ev.blocked)

    def test_tamper_yawar_fail_closes(self) -> None:
        ev = evaluate_anatomy(tamper_chain=True, seed=11)
        yawar = next(o for o in ev.organs if o["id"] == "circulatory")
        self.assertEqual(yawar["status"], "DOWN")
        self.assertTrue(ev.blocked)
        self.assertFalse(ev.chain_ok)

    def test_fabricated_joule_refused(self) -> None:
        ev = evaluate_anatomy(fabricate_joule=True, seed=11)
        nerve = next(o for o in ev.organs if o["id"] == "nervous")
        self.assertEqual(nerve["status"], "DOWN")
        self.assertEqual(nerve["honesty"], "UNAVAILABLE")
        self.assertEqual(ev.energy, "UNAVAILABLE")
        self.assertIsNone(ev.energy_j)
        self.assertTrue(ev.blocked)

    def test_sorry_cannot_be_green(self) -> None:
        ev = evaluate_anatomy(break_skeleton=True, seed=11)
        skel = next(o for o in ev.organs if o["id"] == "skeleton")
        self.assertEqual(skel["status"], "DOWN")
        self.assertEqual(ev.locked_proven, 8)

    def test_willay_veto_with_organs_live(self) -> None:
        ev = evaluate_anatomy(willay_fire=True, seed=11)
        self.assertEqual(ev.live_count, 5)
        self.assertTrue(ev.willay["refused"])
        self.assertTrue(ev.blocked)
        self.assertEqual(len(ev.willay["classifiers"]), 5)


if __name__ == "__main__":
    unittest.main()
