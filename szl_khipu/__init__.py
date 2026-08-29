# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""SZL Holdings khipu kernels — NumPy silhouettes of doctrine v11 LOCKED.

Lambda is advisory. proven_trust is False. Energy is MEASURED-NVML or UNAVAILABLE.
This package hashes with SHA-256; production metal kernels use SHA3-256.
"""

from __future__ import annotations

from typing import Any

from .blocked import deny_by_default, four_way_gate
from .block_kv import PagedCache, block_kv_gather
from .chain import (
    ZERO,
    Receipt,
    ReceiptChain,
    UnifiedReceiptChain,
    canon,
    chain_depth,
    mint_receipt,
    sha256_hex,
    verify_receipt,
    write_training_receipt,
)
from .doctrine import (
    CONJECTURE_1,
    DOCTRINE,
    ENERGY_POLICY,
    LOCKED_EIGHT,
    YUYAY_AXES,
    YUYAY_FLOORS,
    advisory,
    proven_trust,
)
from .formulas import ayni_ok, fifo_ok, run_all
from .governed_norm import layer_norm, rms_norm
from .lambda_gate import (
    LambdaEval,
    check_a1,
    check_a2,
    check_a3,
    check_a4,
    check_a5,
    evaluate_lambda,
    lambda_gate,
    wgm,
    yuyay_weights,
)
from .maskmod import causal_mask, future_mass, maskmod_attn, prefix_mask, sliding_mask
from .ouroboros import OUROBOROS_SELFCHECK, loop_tax
from .receipt_attn import naive_attn, tiled_attn
from .train import mini_embed, moons, receipt_agent, tiny_khipu
from .yarqa import canal_bounds, leaked_attn, yarqa_attn
from .anatomy import (
    ORGAN_SPEC,
    WILLAY_CLASSIFIERS,
    AnatomyEval,
    anatomy_metrics,
    evaluate_anatomy,
)
from .tilegrid import digest_tiles, run_tile_grid, schedule_cover, tile_schedule
from .chaski import drain, enqueue_all, run_chaski
from .ayni import run_ayni
from .shard import SHARD_K, SHARD_N, decode_rs, encode_rs, run_shard
from .bay import BAY_RAILS, evaluate_bay, run_bay
from .greenlight import evaluate_greenlight, run_greenlight

__version__ = "0.1.0"


class _Result(dict[str, Any]):
    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def train_tiny_khipu(seed: int = 20260721, steps: int = 280, **kwargs: Any) -> _Result:
    weights, ev = tiny_khipu.train(seed=seed, steps=steps, **kwargs)
    return _Result(weights=weights, **ev)


def eval_tiny_khipu(weights: dict, data: list | None = None) -> _Result:
    if data is None:
        data = tiny_khipu.synth_curriculum(16, seed=20260721)
    return _Result(**tiny_khipu.evaluate(weights, data))


def save_tiny_khipu(path: str, weights: dict) -> None:
    tiny_khipu.save_npz(path, weights)


class TinyKhipu:
    def __init__(self, seed: int = 20260721) -> None:
        self.weights = tiny_khipu.init_weights(seed)

    def train(self, seed: int = 20260721, steps: int = 280, **kwargs: Any) -> _Result:
        result = train_tiny_khipu(seed=seed, steps=steps, **kwargs)
        self.weights = result["weights"]
        return result

    def forward(self, example: dict[str, Any]) -> dict[str, Any]:
        return tiny_khipu.forward(self.weights, example)


def train_receipt_agent(seed: int = 7, max_steps: int = 400, **kwargs: Any) -> _Result:
    weights, ev = receipt_agent.train(seed=seed, max_steps=max_steps, **kwargs)
    return _Result(weights=weights, **ev)


class ReceiptAgent:
    def __init__(self, seed: int = 7) -> None:
        self.weights = receipt_agent.init_weights(seed)

    def train(self, seed: int = 7, max_steps: int = 400, **kwargs: Any) -> _Result:
        result = train_receipt_agent(seed=seed, max_steps=max_steps, **kwargs)
        self.weights = result["weights"]
        return result

    def predict(self, features: Any) -> Any:
        return receipt_agent.predict(self.weights, features)

    def decide(self, features: Any) -> dict[str, Any]:
        return receipt_agent.decide(features, self.weights)


def train_moons(seed: int = 7, steps: int = 400, **kwargs: Any) -> _Result:
    weights, ev = moons.train(seed=seed, steps=steps, **kwargs)
    return _Result(weights=weights, **ev)


__all__ = [
    "__version__",
    "DOCTRINE",
    "YUYAY_AXES",
    "YUYAY_FLOORS",
    "LOCKED_EIGHT",
    "CONJECTURE_1",
    "ENERGY_POLICY",
    "proven_trust",
    "advisory",
    "canon",
    "sha256_hex",
    "Receipt",
    "ZERO",
    "UnifiedReceiptChain",
    "ReceiptChain",
    "mint_receipt",
    "verify_receipt",
    "write_training_receipt",
    "chain_depth",
    "wgm",
    "yuyay_weights",
    "check_a1",
    "check_a2",
    "check_a3",
    "check_a4",
    "check_a5",
    "evaluate_lambda",
    "lambda_gate",
    "LambdaEval",
    "canal_bounds",
    "yarqa_attn",
    "leaked_attn",
    "naive_attn",
    "tiled_attn",
    "causal_mask",
    "sliding_mask",
    "prefix_mask",
    "maskmod_attn",
    "future_mass",
    "PagedCache",
    "block_kv_gather",
    "rms_norm",
    "layer_norm",
    "loop_tax",
    "OUROBOROS_SELFCHECK",
    "deny_by_default",
    "four_way_gate",
    "run_all",
    "fifo_ok",
    "ayni_ok",
    "train_tiny_khipu",
    "eval_tiny_khipu",
    "save_tiny_khipu",
    "TinyKhipu",
    "train_receipt_agent",
    "ReceiptAgent",
    "train_moons",
    "tiny_khipu",
    "receipt_agent",
    "moons",
    "mini_embed",
    "evaluate_anatomy",
    "anatomy_metrics",
    "AnatomyEval",
    "ORGAN_SPEC",
    "WILLAY_CLASSIFIERS",
    "digest_tiles",
    "run_tile_grid",
    "schedule_cover",
    "tile_schedule",
    "enqueue_all",
    "drain",
    "run_chaski",
    "run_ayni",
    "SHARD_N",
    "SHARD_K",
    "encode_rs",
    "decode_rs",
    "run_shard",
    "BAY_RAILS",
    "evaluate_bay",
    "run_bay",
    "evaluate_greenlight",
    "run_greenlight",
]
