#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Audit which knot-value rule an OKR-derived arithmetic label follows.

Two readings of a cord's knots are compared:

- canonical: the cord value is the sum of OKR ``knot_value_type``, each knot's
  recorded decimal contribution. research/okr_corpus uses this rule.
- turns_multiplied: long-type knots (L, LL, BL, SP) contribute
  ``knot_value_type * NUM_TURNS``. A units long knot already records its turns
  as its value, so this rule squares it: L8 counts 64, not 8.

Corpus mode replays the committed, digest-pinned OKR corpus under both rules and
counts the exact sum relations (R1-R4 of szl_khipu.okr_khipu) that each rule
leaves intact. Label mode reads prompt/completion rows that list one cord's
knots ("knots in order (type+place) = S100, S10, L2.02") and reports which rule
each completion agrees with. Prediction mode rescores model outputs against both.

Fail closed: an unparseable row or an unknown knot value is counted as such and
never scored as a pass; a misaligned prediction file is refused. Digests are
integrity checks, not signatures. Exploratory; not decipherment.
"""

import argparse
import copy
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

SCHEMA = "szl.okr_value_rule_audit/v1"
LONG_TYPES = ("L", "LL", "BL", "SP")
RULES = {
    "canonical": "cord value = sum of knot_value_type over the cord's knots (research/okr_corpus DECODING_RULES)",
    "turns_multiplied": "long-type knots (L, LL, BL, SP) contribute knot_value_type * NUM_TURNS when NUM_TURNS > 1; "
                        "other knots contribute knot_value_type",
}
KNOT_LIST_RE = re.compile(r"knots in order \(type\+place\) = (?P<knots>.+?)\. Using the decimal")
TOKEN_RE = re.compile(r"^(?P<type>[A-Za-z?']{1,3}?)(?P<value>\d+)(?:\.(?P<turns>\d+))?$")
SEALED_DEFAULT = Path(__file__).resolve().parent / "value_rule_audit_v1.json"


class AuditHold(ValueError):
    """Fail-closed refusal: the input cannot be audited as given."""


def parse_knots(text):
    """Parse 'S100, S10, L2.02' into [(type, value, turns_or_None), ...]."""
    knots = []
    for raw in str(text).split(","):
        tok = raw.strip()
        m = TOKEN_RE.match(tok)
        if not m:
            raise AuditHold(f"unparseable knot token: {tok!r}")
        turns = m.group("turns")
        knots.append((m.group("type").upper(), int(m.group("value")), int(turns) if turns is not None else None))
    if not knots:
        raise AuditHold("empty knot list")
    return knots


def cord_value(knots, rule):
    """Value of one cord under ``rule``; None when any knot value is unknown (<= 0)."""
    if rule not in RULES:
        raise AuditHold(f"unknown rule: {rule!r}")
    total = 0
    for typ, value, turns in knots:
        if value <= 0:
            return None
        if rule == "turns_multiplied" and typ in LONG_TYPES and turns is not None and turns > 1:
            total += value * turns
        else:
            total += value
    return total


def classify_label(row):
    """Return (status, detail) for one prompt/completion row."""
    prompt = row.get("prompt") if isinstance(row, dict) else None
    if not isinstance(prompt, str):
        return "unparsed", {"why": "row has no string prompt"}
    m = KNOT_LIST_RE.search(prompt)
    if not m:
        return "not_applicable", {}
    try:
        knots = parse_knots(m.group("knots"))
    except AuditHold as exc:
        return "unparsed", {"why": str(exc)}
    try:
        gold = int(str(row.get("completion", "")).strip())
    except ValueError:
        return "unparsed", {"why": "completion is not an integer"}
    canon = cord_value(knots, "canonical")
    mult = cord_value(knots, "turns_multiplied")
    detail = {"khipu": row.get("khipu"), "gold": gold, "canonical": canon, "turns_multiplied": mult}
    if canon is None or mult is None:
        return "unknown_value", detail
    if canon == mult:
        return ("rules_agree_gold_ok" if gold == canon else "rules_agree_gold_other"), detail
    if gold == canon:
        return "gold_canonical", detail
    if gold == mult:
        return "gold_turns_multiplied", detail
    return "gold_neither", detail


def audit_labels(rows):
    counts, details = Counter(), []
    for row in rows:
        status, detail = classify_label(row)
        counts[status] += 1
        if status != "not_applicable":
            details.append(dict(detail, status=status))
    return dict(sorted(counts.items())), details


def rescore_predictions(label_details, preds):
    """Rescore predictions aligned 1:1, in order, with the scored (arithmetic) label rows."""
    scored = [d for d in label_details if d["status"] != "unparsed"]
    if len(scored) != len(preds):
        raise AuditHold(f"prediction rows ({len(preds)}) != arithmetic label rows ({len(scored)})")
    hits = Counter()
    known = 0
    for i, (d, p) in enumerate(zip(scored, preds)):
        if p.get("khipu") != d.get("khipu") or p.get("gold") != d.get("gold"):
            raise AuditHold(f"prediction row {i} does not align with its label row")
        pred = p.get("pred")
        hits["published_gold"] += int(pred == d["gold"])
        if d["canonical"] is not None:
            known += 1
            hits["canonical"] += int(pred == d["canonical"])
            hits["turns_multiplied"] += int(pred == d["turns_multiplied"])
    n = len(preds)
    return {
        "rows": n,
        "exact_vs_published_gold": [hits["published_gold"], n],
        "rows_with_known_value": known,
        "exact_vs_canonical": [hits["canonical"], known],
        "exact_vs_turns_multiplied": [hits["turns_multiplied"], known],
    }


def _multiplied_copy(khipu):
    k2 = copy.deepcopy(khipu)
    for cord in k2["cords"]:
        for knot in cord.get("knots") or []:
            v, t = knot.get("value"), knot.get("turns")
            if knot.get("type") in LONG_TYPES and isinstance(v, int) and v > 0 and isinstance(t, int) and t > 1:
                knot["value"] = v * t
    return k2


def corpus_audit():
    """Replay the pinned public OKR corpus under both rules (deterministic)."""
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from szl_khipu import okr_khipu as okr

    corpus = okr.load_corpus()
    relations = {rule: Counter() for rule in RULES}
    knots_changed = cords_changed = khipus_changed = 0
    for khipu in corpus["khipus"]:
        k2 = _multiplied_copy(khipu)
        here = 0
        for c1, c2 in zip(khipu["cords"], k2["cords"]):
            n = sum(1 for a, b in zip(c1.get("knots") or [], c2.get("knots") or []) if a.get("value") != b.get("value"))
            if n:
                here += n
                if okr.cord_value(c1)["value"] != okr.cord_value(c2)["value"]:
                    cords_changed += 1
        knots_changed += here
        khipus_changed += int(here > 0)
        for r in okr.find_relations(khipu):
            relations["canonical"][r["type"]] += 1
        for r in okr.find_relations(k2):
            relations["turns_multiplied"][r["type"]] += 1
    return {
        "schema": SCHEMA,
        "corpus_sha256": corpus["sha256"],
        "label": "MEASURED on the digest-pinned OKR corpus; exploratory; not decipherment",
        "rules": RULES,
        "relation_rules": dict(sorted(okr.RELATION_RULES.items())),
        "khipus": len(corpus["khipus"]),
        "knots_changed": knots_changed,
        "cords_changed": cords_changed,
        "khipus_changed": khipus_changed,
        "relations": {rule: dict(sorted(c.items())) for rule, c in relations.items()},
    }


def _read_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise AuditHold(f"{path}:{n}: invalid JSON ({exc.msg})") from None
    return rows


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--labels", help="JSONL with prompt/completion rows (e.g. an OKR structure eval set)")
    ap.add_argument("--preds", help="JSONL predictions aligned with the arithmetic label rows (khipu, gold, pred)")
    ap.add_argument("--corpus", action="store_true", help="replay the pinned public OKR corpus under both rules")
    ap.add_argument("--seal", help="write the corpus result to this JSON file")
    ap.add_argument("--check", nargs="?", const=str(SEALED_DEFAULT), help="recompute and compare with a sealed result")
    a = ap.parse_args(argv)
    if a.check:
        sealed = json.loads(Path(a.check).read_text(encoding="utf-8"))
        fresh = corpus_audit()
        if fresh != sealed:
            print("MISMATCH: recomputed corpus audit differs from the sealed result", file=sys.stderr)
            return 1
        print(json.dumps({"check": "ok", "sealed": a.check, "relations": fresh["relations"]}, sort_keys=True))
        return 0
    out = {"schema": SCHEMA}
    if a.corpus or a.seal:
        out["corpus"] = corpus_audit()
        if a.seal:
            Path(a.seal).write_text(json.dumps(out["corpus"], indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if a.labels:
        counts, details = audit_labels(_read_jsonl(a.labels))
        out["labels"] = {"file_sha256": _sha256(a.labels), "status_counts": counts}
        if a.preds:
            out["predictions"] = dict(rescore_predictions(details, _read_jsonl(a.preds)), file_sha256=_sha256(a.preds))
    elif a.preds:
        raise AuditHold("--preds needs --labels to align against")
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AuditHold as exc:
        print(f"HOLD: {exc}", file=sys.stderr)
        sys.exit(2)
