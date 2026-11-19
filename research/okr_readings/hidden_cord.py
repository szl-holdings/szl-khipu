#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Hidden-cord information test on the pinned OKR records.

Hide one recorded feature of one pendant cord, predict it from the rest of the
same khipu, and count the bits saved by each kind of context: the neighbouring
cords, the cord's position in its cluster, or another feature of the same cord.
Then shuffle the hidden feature among the cords of each khipu and repeat, so
every saving is compared with what unstructured cords would give.

The models are small count tables fitted inside each khipu with the scored cord
left out.  A saving means the recorded features are statistically linked in the
transcription.  It does not say what any feature meant to the people who made
the khipu, and the choice of features, contexts and thresholds was made after
looking at the corpus.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
from collections import Counter
from itertools import groupby
from math import fsum, log2
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "szl_khipu/okr_khipu.py"
FEATURES = Path(__file__).with_name("build_features.py")
SEALED = Path(__file__).with_name("hidden_cord_v1.json")
SCHEMA = "szl.okr.hidden-cord-information/v1"
CORPUS_SHA256 = "6ef204b641826b37c320509952ed4181e93865af20f1cdfefd7516a49cf8ad0d"
TARGETS = ("colour", "attach", "spin", "knot_dir", "fibre", "value_class")
STRUCTURE = ("neighbours", "position")
# A cord has a knot direction only if it has knots, so each of these two
# features gives the other away by definition rather than by convention.
DEFINITIONAL = (("value_class", "knot_dir"), ("knot_dir", "value_class"))
SANTA = ("KH0323", "KH0324", "KH0325", "KH0326", "KH0327", "KH0328")
ALPHA = 1.0
GAMMA = 1.0
MIN_RECORDED = 12
POSITION_CAP = 12
TRIALS = 100
SEED = 2026
LEFT_EDGE, RIGHT_EDGE, UNRECORDED = ("^",), ("$",), ("?",)


class Hold(ValueError):
    """Refuse inputs this test was not written for."""


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")


def digest(report: dict) -> str:
    body = {k: v for k, v in report.items() if k != "report_sha256"}
    return hashlib.sha256(canonical(body)).hexdigest()


def _module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Hold("MODULE_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def contexts_for(target: str) -> tuple:
    return STRUCTURE + tuple(g for g in TARGETS if g != target and (target, g) not in DEFINITIONAL)


def value_class(value, status):
    if status == "unknown":
        return None
    if value == 0:
        return "0"
    if value < 10:
        return "1-9"
    if value < 100:
        return "10-99"
    if value < 1000:
        return "100-999"
    return "1000+"


def runs(ids: list) -> list:
    """(start, end) of each stretch of consecutive equal ids."""
    out, start = [], 0
    for _, members in groupby(ids):
        n = sum(1 for _ in members)
        out.append((start, start + n))
        start += n
    return out


def shuffle_within(column: list, spans: list, rng) -> list:
    """Shuffle recorded values among the recorded slots of each span; gaps stay put."""
    out = list(column)
    for a, b in spans:
        slots = [i for i in range(a, b) if column[i] is not None]
        values = [column[i] for i in slots]
        rng.shuffle(values)
        for i, v in zip(slots, values):
            out[i] = v
    return out


def positions(clusters: list) -> list:
    out = []
    for _, members in groupby(clusters):
        out.extend(min(i, POSITION_CAP) for i, _ in enumerate(members))
    return out


def _held_out(values: list, prior: dict) -> dict:
    """P(value) for a cord of that value once it is removed from its khipu's counts."""
    counts, n = Counter(values), len(values)
    return {v: (c - 1 + ALPHA * prior[v]) / (n - 1 + ALPHA) for v, c in counts.items()}


def bits_khipu(values: list, prior: dict) -> float:
    held = _held_out(values, prior)
    return -fsum(c * log2(held[v]) for v, c in Counter(values).items())


def bits_context(keys: list, values: list, prior: dict) -> float:
    """Cost when each cord is predicted from the other cords sharing its context key."""
    held = _held_out(values, prior)
    by_key = Counter(keys)
    return -fsum(c * log2((c - 1 + GAMMA * held[v]) / (by_key[u] - 1 + GAMMA))
                 for (u, v), c in Counter(zip(keys, values)).items())


def _neighbour_keys(segments: list) -> list:
    keys = []
    for seg in segments:
        last = len(seg) - 1
        keys.append([
            (LEFT_EDGE if i == 0 else UNRECORDED if seg[i - 1] is None else seg[i - 1],
             RIGHT_EDGE if i == last else UNRECORDED if seg[i + 1] is None else seg[i + 1])
            for i in range(len(seg))])
    return keys


def _neighbour_tables(segments: list):
    keys = _neighbour_keys(segments)
    by_key, cells, values = Counter(), Counter(), []
    for seg, ks in zip(segments, keys):
        for v, u in zip(seg, ks):
            if v is not None:
                by_key[u] += 1
                cells[(u, v)] += 1
                values.append(v)
    return keys, by_key, cells, values


def _neighbour_p(seg, ks, i, by_key, cells, held) -> float:
    v, u = seg[i], ks[i]
    cu, cuv = by_key[u] - 1, cells[(u, v)] - 1
    # The two adjacent cords are observed in contexts that contain the hidden
    # value, so a predictor that cannot see it cannot use them either.
    for j in (i - 1, i + 1):
        if 0 <= j < len(seg) and seg[j] is not None and ks[j] == u:
            cu -= 1
            if seg[j] == v:
                cuv -= 1
    return (cuv + GAMMA * held[v]) / (cu + GAMMA)


def neighbour_prob(segments: list, s: int, i: int, prior: dict) -> float:
    keys, by_key, cells, values = _neighbour_tables(segments)
    return _neighbour_p(segments[s], keys[s], i, by_key, cells, _held_out(values, prior))


def bits_neighbours(segments: list, prior: dict) -> float:
    """Cost when each cord is predicted from the values on either side of it."""
    keys, by_key, cells, values = _neighbour_tables(segments)
    if not values:
        return 0.0
    held = _held_out(values, prior)
    return -fsum(log2(_neighbour_p(seg, ks, i, by_key, cells, held))
                 for seg, ks in zip(segments, keys)
                 for i, v in enumerate(seg) if v is not None)


def _columns(khipu: dict, feat: dict) -> dict:
    idx = [i for i, c in enumerate(khipu["cords"]) if c["level"] == 1 and c["parent_kind"] == "primary"]
    cords = [khipu["cords"][i] for i in idx]
    knot_raw = [feat["knot_dir"][i] for i in idx]
    target = {
        "colour": [c["color"] or None for c in cords],
        "attach": [c["attach"] if c["attach"] in ("R", "V") else None for c in cords],
        "spin": [feat["spin"][i] if feat["spin"][i] in "SZ" else None for i in idx],
        "knot_dir": [k if k in "SZM" else None for k in knot_raw],
        "fibre": [feat["fibre"][i] if feat["fibre"][i] != "U" else None for i in idx],
        "value_class": [value_class(c["value"], c["value_status"]) for c in cords],
    }
    context = {name: ["?" if v is None else v for v in col] for name, col in target.items()}
    # As context, "no knots" and "knots of unrecorded direction" stay distinct.
    context["knot_dir"] = knot_raw
    clusters = [c["cluster"] for c in cords]
    context["position"] = positions(clusters)
    return {"okr_num": khipu["okr_num"], "target": target, "context": context,
            "segments": runs([c["parent"] for c in cords]), "clusters": runs(clusters)}


def _segments(column: list, bounds: list) -> list:
    return [column[a:b] for a, b in bounds]


def _feature_costs(table: dict, contexts: tuple, values_at: list, prior: dict) -> dict:
    recorded = [i for i, v in enumerate(values_at) if v is not None]
    values = [values_at[i] for i in recorded]
    return {c: bits_context([table["context"][c][i] for i in recorded], values, prior)
            for c in contexts}


def _costs(table: dict, target: str, values_at: list, prior: dict) -> dict:
    """Cost of every context for one khipu; `values_at` is the (possibly shuffled) column."""
    out = _feature_costs(table, contexts_for(target)[1:], values_at, prior)
    out["neighbours"] = bits_neighbours(_segments(values_at, table["segments"]), prior)
    return out


def _verdict(gain: float, null_max: float) -> str:
    if gain <= null_max:
        return "NOT_ABOVE_SHUFFLE_NULL"
    # A link can beat every shuffle and still cost more bits than it saves in
    # these small models, because a context splits the khipu's counts.
    return "ABOVE_SHUFFLE_NULL_NET_SAVING" if gain > 0 else "ABOVE_SHUFFLE_NULL_NO_NET_SAVING"


def _null(null_bits: list, cords: int):
    null = [round(b / cords, 4) for b in null_bits]
    mean = round(fsum(null) / len(null), 4)
    sd = (fsum((x - mean) ** 2 for x in null) / (len(null) - 1)) ** 0.5 if len(null) > 1 else 0.0
    return null, mean, round(sd, 4)


def _stats(obs_bits: float, null_bits: list, cords: int, cluster_bits: list | None = None) -> dict:
    gain = round(obs_bits / cords, 4)
    row = {"gain_bits_per_cord": gain, "null_mean": None, "null_sd": None, "null_max": None,
           "excess_bits_per_cord": None, "p_upper": None, "verdict": None}
    if null_bits:
        null, mean, sd = _null(null_bits, cords)
        row.update({
            "null_mean": mean, "null_sd": sd, "null_max": max(null),
            "excess_bits_per_cord": round(gain - mean, 4),
            "p_upper": round((1 + sum(x >= gain for x in null)) / (len(null) + 1), 4),
            "verdict": _verdict(gain, max(null)),
        })
    if cluster_bits:
        null, mean, _ = _null(cluster_bits, cords)
        # Stricter control for feature-to-feature links: values move only inside
        # their own cord cluster, so a link that merely follows the khipu's
        # sections disappears here.
        row.update({
            "cluster_null_mean": mean, "cluster_null_max": max(null),
            "excess_within_cluster": round(gain - mean, 4),
            "survives_within_cluster_shuffle": gain > max(null),
        })
    return row


def _target_report(tables: list, target: str, trials: int):
    corpus_counts = Counter(v for t in tables for v in t["target"][target] if v is not None)
    alphabet, total = len(corpus_counts), sum(corpus_counts.values())
    contexts = contexts_for(target)
    features = tuple(c for c in contexts if c not in STRUCTURE)
    obs = dict.fromkeys(contexts, 0.0)
    null = {c: [0.0] * trials for c in contexts}
    strict = {c: [0.0] * trials for c in features}
    bits_corpus = bits_base = 0.0
    khipus = cords = 0
    santa = {}
    for table in tables:
        column = table["target"][target]
        values = [v for v in column if v is not None]
        if len(values) < MIN_RECORDED:
            continue
        own = Counter(values)
        # Corpus frequencies with this khipu removed, so no khipu informs its own prior.
        prior = {v: (corpus_counts[v] - own[v] + 1) / (total - len(values) + alphabet) for v in own}
        base = bits_khipu(values, prior)
        khipus += 1
        cords += len(values)
        bits_corpus += -fsum(c * log2(prior[v]) for v, c in own.items())
        bits_base += base
        seen = _costs(table, target, column, prior)
        own_null = {c: [] for c in contexts}
        own_strict = {c: [] for c in features}
        for c in contexts:
            obs[c] += base - seen[c]
        whole = [(0, len(column))]
        for trial in range(trials):
            tag = f"{SEED}|{table['okr_num']}|{target}|{trial}"
            mixed = _costs(table, target, shuffle_within(column, whole, random.Random(tag)), prior)
            for c in contexts:
                null[c][trial] += base - mixed[c]
                own_null[c].append(base - mixed[c])
            inside = shuffle_within(column, table["clusters"], random.Random(tag + "|cluster"))
            for c, cost in _feature_costs(table, features, inside, prior).items():
                strict[c][trial] += base - cost
                own_strict[c].append(base - cost)
        if table["okr_num"] in SANTA:
            santa[table["okr_num"]] = {
                "cords": len(values),
                "contexts": {c: _stats(base - seen[c], own_null[c], len(values), own_strict.get(c))
                             for c in contexts}}
    if not cords:
        raise Hold(f"NO_ELIGIBLE_KHIPU:{target}")
    block = {
        "khipus": khipus, "cords": cords, "alphabet_size": alphabet,
        "bits_per_cord_corpus": round(bits_corpus / cords, 4),
        "bits_per_cord_khipu": round(bits_base / cords, 4),
        "contexts": {c: _stats(obs[c], null[c], cords, strict.get(c)) for c in contexts},
    }
    return block, santa


def audit(trials: int = TRIALS, targets: tuple = TARGETS) -> dict:
    corpus = _module(ENGINE, "szl_okr_hidden_cord_engine").load_corpus()
    if corpus.get("sha256") != CORPUS_SHA256:
        raise Hold("CORPUS_DIGEST_NOT_PINNED")
    builder = _module(FEATURES, "szl_okr_hidden_cord_features")
    features = builder.load_features()
    if features["corpus_sha256"] != corpus["sha256"]:
        raise Hold("FEATURES_BUILT_FROM_ANOTHER_CORPUS")
    tables = [_columns(k, features["khipus"][k["okr_num"]]) for k in corpus["khipus"]]
    report = {
        "schema": SCHEMA,
        "status": "POST_HOC_EXPLORATORY_INFORMATION_TEST",
        "input_corpus_sha256": corpus["sha256"],
        "input_features_sha256": builder.SHIPPED_SHA256,
        "upstream_okr_revision": corpus["source"]["commit"],
        "preregistered": False,
        "historical_khipu_decipherment": False,
        "meaning_assigned_to_any_feature": False,
        "neural_model_evaluated": False,
        "independent_research_lab_replication": False,
        "signature_verified": False,
        "parameters": {"alpha": ALPHA, "gamma": GAMMA, "min_recorded_cords_per_khipu": MIN_RECORDED,
                       "position_cap": POSITION_CAP, "trials": trials, "seed": SEED,
                       "unit": "level-1 pendant cords attached to a primary cord"},
        "definitional_pairs_not_scored": [list(p) for p in DEFINITIONAL],
        "reading_the_numbers": [
            ("gain_bits_per_cord is the saving over predicting the cord from its khipu's own "
             "frequencies; it can be negative when a context splits the counts without helping."),
            ("null_* repeat the measurement after shuffling the hidden feature among the cords "
             "of each khipu; p_upper cannot go below 1/(trials+1)."),
            ("excess_bits_per_cord is the gain minus the shuffle mean: the part of the saving "
             "that depends on which cord carries which value."),
            ("cluster_null_* and excess_within_cluster repeat that for feature-to-feature links "
             "with values shuffled only inside their own cord cluster."),
            ("A recorded link can come from how a khipu was made, how it survived, or how it was "
             "catalogued. This test cannot tell those apart."),
        ],
        "targets": {}, "santa_valley": {},
    }
    for target in targets:
        block, santa = _target_report(tables, target, trials)
        report["targets"][target] = block
        for okr_num, row in santa.items():
            report["santa_valley"].setdefault(okr_num, {})[target] = row
    report["santa_valley"] = dict(sorted(report["santa_valley"].items()))
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
    for target, block in report["targets"].items():
        for context, row in block["contexts"].items():
            inside = row.get("excess_within_cluster")
            print(f"{target:<12} | {context:<12} gain {row['gain_bits_per_cord']:>8.4f} "
                  f"excess {row['excess_bits_per_cord']:>8.4f} "
                  f"in-cluster {'' if inside is None else format(inside, '8.4f'):>8}  {row['verdict']}"
                  f"{'' if inside is None or row['survives_within_cluster_shuffle'] else '  (not inside clusters)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
