# szl_khipu/maskmod.py — future tokens get zero, not 0.1.
from szl_khipu.maskmod import maskmod_attn
import numpy as np

rng = np.random.default_rng(11)
n, d = 8, 4
Q, K, V = rng.normal(size=(n, d)), rng.normal(size=(n, d)), rng.normal(size=(n, d))
out, probs, fm = maskmod_attn(Q, K, V, kind="causal")
print("future_mass", fm)
assert fm < 1e-12
print("ok")
