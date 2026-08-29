#!/usr/bin/env python3
# Kernels are code, not checkpoints. Smoke proves import + fail-closed.


def lambda_gate(trust: float, lam: float) -> str:
    return "OPEN" if trust >= lam else "CLOSED"


def maskmod(weights, authorized_mask):
    return [w if a else 0.0 for w, a in zip(weights, authorized_mask)]


if __name__ == "__main__":
    assert lambda_gate(0.61, 0.62) == "CLOSED"
    assert lambda_gate(0.62, 0.62) == "OPEN"
    assert maskmod([0.9, 0.8, 0.7], [1, 0, 1]) == [0.9, 0.0, 0.7]
    print("ok")
