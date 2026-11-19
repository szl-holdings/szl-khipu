#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Independent stress test of a published khipu syllabary proposal.

Sivan (2026, ALBA Project) proposes that cords carrying two or more long or
figure-eight knots spell Quechua words, one syllable per knot, and publishes
the mapping, the scoring rule and the dictionaries under open licences.  This
module re-implements that scoring from the description in the project's own
control scripts, applies it to the pinned OKR corpus, and adds three controls:

  1. how many of all possible readings the scoring rule accepts;
  2. whether the proposed mapping reads scrambled cords as well as real ones;
  3. how well a mapping fitted the same way does on scrambled cords.

The proposal, its mapping and its scoring rule are Sivan's.  None of that
project's code is run or copied here, and its dictionaries are read from a
digest-checked local copy, never redistributed.  The outcome is a measurement
of the published evidence.  It neither reads a khipu nor proposes a reading.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import random
from collections import Counter
from itertools import product
from math import fsum
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "szl_khipu/okr_khipu.py"
SEALED = Path(__file__).with_name("syllabary_stress_v1.json")
SCHEMA = "szl.okr.syllabary-stress/v1"
CORPUS_SHA256 = "6ef204b641826b37c320509952ed4181e93865af20f1cdfefd7516a49cf8ad0d"

PROPOSAL = {
    "cite": "Sivan, J. (2026). Evidence for a Syllabic Mapping in Andean Khipu Long-Knot Turn "
            "Counts. ALBA Project preprint.",
    "doi": "10.5281/zenodo.19184002",
    "page": "https://alba-project.org/khipu-reader/",
    "repository": "https://github.com/Alba-Research/KhipuReader",
    "repository_commit": "7c2722b91fcad514653c96f40fa2dae125de92b8",
    "licence": "MIT",
    "read_by_this_project": "project page, README, syllabary.py, corpus_coverage.py, "
                            "negative_controls.py and the head of replication_ur112.py at that "
                            "commit; the preprint itself was not read",
}
# Paths are relative to the proposal's repository at the commit above.
DICTIONARIES = {
    "kaikki_2074": {
        "file": "quechua_kaikki_2074.txt",
        "path_in_repository": "reproducibility/data/quechua_kaikki_2074.txt",
        "sha256": "38e957982087e139ce30a99e24fd41dc97e6b20a7ff8ec6fef158863912cf622"},
    "kaikki_aulex_14991": {
        "file": "quechua_strict_clean.txt",
        "path_in_repository": "src/khipu_translator/data/quechua_strict_clean.txt",
        "sha256": "ad163c3abbb01c46ee3c3107ad85970cda6738d92131ae854b47e7b68a1f67f1"},
}
# The mapping as the proposal's control scripts score it (onset forms throughout),
# and the coda forms its translator uses after the first knot.
V3_ONSET = {0: "lla", 2: "chi", 3: "ma", 4: "ka", 5: "ta", 6: "pa", 7: "wa", 8: "cha",
            9: "pi", 10: "si", 11: "ti", 12: "ku", "E": "qa"}
V3_CODA = {**V3_ONSET, 2: "ki", 7: "y", 8: "na"}
SUFFIXES = ("ta", "pa", "ka", "ma", "na", "qa", "ki", "si", "y")
MIN_LEN = 4
# Khipus the proposal names as used for fitting or tuning the mapping.
FIT_KHIPUS = ("UR039", "UR050", "UR055")
INVENTORY = tuple(c + v for c in ("ch", "h", "k", "l", "ll", "m", "n", "p", "q", "r", "s", "t", "w", "y")
                  for v in "aiu")
PUBLISHED = {"string_cords": 1992, "knotted_cords": 37206,
             "random_mapping_p": 0.001, "random_mappings": 10000}
N_RANDOM = 2000
N_SHUFFLE = 200
N_REFIT = 20
SEED = 2026


class Hold(ValueError):
    """Refuse inputs this test was not written for."""


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")


def digest(report: dict) -> str:
    body = {k: v for k, v in report.items() if k != "report_sha256"}
    return hashlib.sha256(canonical(body)).hexdigest()


def load_corpus() -> dict:
    spec = importlib.util.spec_from_file_location("szl_okr_syllabary_stress_engine", ENGINE)
    if spec is None or spec.loader is None:
        raise Hold("ENGINE_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    corpus = module.load_corpus()
    if corpus.get("sha256") != CORPUS_SHA256:
        raise Hold("CORPUS_DIGEST_NOT_PINNED")
    return corpus


def classify(knots: list) -> tuple:
    """(is a 'STRING' cord, its symbol sequence or None), by the proposal's rule.

    A cord is a STRING cord when it has two or more knots of type L or E.  Its
    symbols are the long knots' turn counts and "E" for a figure-eight; a long
    knot with no recorded turn count is dropped, and fewer than two remaining
    symbols give no sequence.
    """
    terminal = [k for k in knots if k["type"] in ("L", "E")]
    if len(terminal) < 2:
        return False, None
    symbols = tuple("E" if k["type"] == "E" else int(k["turns"])
                    for k in terminal if k["type"] == "E" or k["turns"] is not None)
    return True, symbols if len(symbols) >= 2 else None


def sequences_by_khipu(corpus: dict) -> dict:
    out: dict = {}
    for khipu in corpus["khipus"]:
        seqs = [s for s in (classify(c["knots"])[1] for c in khipu["cords"]) if s]
        if seqs:
            out[khipu["investigator_num"]] = seqs
    return out


def census(corpus: dict) -> dict:
    knotted = strings = 0
    symbols: Counter = Counter()
    for khipu in corpus["khipus"]:
        for cord in khipu["cords"]:
            if cord["knots"]:
                knotted += 1
                strings += classify(cord["knots"])[0]
    by_khipu = sequences_by_khipu(corpus)
    all_seqs = [s for seqs in by_khipu.values() for s in seqs]
    for s in all_seqs:
        symbols.update(str(x) for x in s)
    return {
        "knotted_cords": knotted, "string_cords": strings,
        "string_share": round(strings / knotted, 4),
        "sequences": len(all_seqs), "distinct_sequences": len(set(all_seqs)),
        "khipus_with_sequences": len(by_khipu),
        "sequences_readable_by_v3": sum(all(x in V3_ONSET for x in s) for s in all_seqs),
        "symbol_counts": dict(sorted(symbols.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


def load_words(path: Path, sha256: str) -> set:
    blob = Path(path).read_bytes()
    if hashlib.sha256(blob).hexdigest() != sha256:
        raise Hold("DICTIONARY_DIGEST_MISMATCH")
    return build_exact(blob.decode("utf-8").splitlines())


def build_exact(words) -> set:
    return {w.strip().lower() for w in words if w.strip()}


def build_lookup(words) -> set:
    """The proposal's control-script rule: suffixed forms and prefixes of 4+ letters also count."""
    forms = set()
    for w in build_exact(words):
        forms.add(w)
        forms.update(w + s for s in SUFFIXES if len(w + s) >= MIN_LEN)
    prefixes = {w[:i] for w in forms for i in range(MIN_LEN, len(w))}
    return forms | prefixes


def read(seq: tuple, onset: dict, coda: dict | None = None):
    later = onset if coda is None else coda
    parts = []
    for i, symbol in enumerate(seq):
        syllable = (onset if i == 0 else later).get(symbol)
        if syllable is None:
            return None
        parts.append(syllable)
    return "".join(parts)


def _hit(word, lookup: set) -> bool:
    return word is not None and len(word) >= MIN_LEN and word in lookup


def score(mapping: dict, seq_counts, lookup: set, coda: dict | None = None) -> int:
    return sum(n for seq, n in seq_counts.items() if _hit(read(seq, mapping, coda), lookup))


def density(syllables, lookup: set, n: int) -> float:
    """Share of all n-syllable strings over `syllables` that the rule accepts."""
    words = ["".join(p) for p in product(syllables, repeat=n)]
    return round(sum(_hit(w, lookup) for w in words) / len(words), 4)


def shuffle_order(by_khipu: dict, rng) -> dict:
    out = {}
    for name in sorted(by_khipu):
        out[name] = []
        for seq in by_khipu[name]:
            symbols = list(seq)
            rng.shuffle(symbols)
            out[name].append(tuple(symbols))
    return out


def shuffle_khipu(by_khipu: dict, rng) -> dict:
    out = {}
    for name in sorted(by_khipu):
        pool = [x for seq in by_khipu[name] for x in seq]
        rng.shuffle(pool)
        seqs, at = [], 0
        for seq in by_khipu[name]:
            seqs.append(tuple(pool[at:at + len(seq)]))
            at += len(seq)
        out[name] = seqs
    return out


def counts(by_khipu: dict, exclude: tuple = ()) -> Counter:
    return Counter(s for name, seqs in by_khipu.items() if name not in exclude for s in seqs)


def _key(symbol) -> tuple:
    return (isinstance(symbol, str), symbol)


def fit(seq_counts, inventory, lookup: set, seed: int, start: dict | None = None) -> tuple:
    """Greedy search for a one-to-one symbol-to-syllable mapping with the most hits.

    Moves: give a symbol an unused syllable, or swap two symbols' syllables.
    Sweeps repeat until no move improves the score.  The same search is used on
    real and scrambled cords, so its imperfections affect both alike.
    """
    rng = random.Random(seed)
    symbols = sorted({x for seq in seq_counts for x in seq}, key=_key)
    if len(symbols) > len(inventory):
        raise Hold("MORE_SYMBOLS_THAN_SYLLABLES")
    mapping = dict(start) if start is not None else dict(zip(symbols, rng.sample(inventory, len(symbols))))
    for symbol in symbols:
        if symbol not in mapping:
            mapping[symbol] = rng.choice([s for s in inventory if s not in mapping.values()])
    best = score(mapping, seq_counts, lookup)
    improved = True
    while improved:
        improved = False
        for i, a in enumerate(symbols):
            used = set(mapping.values())
            for syllable in inventory:
                if syllable in used:
                    continue
                trial = {**mapping, a: syllable}
                hits = score(trial, seq_counts, lookup)
                if hits > best:
                    mapping, best, improved = trial, hits, True
                    used = set(mapping.values())
            for b in symbols[i + 1:]:
                trial = {**mapping, a: mapping[b], b: mapping[a]}
                hits = score(trial, seq_counts, lookup)
                if hits > best:
                    mapping, best, improved = trial, hits, True
    return mapping, best


def _best_fit(seq_counts, lookup: set, seed: int) -> int:
    known = Counter({s: n for s, n in seq_counts.items() if all(x in V3_ONSET for x in s)})
    from_proposal = fit(known, INVENTORY, lookup, seed, start=V3_ONSET)[1]
    return max(from_proposal, fit(known, INVENTORY, lookup, seed)[1])


def _tail(observed: int, null: list) -> dict:
    return {"null_mean": round(fsum(null) / len(null), 2), "null_min": min(null), "null_max": max(null),
            "p_upper": round((1 + sum(x >= observed for x in null)) / (len(null) + 1), 4)}


def _rule_report(real: dict, lookup: set, shuffles: dict) -> dict:
    everything, held_out = counts(real), counts(real, FIT_KHIPUS)
    n_all, n_held = sum(everything.values()), sum(held_out.values())
    observed = score(V3_ONSET, everything, lookup)
    rng = random.Random(f"{SEED}|random-mappings")
    symbols = sorted(V3_ONSET, key=_key)
    random_hits = [score(dict(zip(symbols, rng.sample(INVENTORY, len(symbols)))), everything, lookup)
                   for _ in range(N_RANDOM)]
    real_fit = _best_fit(everything, lookup, SEED)
    shuffled_fits = [_best_fit(c, lookup, SEED) for c in shuffles["refit"]]
    return {
        "density": {"two_syllables": density(tuple(V3_ONSET.values()), lookup, 2),
                    "three_syllables": density(tuple(V3_ONSET.values()), lookup, 3)},
        "observed": {
            "sequences": n_all, "hits": observed, "rate": round(observed / n_all, 4),
            "hits_onset_then_coda": score(V3_ONSET, everything, lookup, V3_CODA),
            "outside_fit_khipus": {
                "sequences": n_held, "hits": score(V3_ONSET, held_out, lookup),
                "rate": round(score(V3_ONSET, held_out, lookup) / n_held, 4)},
        },
        "random_mappings": {"trials": N_RANDOM, **_tail(observed, random_hits),
                            "null_mean_rate": round(fsum(random_hits) / len(random_hits) / n_all, 4)},
        "order_shuffle": {"trials": N_SHUFFLE,
                          **_tail(observed, [score(V3_ONSET, c, lookup) for c in shuffles["order"]])},
        "khipu_shuffle": {"trials": N_SHUFFLE,
                          **_tail(observed, [score(V3_ONSET, c, lookup) for c in shuffles["khipu"]])},
        "refit": {"trials": N_REFIT, "best_hits_on_real_cords": real_fit,
                  "proposal_hits_on_real_cords": observed,
                  **_tail(real_fit, shuffled_fits),
                  "scrambled_refits_at_or_above_the_proposal": sum(x >= observed for x in shuffled_fits)},
    }


def _random_mapping_claim(dictionaries: dict) -> dict:
    rule = dictionaries["kaikki_2074"]["rules"]["published_lookup"]
    random_test, observed = rule["random_mappings"], rule["observed"]
    beaten = random_test["null_max"] < observed["hits"]
    return {
        "id": "mapping_beats_random_mappings", "status": "REPLICATED" if beaten else "CONTRADICTED",
        "published": {"p": PUBLISHED["random_mapping_p"], "random_mappings": PUBLISHED["random_mappings"]},
        "measured": {"hits": observed["hits"], "sequences": observed["sequences"],
                     "best_random_mapping_hits": random_test["null_max"],
                     "random_mappings": random_test["trials"], "p_upper": random_test["p_upper"]},
        "note": "The proposed syllables do beat syllables drawn at random. That shows the chosen "
                "syllables form dictionary strings more often than arbitrary ones. It does not "
                "show the cords spell words: the same mapping scores scrambled cords as highly "
                "as real ones (see order_shuffle, khipu_shuffle and refit).",
    }


def audit(dict_dir: Path) -> dict:
    corpus = load_corpus()
    real = sequences_by_khipu(corpus)
    shuffles = {
        "order": [counts(shuffle_order(real, random.Random(f"{SEED}|order|{i}"))) for i in range(N_SHUFFLE)],
        "khipu": [counts(shuffle_khipu(real, random.Random(f"{SEED}|khipu|{i}"))) for i in range(N_SHUFFLE)],
        "refit": [counts(shuffle_khipu(real, random.Random(f"{SEED}|refit|{i}"))) for i in range(N_REFIT)],
    }
    numbers = census(corpus)
    dictionaries = {}
    for name, meta in DICTIONARIES.items():
        words = load_words(Path(dict_dir) / meta["file"], meta["sha256"])
        dictionaries[name] = {
            "sha256": meta["sha256"], "path_in_repository": meta["path_in_repository"],
            "entries": len(words),
            "rules": {"published_lookup": _rule_report(real, build_lookup(words), shuffles),
                      "exact": _rule_report(real, words, shuffles)},
        }
    report = {
        "schema": SCHEMA,
        "status": "POST_HOC_INDEPENDENT_STRESS_TEST_OF_A_PUBLISHED_PROPOSAL",
        "input_corpus_sha256": corpus["sha256"],
        "upstream_okr_revision": corpus["source"]["commit"],
        "preregistered": False,
        "historical_khipu_decipherment": False,
        "new_reading_claimed": False,
        "third_party_code_executed": False,
        "peer_reviewed_source": False,
        "signature_verified": False,
        "proposal": PROPOSAL,
        "published": PUBLISHED,
        "parameters": {"seed": SEED, "random_mappings": N_RANDOM, "shuffles": N_SHUFFLE,
                       "refits": N_REFIT, "min_reading_length": MIN_LEN, "suffixes": list(SUFFIXES),
                       "syllable_inventory": list(INVENTORY), "fit_khipus": list(FIT_KHIPUS),
                       "mapping_scored": {str(k): v for k, v in V3_ONSET.items()}},
        "census": numbers,
        "claims": [{
            "id": "string_cords_1992_of_37206", "status": "PARTIAL",
            "published": {"string_cords": PUBLISHED["string_cords"], "knotted_cords": PUBLISHED["knotted_cords"]},
            "measured": {"string_cords": numbers["string_cords"], "knotted_cords": numbers["knotted_cords"]},
            "note": "Same order of size, different counts. The proposal's tool builds its own "
                    "table from OKR and patches some turn counts from a second database; this "
                    "run uses the pinned corpus only and did not execute that tool.",
        }, _random_mapping_claim(dictionaries)],
        "dictionaries": dictionaries,
        "dictionary_note": "Per the proposal's reproducibility/build_kaikki_dictionary.py, the "
                           "2,074-entry list is a Wiktionary-derived list of 2,060 entries plus "
                           "forms 'observed in the OKR STRING cord corpus' under the mapping "
                           "(14 net new). Those additions favour the mapping in every row here.",
        "not_tested": ["thematic coherence of readings by document type",
                       "astronomical dating of UR006", "the proposed calendar in opening cords",
                       "generalisation to the Khipu Field Guide database",
                       "the UR112 ranking against 154,440 alternative mappings"],
        "reading_the_numbers": [
            ("density is the share of every possible two- or three-knot reading that the scoring "
             "rule accepts as a word; it is the hit rate a mapping gets for free."),
            ("order_shuffle scrambles the knots within each cord; khipu_shuffle deals each khipu's "
             "knots back out to its cords at random. The mapping is held fixed."),
            ("refit searches for the best one-to-one mapping on the real cords and again on "
             "scrambled cords, so a fitted score is compared with fitted scores."),
            ("p_upper cannot go below 1/(trials+1). A hit means a string is in a word list. It "
             "does not mean the cord says that word."),
        ],
    }
    report["report_sha256"] = digest(report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dict-dir", type=Path, default=os.environ.get("SZL_ALBA_DICT_DIR"),
                        help="directory holding the two digest-checked dictionary files")
    parser.add_argument("--write", action="store_true", help="write the sealed report")
    parser.add_argument("--check", action="store_true", help="compare with the sealed report")
    args = parser.parse_args(argv)
    if args.dict_dir is None:
        parser.error("--dict-dir or SZL_ALBA_DICT_DIR is required")
    report = audit(args.dict_dir)
    text = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    if args.write:
        SEALED.write_text(text, encoding="utf-8")
    if args.check:
        same = json.loads(SEALED.read_text(encoding="utf-8")) == json.loads(text)
        print("REPLAY_MATCH" if same else "HOLD: sealed report differs from recomputation")
        return 0 if same else 1
    for name, block in report["dictionaries"].items():
        for rule, r in block["rules"].items():
            o = r["observed"]
            print(f"{name:<19} {rule:<16} density2 {r['density']['two_syllables']:.3f} "
                  f"hits {o['hits']}/{o['sequences']} random-mean {r['random_mappings']['null_mean']:.0f} "
                  f"p {r['random_mappings']['p_upper']} order {r['order_shuffle']['null_mean']:.0f} "
                  f"khipu {r['khipu_shuffle']['null_mean']:.0f} refit real {r['refit']['best_hits_on_real_cords']} "
                  f"scrambled {r['refit']['null_mean']:.0f}-{r['refit']['null_max']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
