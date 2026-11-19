#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Check two reported Puruchuco sums against the pinned OKR corpus.

Urton and Brezine (2005) described an accounting hierarchy among khipus found
together at Puruchuco: values on lower-level khipus are summed onto higher-level
ones.  The Khipu Field Guide's notebook "Replicating Puruchuco" reports that the
total of UR063 (1439) roughly equals cords 34-53 of UR068 (1447).  This module
recomputes those two numbers.  Neither source was read directly: the tier list
and both figures come from a web-search summary of the notebook, so this checks
reported figures, not the paper's cord-by-cord argument.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "szl_khipu/okr_khipu.py"
SEALED = Path(__file__).with_name("puruchuco_v1.json")
SCHEMA = "szl.okr.puruchuco-reported-sums/v1"
CORPUS_SHA256 = "6ef204b641826b37c320509952ed4181e93865af20f1cdfefd7516a49cf8ad0d"

SOURCES = [
    {"key": "urton_brezine2005",
     "cite": "Urton, G. and Brezine, C. J. (2005). Khipu Accounting in Ancient Peru. "
             "Science 309(5737): 1065-1067.",
     "doi": "10.1126/science.1113426", "read_by_this_project": False},
    {"key": "khipu_field_guide",
     "cite": "Khosla, A. Khipu Field Guide, notebook 'Replicating Puruchuco'.",
     "url": "https://khipufieldguide.com/", "read_by_this_project": False,
     "note": "tier list and the figures 1439 and 1447 taken from a web-search summary"},
]
REPORTED = {
    "tiers": {"III": ["UR067", "UR066"], "II": ["UR064", "CM009", "UR068"], "I": ["UR063", "UR073"]},
    "ur063_total": 1439,
    "ur068_span": [34, 53],
    "ur068_span_total": 1447,
}
EXPECTED = {"UR063": "KH0300", "UR064": "KH0301", "UR066": "KH0303",
            "UR067": "KH0304", "UR068": "KH0305", "UR073": "KH0310"}


class Hold(ValueError):
    """Refuse a corpus or span this check was not written for."""


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")


def digest(report: dict) -> str:
    body = {k: v for k, v in report.items() if k != "report_sha256"}
    return hashlib.sha256(canonical(body)).hexdigest()


def _engine():
    spec = importlib.util.spec_from_file_location("szl_okr_puruchuco_engine", ENGINE)
    if spec is None or spec.loader is None:
        raise Hold("ENGINE_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pendants(khipu: dict) -> list:
    """Level-1 pendants in order along each primary cord (ordinal, then id), not stored order."""
    cords = [c for c in khipu["cords"] if c["level"] == 1 and c["parent_kind"] == "primary"]
    rank: dict = {}
    for c in cords:
        rank.setdefault(c["parent"], len(rank))
    return sorted(cords, key=lambda c: (rank[c["parent"]], c["ordinal"], c["id"]))


def _value(cord: dict) -> int:
    return 0 if cord["value_status"] == "unknown" else cord["value"]


def span_sum(cords: list, first: int, last: int) -> dict:
    """Sum of pendant cords first..last, numbered from 1, both ends included."""
    if not 1 <= first <= last <= len(cords):
        raise Hold("SPAN_OUTSIDE_KHIPU")
    span = cords[first - 1:last]
    return {"sum": sum(_value(c) for c in span),
            "unreadable": sum(c["value_status"] == "unknown" for c in span)}


def window_sums(cords: list, width: int) -> list:
    return [sum(_value(c) for c in cords[i:i + width]) for i in range(len(cords) - width + 1)]


def audit(corpus: dict | None = None) -> dict:
    if corpus is None:
        corpus = _engine().load_corpus()
    if corpus.get("sha256") != CORPUS_SHA256:
        raise Hold("CORPUS_DIGEST_NOT_PINNED")
    by_inv = {k["investigator_num"]: k for k in corpus["khipus"]}
    khipus, missing = [], []
    for tier in ("III", "II", "I"):
        for name in REPORTED["tiers"][tier]:
            k = by_inv.get(name)
            if k is None:
                missing.append(name)
                continue
            if EXPECTED.get(name) != k["okr_num"]:
                raise Hold(f"KHIPU_RENAMED:{name}")
            khipus.append({"investigator_num": name, "okr_num": k["okr_num"], "tier": tier,
                           "level1_pendants": len(pendants(k))})
    khipus.sort(key=lambda k: k["investigator_num"])
    ur063, ur068 = pendants(by_inv["UR063"]), pendants(by_inv["UR068"])
    first, last = REPORTED["ur068_span"]
    total = span_sum(ur063, 1, len(ur063))
    span = span_sum(ur068, first, last)
    gap = abs(total["sum"] - span["sum"])
    width = last - first + 1
    windows = window_sums(ur068, width)
    others = [span_sum(pendants(k), 1, len(pendants(k)))["sum"] if pendants(k) else 0
              for k in corpus["khipus"] if k["investigator_num"] != "UR063"]
    report = {
        "schema": SCHEMA,
        "status": "POST_HOC_REPLICATION_OF_REPORTED_FIGURES",
        "input_corpus_sha256": corpus["sha256"],
        "upstream_okr_revision": corpus["source"]["commit"],
        "preregistered": False,
        "historical_khipu_decipherment": False,
        "new_reading_claimed": False,
        "source_paper_read": False,
        "signature_verified": False,
        "sources": SOURCES,
        "reported": REPORTED,
        "khipus": khipus,
        "not_in_corpus": missing,
        "measured": {"ur063_pendant_total": total, "ur068_cords_34_53": span, "gap": gap},
        "specificity": {
            "label": "OURS_EXPLORATORY_NOT_IN_SOURCE",
            "other_khipus_in_corpus": len(others),
            "other_khipus_with_total_within_gap_of_1447":
                sum(abs(t - span["sum"]) <= gap for t in others),
            "ur068_twenty_cord_windows": len(windows),
            "ur068_windows_within_gap_of_1439": sum(abs(w - total["sum"]) <= gap for w in windows),
            "largest_single_cord_in_span": max(_value(c) for c in ur068[first - 1:last]),
            "note": "No other khipu in the corpus has a pendant total this close to the UR068 "
                    "span. Inside UR068 the match is not sensitive to where the window starts, "
                    "because one cord (1236) carries most of the sum.",
        },
        "claims": [
            {"id": "ur063_total_1439",
             "status": "REPLICATED" if total["sum"] == REPORTED["ur063_total"] else "CONTRADICTED",
             "reported": REPORTED["ur063_total"], "measured": total},
            {"id": "ur068_cords_34_53_total_1447",
             "status": "REPLICATED" if span["sum"] == REPORTED["ur068_span_total"] else "CONTRADICTED",
             "reported": REPORTED["ur068_span_total"], "measured": span},
            {"id": "hierarchy_sums_move_upward", "status": "NOT_TESTED",
             "reported": "Urton and Brezine 2005: sums pass from level I to II to III",
             "note": "The paper's cord-by-cord correspondences were not read; only the one pair "
                     "of figures above was checked."},
            {"id": "cm009", "status": "NOT_TESTABLE",
             "note": "CM009 is listed at level II but is not in the pinned OKR corpus."},
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
    if args.check and json.loads(SEALED.read_text(encoding="utf-8")) != json.loads(text):
        print("HOLD: sealed report differs from recomputation")
        return 1
    for claim in report["claims"]:
        print(f"{claim['status']:<13} {claim['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
