#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Replication of published claims about the six Santa Valley khipus.

The claims are other people's: Urton (2017), Medrano and Urton (2018) and
FitzPatrick (2024) link khipus UR087-UR092 to a 1670 Spanish census of San
Pedro de Corongo.  This module re-derives the countable parts of those claims
from the pinned Open Khipu Repository corpus and says, claim by claim, whether
the pinned records reproduce them.

It reads nothing.  It proposes no new meaning for any cord.  The grouping rules
below were written after looking at these six khipus and at the published
counts, so every result here is post hoc.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
from itertools import combinations, groupby
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "szl_khipu/okr_khipu.py"
SEALED = Path(__file__).with_name("santa_valley_v1.json")
SCHEMA = "szl.okr.santa-valley-replication/v1"
CORPUS_SHA256 = "6ef204b641826b37c320509952ed4181e93865af20f1cdfefd7516a49cf8ad0d"
STATUSES = ("REPLICATED", "PARTIAL", "CONTRADICTED", "NOT_TESTABLE", "NOT_TESTED")
GROUP_SIZE = 6
CHANCE_SEED = 1670
CHANCE_TRIALS = 20000

SOURCES = [
    {"key": "urton2017", "cite": "Urton, G. (2017). Inka History in Knots. University of Texas Press.",
     "read_by_this_project": False},
    {"key": "medrano_urton2018",
     "cite": "Medrano, M. and Urton, G. (2018). Toward the Decipherment of a Set of Mid-Colonial "
             "Khipus from the Santa Valley, Coastal Peru. Ethnohistory 65(1): 1-23.",
     "doi": "10.1215/00141801-4260638", "read_by_this_project": False},
    {"key": "fitzpatrick2024",
     "cite": "FitzPatrick, M. (2024). New Insights on Cord Attachment and Social Hierarchy in Six "
             "Khipus from the Santa Valley, Peru. Ethnohistory 71(4): 443-469.",
     "doi": "10.1215/00141801-11266328", "open_preprint": "https://osf.io/sr8kw",
     "read_by_this_project": "first half and footnotes 9-12 of the open preprint "
                             "(pdf sha256 a776a8b56f66cab16b2e6bdd7972a62521f29fbb30e7931044015db69685ec4e); "
                             "section 4 and footnotes 3, 5, 7, 8 were not read"},
]

# Everything in PUBLISHED is quoted or tabulated from the FitzPatrick preprint,
# which reports Medrano and Urton's counts alongside its own.
SANTA = (("KH0323", "UR087"), ("KH0324", "UR088"), ("KH0325", "UR089"),
         ("KH0326", "UR090"), ("KH0327", "UR091"), ("KH0328", "UR092"))
PUBLISHED = {
    "pendant_cords": 804,
    "six_cord_groups": 133,
    "groups_per_khipu": [48, 9, 34, 17, 15, 10],
    "identifier_recto": 63,
    "identifier_verso": 70,
    "kh0326_identifier_sequence": "VVVVVVVVVVRRRVVRR",
    "kh0326_leading_verso_cords": 59,
    "tributaries": 132,
    "tributaries_named": 130,
    "tribute_each": {"pesos": 2, "reales": 7, "quartillos": 3},
    "tribute_total_pesos": 367,
}
PACHACAS = (("Namus", 18), ("Corongo", 23), ("Cuyuchin", 9),
            ("Cusca", 7), ("Guauyan", 41), ("Ucore", 32))
ALIGNMENTS = {"medrano_urton2018": ("Corongo", "Cusca", "Guauyan"),
              "fitzpatrick2024": ("Cuyuchin", "Guauyan", "Namus")}
# FitzPatrick's Table 3: verso total, recto total, error, p.
PUBLISHED_TABLE_3 = (
    (68, 62, 3, 0.02985), (66, 64, 5, 0.04478), (71, 59, 5, 0.04478), (73, 57, 9, 0.07463),
    (64, 66, 9, 0.07463), (73, 57, 9, 0.07463), (62, 68, 13, 0.10448), (59, 71, 19, 0.14925),
    (57, 73, 23, 0.1791), (57, 73, 23, 0.1791), (80, 50, 23, 0.1791), (82, 48, 27, 0.20896),
    (82, 48, 27, 0.20896), (50, 80, 37, 0.28358), (48, 82, 41, 0.31343), (48, 82, 41, 0.31343),
    (91, 39, 45, 0.34328), (96, 34, 55, 0.41791), (39, 91, 59, 0.44776), (34, 96, 69, 0.52239),
)


class Hold(ValueError):
    """Refuse a corpus or input this replication was not written for."""


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")


def digest(report: dict) -> str:
    body = {k: v for k, v in report.items() if k != "report_sha256"}
    return hashlib.sha256(canonical(body)).hexdigest()


def _engine():
    spec = importlib.util.spec_from_file_location("szl_okr_santa_valley_engine", ENGINE)
    if spec is None or spec.loader is None:
        raise Hold("ENGINE_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pendants(khipu: dict) -> list:
    return [c for c in khipu["cords"] if c["level"] == 1 and c["parent_kind"] == "primary"]


def _clusters(cords: list):
    for _, members in groupby(cords, key=lambda c: c["cluster"]):
        yield list(members)


def band_groups(cords: list) -> dict:
    """Six-cord groups read from colour bands inside each cord cluster.

    A same-colour run of six or more yields leading groups of six and sets the
    remainder aside (the published treatment of the ten brown cords on UR090).
    Shorter runs accumulate into one mixed group of six.  Shorter runs that are
    still waiting when a full band arrives, or when the cluster ends, are set
    aside.  A one-cord cluster is a single and never a group member.  The rule
    uses colour and clustering only, so it cannot be steered by knot values or
    attachment direction.
    """
    groups, extras, singles, ambiguous = [], [], [], 0
    for members in _clusters(cords):
        if len(members) == 1:
            singles.extend(members)
            continue
        waiting: list = []
        for _, run_iter in groupby(members, key=lambda c: c["color"]):
            run = list(run_iter)
            if len(run) >= GROUP_SIZE:
                extras.extend(waiting)
                waiting = []
                full = len(run) // GROUP_SIZE
                groups.extend(run[GROUP_SIZE * i:GROUP_SIZE * (i + 1)] for i in range(full))
                extras.extend(run[GROUP_SIZE * full:])
                continue
            waiting.extend(run)
            if len(waiting) > GROUP_SIZE:
                ambiguous += 1
            while len(waiting) >= GROUP_SIZE:
                groups.append(waiting[:GROUP_SIZE])
                waiting = waiting[GROUP_SIZE:]
        extras.extend(waiting)
    return {"groups": groups, "extras": extras, "singles": singles, "ambiguous": ambiguous}


def positional_groups(cords: list) -> dict:
    """Comparison rule: count off sixes from the start of each cluster, colour ignored."""
    groups, extras, singles = [], [], []
    for members in _clusters(cords):
        if len(members) == 1:
            singles.extend(members)
            continue
        full = len(members) // GROUP_SIZE
        groups.extend(members[GROUP_SIZE * i:GROUP_SIZE * (i + 1)] for i in range(full))
        extras.extend(members[GROUP_SIZE * full:])
    return {"groups": groups, "extras": extras, "singles": singles, "ambiguous": 0}


def quartillos(pesos: int, reales: int, quarts: int) -> int:
    """Assumes the usual colonial units: 1 peso = 8 reales, 1 real = 4 quartillos."""
    return 32 * pesos + 4 * reales + quarts


def as_pesos_reales_quartillos(q: int) -> tuple:
    return q // 32, (q % 32) // 4, q % 4


def _error(verso_names: int, recto_names: int, verso: int, recto: int) -> int:
    return abs(verso_names - verso) + abs(recto_names - recto)


def split_table(pachacas, verso: int, recto: int) -> list:
    """All twenty ways to give three of the six pachacas to the verso side."""
    size = dict(pachacas)
    total = sum(size.values())
    rows = []
    for names in combinations([n for n, _ in pachacas], 3):
        v = sum(size[n] for n in names)
        err = _error(v, total - v, verso, recto)
        rows.append({
            "verso": list(names),
            "recto": [n for n, _ in pachacas if n not in names],
            "verso_total": v, "recto_total": total - v, "error": err,
            # (error + 1) / (groups + 1) equals the published p in all twenty rows;
            # the derivation in the source's footnotes was not available to this run.
            "p_published_form": round((err + 1) / (verso + recto + 1), 5),
        })
    rows.sort(key=lambda r: (r["error"], r["verso"]))
    return rows


def _floor_error(total: int, verso: int, recto: int) -> int:
    return min(_error(v, total - v, verso, recto) for v in range(total + 1))


def chance_check(verso: int, recto: int, total: int, parts: int = 6) -> dict:
    """How often would six arbitrary pachaca sizes allow a best-possible split?

    Draws compositions of `total` named tributaries into `parts` positive sizes
    uniformly at random and asks whether any three of them reach the smallest
    error the group counts allow.  One illustrative null among many possible.
    """
    floor = _floor_error(total, verso, recto)
    rng = random.Random(CHANCE_SEED)
    hits = 0
    for _ in range(CHANCE_TRIALS):
        cuts = sorted(rng.sample(range(1, total), parts - 1))
        sizes = [b - a for a, b in zip([0] + cuts, cuts + [total])]
        if any(_error(sum(c), total - sum(c), verso, recto) == floor
               for c in combinations(sizes, 3)):
            hits += 1
    return {"label": "OURS_EXPLORATORY_NOT_IN_SOURCE", "seed": CHANCE_SEED,
            "trials": CHANCE_TRIALS, "floor_error": floor,
            "null": "uniform random compositions of the named tributaries into six positive sizes",
            "fraction_with_a_floor_split": round(hits / CHANCE_TRIALS, 4)}


def _rule_report(per_khipu_groupings: list) -> dict:
    per_khipu, attach, sums = [], {"R": 0, "U": 0, "V": 0}, []
    knotted = knotless = unreadable = total = ambiguous = n_groups = 0
    side = {"R": 0, "U": 0, "V": 0}
    for okr_num, grouping in per_khipu_groupings:
        first = [g[0] for g in grouping["groups"]]
        sequence = "".join(c["attach"] if c["attach"] in ("R", "V") else "U" for c in first)
        khipu_sum = 0
        for cord, letter in zip(first, sequence):
            attach[letter] += 1
            if cord["value_status"] == "known":
                knotted += 1
                khipu_sum += cord["value"]
                side[letter] += cord["value"]
            elif cord["value_status"] == "knotless":
                knotless += 1
            else:
                unreadable += 1
        row = {"okr_num": okr_num, "groups": len(first), "set_aside": len(grouping["extras"]),
               "identifier_sequence": sequence,
               "identifier_values": [c["value"] if c["value_status"] != "unknown" else None
                                     for c in first]}
        if okr_num == "KH0326":
            want = PUBLISHED["kh0326_identifier_sequence"]
            row["published_identifier_sequence"] = want
            row["identifier_sequence_mismatch_groups"] = [
                i + 1 for i, (a, b) in enumerate(zip(sequence, want)) if a != b
            ] if len(sequence) == len(want) else None
        per_khipu.append(row)
        sums.append(khipu_sum)
        total += khipu_sum
        ambiguous += grouping["ambiguous"]
        n_groups += len(first)
    return {
        "groups": n_groups, "ambiguous": ambiguous, "per_khipu": per_khipu,
        "identifier_attachment": attach,
        "first_cord": {"knotted": knotted, "knotless": knotless, "unreadable": unreadable,
                       "knotted_sum": total, "per_khipu_sum": sums, "by_side_sum": side,
                       "fraction_of_document_total": round(total / PUBLISHED["tribute_total_pesos"], 4)},
    }


def _alignment(verso: int, recto: int) -> dict:
    rows = split_table(PACHACAS, verso, recto)
    by_names = {tuple(sorted(r["verso"])): r for r in rows}
    best = [r for r in rows if r["error"] == rows[0]["error"]]
    return {
        "verso_groups": verso, "recto_groups": recto,
        "floor_error": _floor_error(sum(n for _, n in PACHACAS), verso, recto),
        "best_error": rows[0]["error"], "splits_at_best_error": len(best),
        "best_verso": sorted(best[0]["verso"]),
        "named": {key: {"verso": list(names), "error": by_names[names]["error"],
                        "rank_of_20": 1 + sum(r["error"] < by_names[names]["error"] for r in rows)}
                  for key, names in ALIGNMENTS.items()},
    }


def _claims(band: dict, totals: dict, khipus: list, leading: int, table_ok: bool) -> list:
    first = band["first_cord"]
    att = band["identifier_attachment"]
    return [
        {"id": "khipus_in_corpus", "status": "REPLICATED" if len(khipus) == 6 else "CONTRADICTED",
         "published": "six khipus UR087-UR092, Biblioteca Museo Temple Radicati, Lima",
         "measured": [f"{k['okr_num']}={k['investigator_num']} ({k['museum']})" for k in khipus]},
        {"id": "pendant_cords_804",
         "status": "REPLICATED" if totals["pendants_in_multi_cord_clusters"] == PUBLISHED["pendant_cords"]
         else "CONTRADICTED",
         "published": PUBLISHED["pendant_cords"], "measured": totals,
         "note": "804 is reached by leaving out the 20 pendants that are the only cord in their "
                 "cluster; the source's own exclusion rule was not located."},
        {"id": "six_cord_groups_133",
         "status": "REPLICATED" if [k["groups"] for k in band["per_khipu"]] == PUBLISHED["groups_per_khipu"]
         else "CONTRADICTED",
         "published": PUBLISHED["groups_per_khipu"],
         "measured": [k["groups"] for k in band["per_khipu"]],
         "note": "colour-band rule, written after seeing the data and the published counts."},
        {"id": "identifier_recto_63_verso_70",
         "status": "REPLICATED" if (att["R"], att["V"], att["U"]) == (63, 70, 0) else "PARTIAL",
         "published": {"R": PUBLISHED["identifier_recto"], "V": PUBLISHED["identifier_verso"]},
         "measured": att,
         "note": "The pinned records differ from the published counts in two groups: the fifteenth "
                 "group of KH0326 opens with a recto cord (published: verso), and the second group "
                 "of KH0328 opens with a cord whose attachment is recorded as unspecified. The "
                 "published KH0326 sequence is this project's transcription from the preprint."},
        {"id": "kh0326_59_leading_verso",
         "status": "REPLICATED" if leading == PUBLISHED["kh0326_leading_verso_cords"] else "CONTRADICTED",
         "published": PUBLISHED["kh0326_leading_verso_cords"], "measured": leading},
        {"id": "first_cord_total_near_367", "status": "PARTIAL",
         "published": "first-cord values of the 133 groups total 'closely matches' 367 pesos",
         "measured": {"knotted_identifier_cords": first["knotted"], "their_sum": first["knotted_sum"],
                      "knotless_identifier_cords": first["knotless"],
                      "unreadable_identifier_cords": first["unreadable"]},
         "note": "360 is 98.1% of 367. PARTIAL rather than REPLICATED because the source's exact "
                 "sum was not read, thirteen identifier cords carry no knots or cannot be read, "
                 "and the sum depends on the grouping rule (see rules.positional)."},
        {"id": "table_3_split_arithmetic", "status": "REPLICATED" if table_ok else "CONTRADICTED",
         "published": "twenty splits of the six pachacas with error and p (FitzPatrick 2024, Table 3)",
         "measured": "all twenty rows recomputed from the published pachaca sizes and group counts",
         "note": "Arithmetic on published inputs; it does not test whether the split is meaningful."},
        {"id": "tribute_paid_by_moiety", "status": "NOT_TESTED",
         "published": "FitzPatrick 2024, section 4",
         "measured": first["by_side_sum"],
         "note": "That section was not read, so there is no published figure to compare with. "
                 "The measured sums by attachment side are reported for whoever has the text."},
    ]


def audit(corpus: dict | None = None) -> dict:
    if corpus is None:
        corpus = _engine().load_corpus()
    if corpus.get("sha256") != CORPUS_SHA256:
        raise Hold("CORPUS_DIGEST_NOT_PINNED")
    by_okr = {k["okr_num"]: k for k in corpus["khipus"]}
    khipus, band_in, pos_in = [], [], []
    level1 = singles = 0
    leading = None
    for okr_num, inv in SANTA:
        k = by_okr.get(okr_num)
        if k is None or k["investigator_num"] != inv:
            raise Hold(f"KHIPU_MISSING_OR_RENAMED:{okr_num}")
        cords = pendants(k)
        band = band_groups(cords)
        band_in.append((okr_num, band))
        pos_in.append((okr_num, positional_groups(cords)))
        level1 += len(cords)
        singles += len(band["singles"])
        if okr_num == "KH0326":
            letters = "".join(c["attach"] for c in cords)
            leading = len(letters) - len(letters.lstrip("V"))
        khipus.append({"okr_num": okr_num, "investigator_num": inv, "museum": k["museum"],
                       "provenance": k["provenance"], "level1_pendants": len(cords)})
    totals = {"level1_pendants": level1, "one_cord_cluster_pendants": singles,
              "pendants_in_multi_cord_clusters": level1 - singles}
    band_report = _rule_report(band_in)
    table = split_table(PACHACAS, PUBLISHED["identifier_verso"], PUBLISHED["identifier_recto"])
    table_ok = (sorted((r["verso_total"], r["recto_total"], r["error"], r["p_published_form"])
                       for r in table) == sorted(PUBLISHED_TABLE_3))
    att = band_report["identifier_attachment"]
    each = quartillos(**{"pesos": PUBLISHED["tribute_each"]["pesos"],
                         "reales": PUBLISHED["tribute_each"]["reales"],
                         "quarts": PUBLISHED["tribute_each"]["quartillos"]})
    named = sum(n for _, n in PACHACAS)
    report = {
        "schema": SCHEMA,
        "status": "POST_HOC_REPLICATION_OF_PUBLISHED_CLAIMS",
        "input_corpus_sha256": corpus["sha256"],
        "upstream_okr_revision": corpus["source"]["commit"],
        "preregistered": False,
        "historical_khipu_decipherment": False,
        "new_reading_claimed": False,
        "independent_research_lab_replication": False,
        "signature_verified": False,
        "source_paper_fully_read": False,
        "sources": SOURCES,
        "published": PUBLISHED,
        "khipus": khipus,
        "totals": totals,
        "kh0326_leading_verso_cords": leading,
        "rules": {"colour_band": band_report, "positional": _rule_report(pos_in)},
        "document": {
            "total_pesos": PUBLISHED["tribute_total_pesos"],
            "tributaries_times_stated_rate": dict(zip(
                ("pesos", "reales", "quartillos"),
                as_pesos_reales_quartillos(PUBLISHED["tributaries"] * each))),
            "note": "132 tributaries at 2 pesos 7 reales 3 quartillos come to 391 pesos 7 reales, "
                    "not the 367 the document states. Our arithmetic, assuming 8 reales to the peso "
                    "and 4 quartillos to the real; the source's footnote on this was not read.",
        },
        "table_3": table,
        "alignment_with_published_counts": _alignment(PUBLISHED["identifier_verso"],
                                                      PUBLISHED["identifier_recto"]),
        "alignment_with_corpus_counts": _alignment(att["V"], att["R"]),
        "alignment_with_corpus_counts_unspecified_as_recto": _alignment(att["V"], att["R"] + att["U"]),
        "chance_check": chance_check(PUBLISHED["identifier_verso"], PUBLISHED["identifier_recto"], named),
        "claims": _claims(band_report, totals, khipus, leading, table_ok),
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
    if args.check and json.loads(SEALED.read_text(encoding="utf-8")) != json.loads(text):
        print("HOLD: sealed report differs from recomputation")
        return 1
    for claim in report["claims"]:
        print(f"{claim['status']:<13} {claim['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
