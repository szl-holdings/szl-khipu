# szl_khipu/yarqa.py — canal-local softmax. Cross-canal leak ~0.
from szl_khipu.yarqa import yarqa_attn, canal_bounds
import numpy as np

rng = np.random.default_rng(7)
S, D, N = 8, 4, 3
Q = rng.normal(size=(S, D))
K = rng.normal(size=(S, D))
V = rng.normal(size=(S, D))
out, probs, leaked = yarqa_attn(Q, K, V, n_canals=N)
print("bounds", canal_bounds(S, N))
print("leaked", leaked)
assert leaked < 1e-12
print("ok")
