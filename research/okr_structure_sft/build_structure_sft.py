#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Build the OKR structure training and evaluation sets with the canonical knot reading.

Rebuilds the SZL OKR-structure SFT set (v3) and held-out evaluation set (v2) from the
digest-pinned public corpus research/okr_corpus/okr_corpus_v1.json.gz. Version 2 of
the training set and version 1 of the evaluation set labelled cord totals with a
turns-multiplied rule (see research/okr_value_rule) and wrote knotless broken cords
as 0. Here every value comes from szl_khipu.okr_khipu.cord_value: the sum of each
knot's recorded decimal contribution, UNKNOWN (never 0) when a knot value is missing
or a knotless cord is broken or cut.

Split: a khipu is held out when int(sha256(str(KHIPU_ID)), 16) % 10 == 0, the rule of
the previous sets (61 of the 611 khipus that have pendant cords).

Pendant cords are CORD_LEVEL 1 cords in (ordinal, id) order; "cord n" is the n-th.

Rows per khipu:
- okr-structure-qa: a factual summary (train and eval).
- okr-pendant-sum-qa: the sum of all pendant values, only when every pendant value is
  known and there are at most 60 pendants (train and eval).
- okr-cord-sequence: one text row listing every pendant cord (train only).
- okr-cipher-qa: the first pendants with a known value and at least one knot, up to
  three per training khipu and five per held-out khipu (the previous sets' counts).

Summary counts (knots, distinct colours) are taken over pendant cords, as before.

Exploratory training data. Not decipherment. Digests are integrity checks, not
signatures.
"""

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from szl_khipu import okr_khipu as okr  # noqa: E402

SCHEMA = "szl.okr_structure_sft_manifest/v1"
MANIFEST = HERE / "structure_v3_manifest.json"
TRAIN_FILE = "khipu_structure_sft_v3.jsonl"
EVAL_FILE = "khipu_structure_eval_v2.jsonl"
CIPHER_PER_KHIPU = {"train": 3, "eval": 5}
PENDANT_SUM_MAX = 60
LICENSE = "MIT (Open Khipu Repository data, DOI 10.5281/zenodo.18025748)"
READING_RULE = ("cord value = sum of OKR knot_value_type (each knot's recorded decimal contribution); "
                "UNKNOWN, never 0, when a knot value is missing or a knotless cord is broken or cut; "
                "knotless intact cords are 0")
SPLIT_RULE = "held out when int(sha256(str(KHIPU_ID)).hexdigest(), 16) % 10 == 0"
CIPHER_PROMPT = ("Khipu {kh}, cord {n}: knots in order (type + recorded value) = {tokens}. "
                 "A knot's recorded value is its decimal contribution: a single knot shows its place value "
                 "(1000, 100, 10 or 1) and a long knot its number of turns. What is the cord's total value?")


def held_out(khipu) -> bool:
    return int(hashlib.sha256(str(khipu["id"]).encode()).hexdigest(), 16) % 10 == 0


def pendants(khipu):
    return sorted((c for c in khipu["cords"] if c.get("level") == 1), key=lambda c: (c.get("ordinal") or 0, c["id"]))


def _num(x):
    return "?" if x is None else f"{x:g}"


def knot_tokens(cord):
    knots = cord.get("knots") or []
    if not knots:
        return "-"
    return ", ".join(f"{k['type']}{k['value'] if isinstance(k.get('value'), int) and k['value'] > 0 else '?'}" for k in knots)


def provenance(khipu):
    p = (khipu.get("provenance") or "").strip()
    return p if p and p.lower() != "unknown" else "provenance unrecorded"


def summary_row(khipu, pend):
    kh = khipu["okr_num"]
    vals = [okr.cord_value(c) for c in pend]
    knotted = [c for c in pend if c.get("knots")]
    known_knotted = [v["value"] for c, v in zip(pend, vals) if c.get("knots") and v["status"] == "known"]
    unknown = sum(1 for v in vals if v["status"] == "unknown")
    n_knots = sum(len(c.get("knots") or []) for c in pend)
    colors = {c.get("color") for c in pend if c.get("color")}
    prim = khipu.get("primaries") or []
    plen = _num(prim[0].get("length")) if prim else "?"
    if unknown:
        total = (f"total decimal value unknown ({unknown} pendant cords have unknown values; "
                 f"the known knotted cords sum to {sum(known_knotted)})")
    else:
        total = f"total decimal value {sum(known_knotted)}"
    text = (f"{kh} ({provenance(khipu)}): {len(pend)} pendant cords, {n_knots} knots total, "
            f"{len(colors)} distinct colors, {len(knotted)} knotted pendant cords; {total}; "
            f"primary cord length {plen}.")
    return {"prompt": f"Khipu {kh}: summarize its physical structure from the Open Khipu Repository record.",
            "completion": text, "tier": "okr-structure-qa"}


def pendant_sum_row(khipu, pend):
    vals = [okr.cord_value(c) for c in pend]
    if not pend or len(pend) > PENDANT_SUM_MAX or any(v["value"] is None for v in vals):
        return None
    listed = ", ".join(str(v["value"]) for v in vals)
    return {"prompt": f"Khipu {khipu['okr_num']} pendant cord decimal values in cord order: [{listed}]. "
                      "What is the sum of all pendant cord values on this khipu?",
            "completion": str(sum(v["value"] for v in vals)), "tier": "okr-pendant-sum-qa"}


def sequence_row(khipu, pend):
    parts = []
    for n, c in enumerate(pend, 1):
        v = okr.cord_value(c)["value"]
        parts.append(f"c{n}[len={_num(c.get('length'))},col={c.get('color') or '?'},"
                     f"val={'?' if v is None else v},k={knot_tokens(c).replace(', ', ',')}]")
    return {"text": f"khipu-sequence {khipu['okr_num']} ({provenance(khipu)}): " + " ".join(parts),
            "tier": "okr-cord-sequence"}


def cipher_rows(khipu, pend, limit):
    rows = []
    for n, c in enumerate(pend, 1):
        v = okr.cord_value(c)
        if v["status"] != "known" or not c.get("knots"):
            continue
        rows.append({"prompt": CIPHER_PROMPT.format(kh=khipu["okr_num"], n=n, tokens=knot_tokens(c)),
                     "completion": str(v["value"]), "tier": "okr-cipher-qa"})
        if len(rows) == limit:
            break
    return rows


def build(corpus=None):
    corpus = corpus or okr.load_corpus()
    train, evals = [], []
    for khipu in sorted(corpus["khipus"], key=lambda k: k["okr_num"]):
        pend = pendants(khipu)
        if not pend:
            continue
        is_eval = held_out(khipu)
        rows = [summary_row(khipu, pend)]
        ps = pendant_sum_row(khipu, pend)
        if ps:
            rows.append(ps)
        if not is_eval:
            rows.append(sequence_row(khipu, pend))
        rows.extend(cipher_rows(khipu, pend, CIPHER_PER_KHIPU["eval" if is_eval else "train"]))
        for r in rows:
            r.update({"khipu": khipu["okr_num"], "split": "eval" if is_eval else "train",
                      "rule": "canonical", "license": LICENSE})
        (evals if is_eval else train).extend(rows)
    return corpus, train, evals


def _jsonl(rows) -> bytes:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode("utf-8")


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def manifest_for(corpus, train, evals):
    def part(name, rows):
        b = _jsonl(rows)
        return {"file": name, "rows": len(rows), "sha256": _sha(b), "bytes": len(b),
                "khipus": len({r["khipu"] for r in rows}),
                "tiers": dict(sorted(Counter(r["tier"] for r in rows).items()))}
    return {
        "schema": SCHEMA,
        "builder": "research/okr_structure_sft/build_structure_sft.py",
        "builder_sha256": _sha(Path(__file__).read_bytes()),
        "corpus_sha256": corpus["sha256"],
        "okr_source": {k: corpus["source"].get(k) for k in ("commit", "db_sha256", "doi")},
        "split_rule": SPLIT_RULE,
        "reading_rule": READING_RULE,
        "cipher_rows_per_khipu": CIPHER_PER_KHIPU,
        "pendant_sum_max_pendants": PENDANT_SUM_MAX,
        "train": part(TRAIN_FILE, train),
        "eval": part(EVAL_FILE, evals),
        "label": "MEASURED counts from the digest-pinned corpus; exploratory training data; not decipherment",
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", help="write the two JSONL files and the manifest into this directory")
    ap.add_argument("--seal", action="store_true", help="also write the manifest next to this script")
    ap.add_argument("--check", action="store_true", help="rebuild in memory and compare with the committed manifest")
    a = ap.parse_args(argv)
    corpus, train, evals = build()
    man = manifest_for(corpus, train, evals)
    if a.check:
        sealed = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if sealed != man:
            print("MISMATCH: rebuilt datasets differ from the committed manifest", file=sys.stderr)
            return 1
        print(json.dumps({"check": "ok", "train_sha256": man["train"]["sha256"], "eval_sha256": man["eval"]["sha256"]}))
        return 0
    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / TRAIN_FILE).write_bytes(_jsonl(train))
        (out / EVAL_FILE).write_bytes(_jsonl(evals))
        (out / MANIFEST.name).write_text(json.dumps(man, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if a.seal:
        MANIFEST.write_text(json.dumps(man, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: man[k] for k in ("train", "eval")}, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
