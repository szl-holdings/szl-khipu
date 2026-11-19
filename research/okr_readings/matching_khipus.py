#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Find khipus that carry the same run of numbers, and see what else was copied.

Urton (2005) described "matching khipus": pairs or triplets with identical or
nearly identical number sequences, read as duplicate accounts kept as a check.
Known examples were found by eye.  This module searches the pinned OKR corpus
for them by aligning pendant-value sequences, keeps a pair only if its
alignment beats every shuffle of one khipu's cord order, and then asks of each
kept pair: where two cords carry the same number, do they also share colour,
attachment, spin, fibre, termination or knot direction more often than cords
paired at random, and does that survive holding the number fixed?

Some pairs turn out to be one khipu entered twice: the main cords are the same
length and matched cords agree to a centimetre or two.  Those are flagged and
kept apart, because there the comparison measures two recordings of one object,
not two khipus.

Nothing here says what a feature meant.  A pair is a candidate until someone
checks the objects; the pinned records cannot rule out one record typed from
another.  Thresholds were set after looking at the data.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import importlib.util
import json
import random
from collections import Counter, defaultdict
from math import comb, log2
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ENGINE = ROOT / "szl_khipu/okr_khipu.py"
SEALED = HERE / "matching_khipus_v1.json"
SCHEMA = "szl.okr.matching-khipus/v1"
CORPUS_SHA256 = "6ef204b641826b37c320509952ed4181e93865af20f1cdfefd7516a49cf8ad0d"
FEATURES = ("colour", "attach", "spin", "fibre", "term", "long_knot_dir", "single_knot_dir")
KHIPU_LEVEL = ("attach", "spin", "long_knot_dir", "single_knot_dir")
OPPOSITES = ({"R", "V"}, {"S", "Z"})
MISMATCH, GAP = -4.0, -3.0
TRIGRAM_BITS = 20.0
RARE_BITS = 9.0
MIN_SCORE = 40.0
MIN_EXACT = 8
MAX_CELLS = 400_000
N_ORDER = 100
N_FIDELITY = 500
SEED = 2026
# One object entered twice: main cords within 5%, matched cords within 3 cm at the median.
ONE_OBJECT_PRIMARY_TOL = 0.05
ONE_OBJECT_MAX_DIFF_CM = 3.0
ONE_OBJECT_MIN_CORDS = 8
# Pairs described as matching in the Puruchuco literature (Urton and Brezine 2005).
KNOWN = (("UR064", "UR068"), ("UR066", "UR067"), ("UR063", "UR073"))
_SNIPPET = "search-engine summary of the page, 2026-11-19; the page itself was not reachable from this environment"
# What the Khipu Field Guide (Ashok Khosla) and the OKR records already say about pairs found here.
PRIOR_ART = (
    {"pair": [], "kind": "method", "source": "https://khipufieldguide.com/notebook/appendix/notebooks/"
     "07 - Removing Duplicate Khipus.html",
     "says": "an earlier duplicate-khipu search on the KFG database; duplicates were removed from that database",
     "seen_via": _SNIPPET},
    {"pair": ["UR1107", "UR237"], "kind": "listed_duplicate",
     "source": "https://www.khipufieldguide.com/sketchbook/khipus/KH0121/html/KH0121_sketch.html",
     "says": "KH0473 (UR237) was identified by Winston Wright as a duplicate of KH0121 (UR1107, AS107)",
     "seen_via": _SNIPPET},
    {"pair": ["AS125", "UR247"], "kind": "listed_duplicate",
     "source": "https://www.khipufieldguide.com/sketchbook/khipus/AS125/html/AS125_sketch.html",
     "says": "UR247 is a duplicate of AS125 and has been reconciled with it (KH0140)",
     "seen_via": _SNIPPET},
    {"pair": ["UR232", "UR233"], "kind": "physical_join",
     "source": "https://www.khipufieldguide.com/catalog/KH0469.html",
     "says": "UR232 primary cord notes: beginning end spliced with UR 233",
     "seen_via": _SNIPPET},
    {"pair": ["UR255", "UR267A"], "kind": "okr_note", "source": "pinned OKR database, khipu_main.NOTES",
     "says": "UR255: 'UR267 A match'; UR267A: \"UR255 'Match'\"", "seen_via": "read from the pinned database"},
    {"pair": ["UR256", "UR267B"], "kind": "okr_note", "source": "pinned OKR database, khipu_main.NOTES",
     "says": "UR256: 'UR 267-B Match'; UR267B: \"UR256 partial 'match'\"", "seen_via": "read from the pinned database"},
    {"pair": ["UR066", "UR067"], "kind": "okr_note", "source": "pinned OKR database, khipu_main.NOTES",
     "says": "UR067: 'UR66 and UR67 were wrapped together. They have matching numeric sequences.'",
     "seen_via": "read from the pinned database"},
    {"pair": ["AS038/HP036", "UR122"], "kind": "similarity_neighbour",
     "source": "https://www.khipufieldguide.com/catalog/KH0362.html",
     "says": "the KH0362 (UR122) page names KH0049 (AS038/HP036) as its previous 'similar khipu'",
     "seen_via": _SNIPPET},
)


class Hold(ValueError):
    """Refuse inputs this search was not written for."""


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


def _knot_family(code) -> str:
    global _ENGINE_FAMILY
    if _ENGINE_FAMILY is None:
        _ENGINE_FAMILY = _module(ENGINE, "szl_okr_matching_family").knot_family
    return _ENGINE_FAMILY(code)


_ENGINE_FAMILY = None


def _gain(x, y, info: dict) -> float:
    if x is None or y is None:
        return 0.0
    if x == y:
        return info[x]
    if x >= 10 and y >= 10 and abs(x - y) <= 1:
        return 0.5 * min(info[x], info[y])
    return MISMATCH


def align(a: list, b: list, info: dict) -> tuple:
    """Best local alignment of two value sequences: (score in bits, aligned index pairs).

    Equal values earn their rarity in bits, values one apart earn half, an
    unreadable cord earns nothing, a different value or a skipped cord costs.
    """
    width = len(b) + 1
    rows = [[0.0] * width]
    best, at = 0.0, (0, 0)
    for i, x in enumerate(a, 1):
        prev, cur = rows[-1], [0.0] * width
        worth = None if x is None else info[x]
        for j, y in enumerate(b, 1):
            # _gain(x, y, info), written out: this loop is where the search spends its time.
            if x is None or y is None:
                gain = 0.0
            elif x == y:
                gain = worth
            elif x >= 10 and y >= 10 and -1 <= x - y <= 1:
                gain = 0.5 * min(worth, info[y])
            else:
                gain = MISMATCH
            v = prev[j - 1] + gain
            skip = (prev[j] if prev[j] > cur[j - 1] else cur[j - 1]) + GAP
            if skip > v:
                v = skip
            if v > 0.0:
                cur[j] = v
                if v > best:
                    best, at = v, (i, j)
        rows.append(cur)
    pairs, (i, j) = [], at
    while i > 0 and j > 0 and rows[i][j] > 0:
        here = rows[i][j]
        if abs(here - (rows[i - 1][j - 1] + _gain(a[i - 1], b[j - 1], info))) < 1e-9:
            pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif abs(here - (rows[i - 1][j] + GAP)) < 1e-9:
            i -= 1
        else:
            j -= 1
    return best, pairs[::-1]


def bound(a: list, b: list, info: dict) -> tuple:
    """Ceilings on (alignment score, equal nonzero values) that cost one pass, not a table.

    Every cord aligns with at most one cord of the other khipu, so a value can
    earn full credit only as often as both khipus carry it, and half credit
    for the rest only if a value one away is present.
    """
    ca, cb = Counter(v for v in a if v is not None), Counter(v for v in b if v is not None)

    def ceiling(mine, theirs):
        total = 0.0
        for v, n in mine.items():
            equal = min(n, theirs[v])
            near = v >= 10 and (v + 1 in theirs or v - 1 >= 10 and v - 1 in theirs)
            total += info[v] * (equal + 0.5 * (n - equal) * near)
        return total

    return min(ceiling(ca, cb), ceiling(cb, ca)), sum(min(n, cb[v]) for v, n in ca.items() if v)


def seed_pairs(seqs: dict, info: dict) -> set:
    """Candidate (a, b, orientation) triples worth aligning, with a < b.

    Two khipus are seeded by a shared run of three values that is informative
    enough, read forwards or backwards, or by sharing at least three rare
    values (to within one) that make up a quarter of the smaller rare set.
    """
    forward, backward = defaultdict(set), defaultdict(set)
    rare = {}
    for name, seq in seqs.items():
        rare[name] = {v for v in seq if v is not None and info[v] >= RARE_BITS}
        for i in range(len(seq) - 2):
            tri = tuple(seq[i:i + 3])
            if None not in tri and sum(info[v] for v in tri) >= TRIGRAM_BITS:
                forward[tri].add(name)
                backward[tri[::-1]].add(name)
    seeds = set()
    for tri, names in forward.items():
        for a in names:
            seeds.update((a, b, "fwd") for b in names if a < b)
            seeds.update((a, b, "rev") for b in backward.get(tri, ()) if a < b)
    names = sorted(n for n, values in rare.items() if len(values) >= 3)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            shared = sum(1 for v in rare[a] if v in rare[b] or v - 1 in rare[b] or v + 1 in rare[b])
            if shared >= max(3, 0.25 * min(len(rare[a]), len(rare[b]))):
                seeds.update(((a, b, "fwd"), (a, b, "rev")))
    return seeds


def order_null(a: list, b: list, info: dict, trials: int, seed: str) -> dict:
    """Align a with shuffles of b's cord order: how often, and how nearly, they match b itself."""
    real = align(a, b, info)[0]
    rng = random.Random(seed)
    shuffled, scores = list(b), []
    for _ in range(trials):
        rng.shuffle(shuffled)
        scores.append(align(a, shuffled, info)[0])
    return {"p_order": round((1 + sum(x >= real for x in scores)) / (trials + 1), 4),
            "null_mean_bits": round(sum(scores) / trials, 1), "null_max_bits": round(max(scores), 1)}


def order_p(a: list, b: list, info: dict, trials: int, seed: str) -> float:
    """Share of shuffles of b's cord order that align with a at least as well as b does."""
    return order_null(a, b, info, trials, seed)["p_order"]


def _spearman(xs: list, ys: list) -> float:
    def ranks(values):
        order = sorted(range(len(values)), key=values.__getitem__)
        out, i = [0.0] * len(values), 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            for k in range(i, j + 1):
                out[order[k]] = (i + j) / 2
            i = j + 1
        return out

    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    sxx = sum((x - mx) ** 2 for x in rx)
    syy = sum((y - my) ** 2 for y in ry)
    if not sxx or not syy:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(rx, ry)) / (sxx * syy) ** 0.5


def length_agreement(rows: list) -> dict:
    """How closely matched cords agree in length; rows are (cm on a, cm on b), 0 or None unrecorded."""
    rows = [(x, y) for x, y in rows if x and y]
    if not rows:
        return {"compared": 0, "median_abs_diff_cm": None, "spearman": None}
    gaps = sorted(abs(x - y) for x, y in rows)
    mid = len(gaps) // 2
    median = gaps[mid] if len(gaps) % 2 else (gaps[mid - 1] + gaps[mid]) / 2
    rho = round(_spearman([x for x, _ in rows], [y for _, y in rows]), 3) if len(rows) >= 5 else None
    return {"compared": len(rows), "median_abs_diff_cm": round(median, 2), "spearman": rho}


def truncated(high, low):
    """How many low-order decimal places high lost to become low (4130 -> 4000 is 3), or None."""
    if high is None or low is None or low <= 0 or low >= high:
        return None
    place, places = 10, 1
    while place <= high:
        if high - high % place == low:
            return places
        place, places = place * 10, places + 1
    return None


def breakage(rows: list, ratio) -> dict:
    """Do disagreements between matched cords look like knots lost from broken cords?

    rows are (value on a, value on b, cm on a, cm on b) for aligned cords; ratio
    is b's typical cord length over a's.  A cord that lost its lower knots
    should also be shorter than its partner predicts.  Under no breakage the
    truncated side is as likely to be the longer cord as the shorter one.
    """
    out = {"differing": 0, "truncated": 0, "truncated_on_a": 0, "truncated_on_b": 0,
           "truncated_with_lengths": 0, "truncated_on_shorter_cord": 0,
           "unreadable": 0, "unreadable_with_lengths": 0, "unreadable_on_shorter_cord": 0}

    def shorter(side, la, lb):
        if not la or not lb or not ratio:
            return None
        return lb < ratio * la if side == "b" else la * ratio < lb

    for va, vb, la, lb in rows:
        if va is None and vb is None:
            continue
        if va is None or vb is None:
            out["unreadable"] += 1
            short = shorter("a" if va is None else "b", la, lb)
            if short is not None:
                out["unreadable_with_lengths"] += 1
                out["unreadable_on_shorter_cord"] += short
            continue
        if va == vb:
            continue
        out["differing"] += 1
        side = "b" if truncated(va, vb) else "a" if truncated(vb, va) else None
        if side is None:
            continue
        out["truncated"] += 1
        out[f"truncated_on_{side}"] += 1
        short = shorter(side, la, lb)
        if short is not None:
            out["truncated_with_lengths"] += 1
            out["truncated_on_shorter_cord"] += short
    t, k = out["truncated_with_lengths"], out["truncated_on_shorter_cord"]
    out["p_shorter"] = round(sum(comb(t, i) for i in range(k, t + 1)) / 2 ** t, 4) if t else None
    return out


def one_object(primary_a, primary_b, agreement: dict) -> bool:
    """Do the lengths look like one khipu measured twice rather than two khipus?"""
    if not primary_a or not primary_b or agreement["compared"] < ONE_OBJECT_MIN_CORDS:
        return False
    if abs(primary_a - primary_b) > ONE_OBJECT_PRIMARY_TOL * max(primary_a, primary_b):
        return False
    return agreement["median_abs_diff_cm"] <= ONE_OBJECT_MAX_DIFF_CM


def fidelity(rows: list, trials: int, seed: str) -> dict:
    """Agreement of a feature across matched cords, against two shuffles.

    rows are (value on a, value on b, the number both cords carry).  The first
    shuffle re-pairs b's cords at random.  The second only re-pairs cords that
    carry the same number, so agreement that merely follows the number cannot
    beat it.

    agree counts equal codes.  consistent counts cords that follow the
    commonest pairing of a's code with b's, so a faithful relabelling (two
    recorders' colour names, or every knot turned the other way) still shows.
    """
    rows = [r for r in rows if r[0] is not None and r[1] is not None]

    def paired(xs, ys):
        seen = defaultdict(Counter)
        for x, y in zip(xs, ys):
            seen[x][y] += 1
        return sum(max(c.values()) for c in seen.values())

    out = {"compared": len(rows), "agree": sum(x == y for x, y, _ in rows),
           "consistent": paired([r[0] for r in rows], [r[1] for r in rows])}
    if not rows:
        return {**out, "null_mean": None, "p_above": None, "p_below": None, "p_consistent": None,
                "movable_within_value": 0, "p_above_within_value": None, "p_below_within_value": None,
                "p_consistent_within_value": None}
    strata = defaultdict(list)
    for i, (_, y, value) in enumerate(rows):
        strata[value].append(i)
    movable = sum(len(ids) for ids in strata.values() if len({rows[i][1] for i in ids}) > 1)
    rng = random.Random(seed)
    xs, ys = [x for x, _, _ in rows], [y for _, y, _ in rows]
    free, inside, free_paired, inside_paired = [], [], [], []
    for _ in range(trials):
        mixed = list(ys)
        rng.shuffle(mixed)
        free.append(sum(x == y for x, y in zip(xs, mixed)))
        free_paired.append(paired(xs, mixed))
        kept = list(ys)
        for ids in strata.values():
            values = [ys[i] for i in ids]
            rng.shuffle(values)
            for i, v in zip(ids, values):
                kept[i] = v
        inside.append(sum(x == y for x, y in zip(xs, kept)))
        inside_paired.append(paired(xs, kept))

    def tail(null, upper, seen="agree"):
        hits = sum((n >= out[seen]) if upper else (n <= out[seen]) for n in null)
        return round((1 + hits) / (trials + 1), 4)

    return {**out, "null_mean": round(sum(free) / trials, 2),
            "p_above": tail(free, True), "p_below": tail(free, False),
            "p_consistent": tail(free_paired, True, "consistent"),
            "movable_within_value": movable,
            "p_above_within_value": tail(inside, True) if movable else 1.0,
            "p_below_within_value": tail(inside, False) if movable else 1.0,
            "p_consistent_within_value": tail(inside_paired, True, "consistent") if movable else 1.0}


def dominant(values: list):
    """The value at least four in five recorded cords share, 'mixed', or None if under five."""
    counts = Counter(v for v in values if v is not None)
    total = sum(counts.values())
    if total < 5:
        return None
    value, n = counts.most_common(1)[0]
    return value if n / total >= 0.8 else "mixed"


def family_direction(knots: list, families: tuple):
    """S or Z if every directed knot of these families on the cord agrees, M if they differ, else None.

    Families follow the OKR engine's knot_family: double long, belted long and
    spiral are long knots, double figure-eight is a figure-eight.
    """
    seen = {d for kind, _, d in knots if _knot_family(kind) in families and d in ("S", "Z")}
    return None if not seen else seen.pop() if len(seen) == 1 else "M"


def _tables(corpus: dict, features: dict, knots: dict, hidden) -> dict:
    """Per khipu: pendant values in order along the cord, and each pendant's features."""
    builder = _module(HERE / "build_features.py", "szl_okr_matching_features")
    out = {}
    for khipu in corpus["khipus"]:
        name = khipu["okr_num"]
        order = hidden.pendant_order(khipu)
        feat, per_cord = features["khipus"][name], builder.cord_knots(knots["khipus"][name])
        cords = [khipu["cords"][i] for i in order]
        main = sum(p["length"] or 0 for p in khipu["primaries"])
        out[name] = {
            "values": [c["value"] if c["value_status"] != "unknown" else None for c in cords],
            "lengths": [c["length"] or None for c in cords],
            "features": {
                "colour": [c["color"] or None for c in cords],
                "attach": [c["attach"] if c["attach"] in ("R", "V") else None for c in cords],
                "spin": [feat["spin"][i] if feat["spin"][i] in "SZ" else None for i in order],
                "fibre": [feat["fibre"][i] if feat["fibre"][i] != "U" else None for i in order],
                "term": [c["term"] or None for c in cords],
                "long_knot_dir": [family_direction(per_cord[i], ("long", "figure-eight")) for i in order],
                "single_knot_dir": [family_direction(per_cord[i], ("single",)) for i in order],
            },
            "meta": {"name": khipu["investigator_num"], "museum": khipu["museum"],
                     "museum_num": knots["khipus"][name]["museum_num"],
                     "provenance": khipu["provenance"], "pendants": len(cords),
                     "other_names": khipu["other_names"], "main_cord_cm": round(main, 1) or None},
        }
    return out


def _oriented(table: dict, orientation: str) -> dict:
    if orientation == "fwd":
        return table
    return {"values": table["values"][::-1], "lengths": table["lengths"][::-1],
            "features": {f: col[::-1] for f, col in table["features"].items()}, "meta": table["meta"]}


def _relation(x, y) -> str:
    if x is None or y is None or "mixed" in (x, y) or "M" in (x, y):
        return "unclear"
    return "same" if x == y else "opposite" if {x, y} in OPPOSITES else "unclear"


def _pair_report(a: str, b: str, orientation: str, tables: dict, info: dict, trials: tuple) -> dict:
    n_order, n_fid = trials
    ta, tb = tables[a], _oriented(tables[b], orientation)
    score, pairs = align(ta["values"], tb["values"], info)
    exact = [(i, j) for i, j in pairs if ta["values"][i] is not None and ta["values"][i] == tb["values"][j]]
    solid = [(i, j) for i, j in exact if ta["values"][i] > 0]
    tag = f"{SEED}|{a}|{b}|{orientation}"
    report = {
        "a": a, "b": b, "a_name": ta["meta"]["name"], "b_name": tb["meta"]["name"],
        "orientation": orientation, "score_bits": round(score, 1),
        "aligned": len(pairs), "exact": len(exact), "exact_nonzero": len(solid),
        "pendants": [ta["meta"]["pendants"], tb["meta"]["pendants"]],
        "museum": [ta["meta"]["museum"], tb["meta"]["museum"]],
        "museum_num": [ta["meta"]["museum_num"], tb["meta"]["museum_num"]],
        "provenance": [ta["meta"]["provenance"], tb["meta"]["provenance"]],
        "other_names": [ta["meta"]["other_names"], tb["meta"]["other_names"]],
    }
    if n_order:
        last = len(tb["values"]) - 1
        own = (lambda j: j) if orientation == "fwd" else (lambda j: last - j)
        report["span"] = [[pairs[0][0], pairs[-1][0]], sorted((own(pairs[0][1]), own(pairs[-1][1])))]
        report.update(order_null(ta["values"], tb["values"], info, n_order, tag + "|order"))
        differ = Counter((ta["values"][i], tb["values"][j]) for i, j in pairs
                         if None not in (ta["values"][i], tb["values"][j]) and ta["values"][i] != tb["values"][j])
        report["aligned_but_different"] = {
            "cords": sum(differ.values()),
            "commonest": [[x, y, n] for (x, y), n in sorted(differ.items(), key=lambda kv: (-kv[1], kv[0]))[:5]]}
        colours = Counter((ta["features"]["colour"][i], tb["features"]["colour"][j]) for i, j in solid
                          if None not in (ta["features"]["colour"][i], tb["features"]["colour"][j]))
        report["colour_pairs"] = [[x, y, n] for (x, y), n in
                                  sorted(colours.items(), key=lambda kv: (-kv[1], kv[0]))[:8]]
        report["main_cord_cm"] = [ta["meta"]["main_cord_cm"], tb["meta"]["main_cord_cm"]]
        report["cord_length"] = length_agreement([(ta["lengths"][i], tb["lengths"][j]) for i, j in solid])
        report["one_object_suspected"] = one_object(*report["main_cord_cm"], report["cord_length"])
        ratios = sorted(tb["lengths"][j] / ta["lengths"][i] for i, j in solid
                        if ta["lengths"][i] and tb["lengths"][j])
        ratio = None
        if ratios:
            mid = len(ratios) // 2
            ratio = ratios[mid] if len(ratios) % 2 else (ratios[mid - 1] + ratios[mid]) / 2
        report["length_ratio_b_to_a"] = round(ratio, 3) if ratio else None
        report["breakage"] = breakage([(ta["values"][i], tb["values"][j], ta["lengths"][i], tb["lengths"][j])
                                       for i, j in pairs], ratio)
        report["fidelity"] = {
            f: fidelity([(ta["features"][f][i], tb["features"][f][j], ta["values"][i]) for i, j in solid],
                        n_fid, f"{tag}|{f}") for f in FEATURES}
        report["khipu_level"] = {}
        for f in KHIPU_LEVEL:
            x, y = dominant(ta["features"][f]), dominant(tb["features"][f])
            report["khipu_level"][f] = {"a": x, "b": y, "relation": _relation(x, y)}
    return report


@functools.lru_cache(maxsize=1)
def _search() -> dict:
    """Everything that does not depend on the shuffles: tables, weights, seeds, best alignments."""
    corpus = _module(ENGINE, "szl_okr_matching_engine").load_corpus()
    if corpus.get("sha256") != CORPUS_SHA256:
        raise Hold("CORPUS_DIGEST_NOT_PINNED")
    builder = _module(HERE / "build_features.py", "szl_okr_matching_builder")
    hidden = _module(HERE / "hidden_cord.py", "szl_okr_matching_hidden")
    tables = _tables(corpus, builder.load_features(), builder.load_knots(), hidden)
    counts = Counter(v for t in tables.values() for v in t["values"] if v is not None)
    total = sum(counts.values())
    info = {v: -log2(n / total) for v, n in counts.items()}
    seqs = {name: t["values"] for name, t in tables.items()}
    seeds = seed_pairs(seqs, info)
    best: dict = {}
    too_large = aligned = 0
    ceilings: dict = {}
    for a, b, orientation in sorted(seeds):
        if (a, b) not in ceilings:
            ceilings[(a, b)] = bound(seqs[a], seqs[b], info)
        if ceilings[(a, b)][0] < MIN_SCORE or ceilings[(a, b)][1] < MIN_EXACT:
            continue
        if len(seqs[a]) * len(seqs[b]) > MAX_CELLS:
            too_large += 1
            continue
        aligned += 1
        row = _pair_report(a, b, orientation, tables, info, (0, 0))
        if row["score_bits"] < MIN_SCORE or row["exact_nonzero"] < MIN_EXACT:
            continue
        kept = best.get((a, b))
        if kept is None or row["score_bits"] > kept["score_bits"]:
            best[(a, b)] = row
    return {"tables": tables, "info": info, "best": best, "corpus_sha256": corpus["sha256"],
            "okr_revision": corpus["source"]["commit"],
            "inputs": (builder.SHIPPED_SHA256, builder.KNOTS_SHA256),
            "search": {"khipus": len(seqs), "seeded": len(seeds), "aligned": aligned,
                       "skipped_as_too_large": too_large, "scored": len(best)}}


def audit(trials: int | None = None, only: tuple | None = None) -> dict:
    found = _search()
    tables, info, best = found["tables"], found["info"], found["best"]
    scored = sorted(best.values(), key=lambda r: (-r["score_bits"], r["a"], r["b"]))
    n_order = N_ORDER if trials is None else trials
    floor = round(1 / (n_order + 1), 4) if n_order else None
    pairs = []
    if n_order:
        for row in scored:
            if only is not None and (row["a"], row["b"]) != tuple(only):
                continue
            full = _pair_report(row["a"], row["b"], row["orientation"], tables, info, (n_order, N_FIDELITY))
            if full["p_order"] == floor:
                pairs.append(full)
    accepted = {frozenset((p["a_name"], p["b_name"])) for p in pairs}
    listed = {frozenset((r["a_name"], r["b_name"])) for r in scored}

    def group(members: list) -> dict:
        def clear(feature, key):
            return sum(p["fidelity"][feature][key] is not None and p["fidelity"][feature][key] <= 0.01
                       for p in members)

        return {"pairs": len(members),
                "features": {f: {"compared": sum(p["fidelity"][f]["compared"] for p in members),
                                 "agree": sum(p["fidelity"][f]["agree"] for p in members),
                                 "consistent": sum(p["fidelity"][f]["consistent"] for p in members),
                                 "pairs_agree_above_shuffle": clear(f, "p_above"),
                                 "pairs_agree_above_within_value": clear(f, "p_above_within_value"),
                                 "pairs_agree_below_shuffle": clear(f, "p_below"),
                                 "pairs_consistent_above_shuffle": clear(f, "p_consistent"),
                                 "pairs_consistent_above_within_value": clear(f, "p_consistent_within_value")}
                             for f in FEATURES},
                "khipu_level": {f: dict(sorted(Counter(p["khipu_level"][f]["relation"]
                                                       for p in members).items())) for f in KHIPU_LEVEL}}

    summary = {"two_objects": group([p for p in pairs if not p["one_object_suspected"]]),
               "one_object_suspected": group([p for p in pairs if p["one_object_suspected"]])}
    for name, members in (("two_objects", [p for p in pairs if not p["one_object_suspected"]]),
                          ("one_object_suspected", [p for p in pairs if p["one_object_suspected"]])):
        keys = ("differing", "truncated", "truncated_with_lengths", "truncated_on_shorter_cord",
                "unreadable", "unreadable_with_lengths", "unreadable_on_shorter_cord")
        totals = {k: sum(p["breakage"][k] for p in members) for k in keys}
        t, k = totals["truncated_with_lengths"], totals["truncated_on_shorter_cord"]
        totals["p_shorter"] = round(sum(comb(t, i) for i in range(k, t + 1)) / 2 ** t, 4) if t else None
        summary[name]["breakage"] = totals
    report = {
        "schema": SCHEMA,
        "status": "POST_HOC_EXPLORATORY_SEARCH",
        "input_corpus_sha256": found["corpus_sha256"],
        "input_features_sha256": found["inputs"][0],
        "input_knots_sha256": found["inputs"][1],
        "upstream_okr_revision": found["okr_revision"],
        "preregistered": False,
        "historical_khipu_decipherment": False,
        "meaning_assigned_to_any_feature": False,
        "pairs_verified_on_the_objects": False,
        "signature_verified": False,
        "parameters": {"mismatch": MISMATCH, "gap": GAP, "trigram_bits": TRIGRAM_BITS,
                       "rare_bits": RARE_BITS, "min_score_bits": MIN_SCORE, "min_exact_nonzero": MIN_EXACT,
                       "max_cells": MAX_CELLS, "order_shuffles": N_ORDER, "fidelity_shuffles": N_FIDELITY,
                       "one_object_main_cord_tolerance": ONE_OBJECT_PRIMARY_TOL,
                       "one_object_max_median_diff_cm": ONE_OBJECT_MAX_DIFF_CM,
                       "one_object_min_cords": ONE_OBJECT_MIN_CORDS,
                       "seed": SEED, "unit": "level-1 pendants in ordinal order"},
        "search": found["search"],
        "scored": [{k: r[k] for k in ("a", "b", "a_name", "b_name", "orientation", "score_bits",
                                      "aligned", "exact", "exact_nonzero")} for r in scored],
        "pairs": pairs,
        "known_pairs": [{"id": f"{x}~{y}",
                         "status": "REPLICATED" if frozenset((x, y)) in accepted
                         else "PARTIAL" if frozenset((x, y)) in listed else "NOT_FOUND"} for x, y in KNOWN],
        "fidelity_summary": summary,
        "prior_art": [dict(entry) for entry in PRIOR_ART],
        "reading_the_numbers": [
            ("score_bits adds the rarity of every value the two khipus share in the same order; "
             "p_order is the share of shuffles of one khipu's cord order that score as high, and "
             "null_max_bits is the best any shuffle did."),
            ("span gives the first and last matched pendant on each khipu, counted from 0 in its "
             "own cord order."),
            ("one_object_suspected is true when the main cords are within 5% in length and matched "
             "cords differ by 3 cm or less at the median: one khipu entered twice, not two khipus."),
            ("fidelity compares a feature across cords that carry the same nonzero number. agree "
             "counts equal codes; consistent counts cords that follow the commonest pairing of one "
             "khipu's code with the other's. p_above, p_below and p_consistent use a free shuffle; "
             "the within_value columns re-pair only cords with equal numbers, and "
             "movable_within_value says how many cords that can move."),
            ("khipu_level gives each khipu's prevailing value (four in five cords) and whether "
             "the two are the same or opposite."),
            ("breakage looks at aligned cords whose numbers differ: a truncation is one number with "
             "its lower knots gone (4130 against 4000). If cords broke, the truncated cord should be "
             "shorter than its partner predicts; p_shorter is the chance of that many or more under a "
             "fair coin. unreadable counts aligned cords with no readable number on one side."),
            ("prior_art records what the OKR notes and the Khipu Field Guide already say about these "
             "pairs. The Field Guide entries were seen through search-engine summaries; those pages "
             "were not opened from this environment."),
            ("A kept pair is a candidate until the objects are checked. The records cannot "
             "exclude one record typed from another."),
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
    print(json.dumps(report["search"]), json.dumps(report["known_pairs"]))
    for p in report["pairs"]:
        print(f"{p['score_bits']:7.1f} (shuffle max {p['null_max_bits']:6.1f}) {p['a_name']:<12} "
              f"{p['b_name']:<12} {p['orientation']} exact {p['exact_nonzero']:>3} "
              f"{'ONE OBJECT?' if p['one_object_suspected'] else '':<11} | "
              f"{p['museum_num'][0]} / {p['museum_num'][1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
