"""Public Wave 8 facade for bounded KHIPU-X1 causal-LM references."""

from .causal_lm_mapping import (
    CausalLMMappingError,
    CausalLMTensorNames,
    MappedCausalLM,
    map_causal_lm,
)
from .causal_lm_reference import (
    CausalLMReferenceError,
    CausalLMResult,
    CausalLMWeights,
    GreedyGenerationResult,
    greedy_generate,
    greedy_next_token,
    run_causal_lm,
)

__all__ = [
    "CausalLMMappingError",
    "CausalLMReferenceError",
    "CausalLMResult",
    "CausalLMTensorNames",
    "CausalLMWeights",
    "GreedyGenerationResult",
    "MappedCausalLM",
    "greedy_generate",
    "greedy_next_token",
    "map_causal_lm",
    "run_causal_lm",
]
