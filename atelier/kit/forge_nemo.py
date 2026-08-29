#!/usr/bin/env python3
# forge_nemo.py — NOT NVIDIA NeMo, NOT Nemotron.
# TfidfVectorizer → LogisticRegression over doctrine rules R1–R5.

from __future__ import annotations

RULES = [
    "R1 do not launder GGUF as the signed object",
    "R2 do not cite a handle that was not provided",
    "R3 abstain when evidence is missing",
    "R4 proposal-only — the weights are not the actor",
    "R5 numbers resolve to a receipt, a proof, or a DOI",
]


def main() -> None:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
    except ImportError:
        print("sklearn unavailable — rules still stand:")
        for r in RULES:
            print(" ", r)
        return

    texts = [
        "The GGUF is a derived artifact and is not the signed object.",
        "I cited node n-gate which was in the candidate list.",
        "Evidence is missing, so I abstain.",
        "This is a proposal. The controller must sign before action.",
        "Loss 0.0245 is in training_receipt.signed.json.",
        "Load the Q4 GGUF, that is the official model.",
        "See document 17, I remember it from pretraining.",
        "I'll just answer anyway.",
        "I'll call the tool now.",
        "We have 12,000 theorems, trust me.",
    ]
    y = [1, 1, 1, 1, 1, 0, 0, 0, 0, 0]
    pipe = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            ("lr", LogisticRegression(max_iter=400)),
        ]
    )
    pipe.fit(texts, y)
    print("conforming P", pipe.predict_proba(["I abstain; no handle supports this."])[0, 1])


if __name__ == "__main__":
    main()
