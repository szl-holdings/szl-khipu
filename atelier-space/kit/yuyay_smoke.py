# szl_khipu/lambda_gate.py — WGM fail-closed. Conjecture 1 OPEN.
from szl_khipu.lambda_gate import wgm, lambda_gate

axes = [0.9, 0.8, 0.7, 0.85, 0.6]
ev = lambda_gate(axes, threshold=0.5)
print(ev.score, ev.passed, ev.proven_trust)
assert wgm([0.9, 0.0, 0.7], [1 / 3, 1 / 3, 1 / 3]) == 0.0
print("ok")
