# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""RimayWitness — sealed utterance. Original cut.

Spoken tokens are sealed. Paraphrase or drop a word after the rimay
digest fail-closes. Not ASR. Not a transcript. Not EchoWitness.
"""

from __future__ import annotations

from typing import Any

from .chaski import djb2

RIMAY_WORDS: tuple[str, ...] = ("kay", "pacha", "kawsay")


def run_rimay(seed: int = 11, mode: int = 0) -> dict[str, Any]:
    sealed = list(RIMAY_WORDS)
    digest = djb2(f"{int(seed)}|" + " ".join(sealed))
    live = list(sealed)
    if mode == 1:
        live[1] = "mundo"
    if mode == 2:
        live.pop()
    now = djb2(f"{int(seed)}|" + " ".join(live))
    same = " ".join(live) == " ".join(RIMAY_WORDS)
    hold = 1 if now == digest and same and mode == 0 else 0
    if hold:
        reason = "RimayWitness HOLDS · utterance sealed · not ASR · not a transcript · not EchoWitness"
    elif mode == 1:
        reason = "RimayWitness BROKEN · utterance paraphrased after seal · fail closed"
    else:
        reason = "RimayWitness BROKEN · spoken word dropped after seal · fail closed · not a silent rewrite"
    return {
        "hold": hold,
        "broken": 0 if hold else 1,
        "words": live,
        "claimed": list(RIMAY_WORDS),
        "digest": digest,
        "now": now,
        "mode": mode,
        "reason": reason,
        "what_not": "Not ASR. Not a transcript. Not EchoWitness. Original cut.",
    }
