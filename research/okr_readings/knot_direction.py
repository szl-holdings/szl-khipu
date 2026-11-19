#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Is a knot's S/Z direction set by its type inside each khipu?

Knot direction has been proposed as a binary sign (Urton 2003).  Before asking
what it might mean, this test asks how much of its recorded variation inside a
khipu is left once the knot's type (single, long, figure-eight) is known.  Each
knot with a recorded direction is hidden in turn and predicted from the other
knots of the same khipu, first from the khipu's own frequencies, then knowing
the knot's type, then its type and turn count.  Shuffling directions among the
khipu's knots gives the control.

A saving shows a statistical link in the transcription.  It does not say what
direction meant, and the choice of contexts was made after looking at the data.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
from collections import Counter
from math import fsum, log2
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEALED = HERE / "knot_direction_v1.json"
SCHEMA = "szl.okr.knot-direction/v1"
MIN_KNOTS = 20
TRIALS = 100
SEED = 2026
CONTEXTS = {"type": lambda k: k[0], "type_and_turns": lambda k: (k[0], k[1])}


def _module(name: str):
    spec = importlib.util.spec_from_file_location(f"szl_okr_knot_direction_{name}", HERE / f"{name}.py")
    if spec is None or spec.loader is None:
        raise ValueError("MODULE_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_FEATURES = _module("build_features")
_HIDDEN = _module("hidden_cord")
digest = _HIDDEN.digest


def knots_digest() -> str:
    return _FEATURES.KNOTS_SHA256


def directed_knots(cords: list) -> list:
    return [k for cord in cords for k in cord if k[2] in ("S", "Z")]


def majority_hits(knots: list, key) -> int:
    """How many knots carry the commonest direction among knots sharing their key."""
    groups: dict = {}
    for k in knots:
        groups.setdefault(key(k), Counter())[k[2]] += 1
    return sum(max(c.values()) for c in groups.values())


def bits(knots: list, key, prior: dict) -> float:
    """Leave-one-out cost of the directions, given each knot's key (None = khipu only)."""
    return _HIDDEN.bits_context([key(k) for k in knots], [k[2] for k in knots], prior)


def audit(trials: int = TRIALS) -> dict:
    record = _FEATURES.load_knots()
    khipus = {name: directed_knots(_FEATURES.cord_knots(entry))
              for name, entry in record["khipus"].items()}
    corpus_counts = Counter(k[2] for knots in khipus.values() for k in knots)
    total = sum(corpus_counts.values())
    names = sorted(n for n, knots in khipus.items() if len(knots) >= MIN_KNOTS)
    n_knots = bits_corpus = bits_base = 0.0
    obs = dict.fromkeys(CONTEXTS, 0.0)
    null = {c: [0.0] * trials for c in CONTEXTS}
    hits = {"khipu": 0, "type": 0, "type_and_turns": 0}
    both = 0
    for name in names:
        knots = khipus[name]
        own = Counter(k[2] for k in knots)
        prior = {v: (corpus_counts[v] - own[v] + 1) / (total - len(knots) + 2) for v in ("S", "Z")}
        base = _HIDDEN.bits_khipu([k[2] for k in knots], prior)
        n_knots += len(knots)
        bits_corpus += -fsum(c * log2(prior[v]) for v, c in own.items())
        bits_base += base
        both += len(own) == 2
        hits["khipu"] += majority_hits(knots, lambda k: None)
        for c, key in CONTEXTS.items():
            obs[c] += base - bits(knots, key, prior)
            hits[c] += majority_hits(knots, key)
        for trial in range(trials):
            rng = random.Random(f"{SEED}|{name}|{trial}")
            directions = [k[2] for k in knots]
            rng.shuffle(directions)
            mixed = [(k[0], k[1], d) for k, d in zip(knots, directions)]
            for c, key in CONTEXTS.items():
                null[c][trial] += base - bits(mixed, key, prior)
    n = int(n_knots)
    contexts = {}
    for c in CONTEXTS:
        row = _HIDDEN._stats(obs[c], null[c], n)
        contexts[c] = {("gain_bits_per_knot" if k == "gain_bits_per_cord" else
                        "excess_bits_per_knot" if k == "excess_bits_per_cord" else k): v
                       for k, v in row.items()}
    report = {
        "schema": SCHEMA,
        "status": "POST_HOC_EXPLORATORY_INFORMATION_TEST",
        "input_knots_sha256": knots_digest(),
        "input_corpus_sha256": record["corpus_sha256"],
        "upstream_okr_revision": record["source"]["commit"],
        "preregistered": False,
        "historical_khipu_decipherment": False,
        "meaning_assigned_to_any_feature": False,
        "signature_verified": False,
        "parameters": {"min_directed_knots_per_khipu": MIN_KNOTS, "trials": trials, "seed": SEED,
                       "alpha": _HIDDEN.ALPHA, "gamma": _HIDDEN.GAMMA,
                       "unit": "knots with a recorded S or Z direction, on cords of any level"},
        "khipus": len(names), "knots": n, "khipus_with_both_directions": both,
        "bits_per_knot_corpus": round(bits_corpus / n, 4),
        "bits_per_knot_khipu": round(bits_base / n, 4),
        "majority_accuracy": {k: round(v / n, 4) for k, v in hits.items()},
        "contexts": contexts,
        "reading_the_numbers": [
            ("majority_accuracy is the share of knots that carry the commonest direction of their "
             "khipu, of their knot type in that khipu, and of their type and turn count."),
            ("gain_bits_per_knot is the saving over the khipu's own direction frequencies; the "
             "null repeats it with directions shuffled among the khipu's knots."),
            ("Direction is recorded per knot by the cataloguer. Agreement between type and "
             "direction can reflect how knots are tied as well as how they were written down."),
        ],
    }
    report["report_sha256"] = digest(report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="write the sealed report")
    parser.add_argument("--check", action="store_true", help="compare with the sealed report")
    args = parser.parse_args(argv)
    report = audit()
    text = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    if args.write:
        SEALED.write_text(text, encoding="utf-8")
    if args.check:
        same = json.loads(SEALED.read_text(encoding="utf-8")) == json.loads(text)
        print("REPLAY_MATCH" if same else "HOLD: sealed report differs from recomputation")
        return 0 if same else 1
    print(json.dumps({k: report[k] for k in ("khipus", "knots", "khipus_with_both_directions",
                                             "bits_per_knot_corpus", "bits_per_knot_khipu",
                                             "majority_accuracy", "contexts")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
