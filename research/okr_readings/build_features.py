#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Derive three recorded cord features the v1 corpus leaves out.

Spin direction, fibre and knot direction are in the pinned Open Khipu
Repository database but not in okr_corpus_v1.  This builder copies them out,
one character per cord, in the corpus's own cord order.  It refuses any
database whose SHA-256 is not the pinned one and adds nothing that is not a
recorded field.  "U" means the field was not recorded, not that it is absent
on the object.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "szl_khipu/okr_khipu.py"
SHIPPED = Path(__file__).with_name("okr_features_v1.json.gz")
SCHEMA = "szl.okr_features/v1"
DB_SHA256 = "607913034a0f478c5c792025d0c3cab8a9a8f05223ed6bc9c2990122a8c1c4db"
CORPUS_SHA256 = "6ef204b641826b37c320509952ed4181e93865af20f1cdfefd7516a49cf8ad0d"
SHIPPED_SHA256 = "1cd7c4cd822e0783969ca69a2dfae484b8c81b48ca57989fb535d53367e1d3c9"
MAX_GZ_BYTES = 4 * 1024 * 1024
MAX_JSON_BYTES = 16 * 1024 * 1024
# One character per fibre code in the database's fiber_dc table.
FIBRE_CODES = {"A": "a", "L": "l", "CN": "c", "W": "w", "V": "v", "CL": "m",
               "CC": "x", "CW": "y", "X": "i", "H": "h", "AH": "n"}


class Hold(ValueError):
    """Refuse an unpinned database, an unknown code or a tampered file."""


def engine():
    spec = importlib.util.spec_from_file_location("szl_okr_features_engine", ENGINE)
    if spec is None or spec.loader is None:
        raise Hold("ENGINE_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def spin_code(raw) -> str:
    return raw if raw in ("S", "Z") else "U"


def fibre_code(raw) -> str:
    if raw is None or raw == "":
        return "U"
    if raw not in FIBRE_CODES:
        raise Hold(f"UNKNOWN_FIBRE_CODE:{raw!r}")
    return FIBRE_CODES[raw]


def knot_direction_signature(directions) -> str:
    """'-' no knots, 'U' none recorded, 'S' or 'Z' if all recorded agree, 'M' if mixed."""
    directions = list(directions)
    if not directions:
        return "-"
    seen = {d for d in directions if d in ("S", "Z")}
    if not seen:
        return "U"
    return seen.pop() if len(seen) == 1 else "M"


def cord_ids_digest(cords: list) -> str:
    return hashlib.sha256(",".join(str(c["id"]) for c in cords).encode("ascii")).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def build(db_path: Path) -> dict:
    if _sha256_file(db_path) != DB_SHA256:
        raise Hold("DATABASE_DIGEST_NOT_PINNED")
    corpus = engine().load_corpus()
    if corpus["sha256"] != CORPUS_SHA256:
        raise Hold("CORPUS_DIGEST_NOT_PINNED")
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        cord_rows = {cid: (twist, fibre) for cid, twist, fibre in
                     con.execute("SELECT CORD_ID, TWIST, FIBER FROM cord")}
        knots: dict = {}
        for cid, direction in con.execute(
                "SELECT CORD_ID, DIRECTION FROM knot ORDER BY CORD_ID, CLUSTER_ORDINAL, KNOT_ORDINAL"):
            knots.setdefault(cid, []).append(direction)
    finally:
        con.close()
    khipus, totals = {}, {"spin": Counter(), "fibre": Counter(), "knot_dir": Counter()}
    n_cords = 0
    for khipu in corpus["khipus"]:
        spin, fibre, knot_dir = [], [], []
        for cord in khipu["cords"]:
            if cord["id"] not in cord_rows:
                raise Hold(f"CORD_NOT_IN_DATABASE:{cord['id']}")
            twist, fib = cord_rows[cord["id"]]
            spin.append(spin_code(twist))
            fibre.append(fibre_code(fib))
            knot_dir.append(knot_direction_signature(knots.get(cord["id"], [])))
            totals["fibre"][fib if fib else "U"] += 1
        totals["spin"].update(spin)
        totals["knot_dir"].update(knot_dir)
        n_cords += len(spin)
        khipus[khipu["okr_num"]] = {"spin": "".join(spin), "fibre": "".join(fibre),
                                    "knot_dir": "".join(knot_dir),
                                    "cord_ids_sha256": cord_ids_digest(khipu["cords"])}
    return {
        "schema": SCHEMA,
        "source": {"repository": corpus["source"]["repository"], "commit": corpus["source"]["commit"],
                   "db_path": "data/khipu.db", "db_sha256": DB_SHA256,
                   "license": corpus["source"]["license"], "doi": corpus["source"]["doi"]},
        "corpus_sha256": corpus["sha256"],
        "fields": {"spin": "cord.TWIST: S, Z, or U (not recorded)",
                   "fibre": "cord.FIBER through fibre_codes, or U (not recorded)",
                   "knot_dir": "knot.DIRECTION over the cord's knots: - no knots, U none recorded, "
                               "S or Z all recorded agree, M mixed"},
        "fibre_codes": FIBRE_CODES,
        "totals": {"cords": n_cords, **{k: dict(sorted(v.items())) for k, v in totals.items()}},
        "khipus": khipus,
    }


KNOTS_SHIPPED = Path(__file__).with_name("okr_knots_v1.json.gz")
KNOTS_SCHEMA = "szl.okr_knots/v1"
KNOTS_SHA256 = "1ad88f0252fadcf489e09c1237c0a74bb92c2712d5cec97f3cffd9153cbe6c5e"
_KNOT = re.compile(r"^([A-Z?]+?)(\d*)([SZU])$")


def knot_code(kind, turns, direction) -> str:
    """One knot as TYPE, optional turn count, then S, Z or U (direction not recorded)."""
    letters = "".join(ch for ch in str(kind or "").upper() if ch.isalpha()) or "?"
    count = "" if turns is None else str(int(turns))
    return f"{letters}{count}{direction if direction in ('S', 'Z') else 'U'}"


def parse_knot(code: str) -> tuple:
    match = _KNOT.match(code)
    if match is None:
        raise Hold(f"BAD_KNOT_CODE:{code!r}")
    kind, count, direction = match.groups()
    return kind, int(count) if count else None, direction


def cord_knots(entry: dict) -> list:
    """Per cord, in corpus cord order, the list of (type, turns, direction) knots."""
    if entry["cords"] == 0:
        return []
    cords = [[parse_knot(code) for code in cord.split(",") if code] for cord in entry["knots"].split("|")]
    if len(cords) != entry["cords"]:
        raise Hold("KNOT_RECORD_CORD_COUNT_MISMATCH")
    return cords


def build_knots(db_path: Path) -> dict:
    """Every knot's type, turn count and recorded direction, plus each khipu's museum number."""
    if _sha256_file(db_path) != DB_SHA256:
        raise Hold("DATABASE_DIGEST_NOT_PINNED")
    corpus = engine().load_corpus()
    if corpus["sha256"] != CORPUS_SHA256:
        raise Hold("CORPUS_DIGEST_NOT_PINNED")
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        by_cord: dict = {}
        for cid, kind, turns, direction in con.execute(
                "SELECT CORD_ID, TYPE_CODE, NUM_TURNS, DIRECTION FROM knot "
                "ORDER BY CORD_ID, CLUSTER_ORDINAL, KNOT_ORDINAL, KNOT_ID"):
            by_cord.setdefault(cid, []).append(knot_code(kind, turns, direction))
        museum = {okr: " ".join(str(num or "").split())
                  for okr, num in con.execute("SELECT OKR_NUM, MUSEUM_NUM FROM khipu_main")}
    finally:
        con.close()
    khipus, direction, n_knots = {}, Counter(), 0
    for khipu in corpus["khipus"]:
        cords = [by_cord.get(c["id"], []) for c in khipu["cords"]]
        for codes in cords:
            direction.update(code[-1] for code in codes)
            n_knots += len(codes)
        khipus[khipu["okr_num"]] = {"knots": "|".join(",".join(codes) for codes in cords),
                                    "cords": len(cords),
                                    "museum_num": museum.get(khipu["okr_num"], "")}
    return {
        "schema": KNOTS_SCHEMA,
        "source": {"repository": corpus["source"]["repository"], "commit": corpus["source"]["commit"],
                   "db_path": "data/khipu.db", "db_sha256": DB_SHA256,
                   "license": corpus["source"]["license"], "doi": corpus["source"]["doi"]},
        "corpus_sha256": corpus["sha256"],
        "fields": {"knots": "per cord in corpus order, cords joined by |, knots by comma; each knot "
                            "is TYPE_CODE, NUM_TURNS if recorded, then DIRECTION as S, Z or U "
                            "(not recorded)",
                   "museum_num": "khipu_main.MUSEUM_NUM, whitespace collapsed"},
        "totals": {"knots": n_knots, "direction": dict(sorted(direction.items()))},
        "khipus": khipus,
    }


def load_knots(path: Path | None = None, expected_sha256: str | None = None) -> dict:
    path = KNOTS_SHIPPED if path is None else path
    blob = path.read_bytes()
    if len(blob) > MAX_GZ_BYTES:
        raise Hold("KNOTS_FILE_TOO_LARGE")
    if hashlib.sha256(blob).hexdigest() != (expected_sha256 or KNOTS_SHA256):
        raise Hold("KNOTS_DIGEST_MISMATCH")
    with gzip.GzipFile(fileobj=io.BytesIO(blob)) as gz:
        raw = gz.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise Hold("KNOTS_JSON_TOO_LARGE")
    knots = json.loads(raw)
    if knots.get("schema") != KNOTS_SCHEMA:
        raise Hold("KNOTS_SCHEMA_MISMATCH")
    return knots


def encode(features: dict) -> bytes:
    raw = json.dumps(features, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0, compresslevel=9) as gz:
        gz.write(raw)
    return buf.getvalue()


def load_features(path: Path | None = None, expected_sha256: str | None = None) -> dict:
    path = SHIPPED if path is None else path
    blob = path.read_bytes()
    if len(blob) > MAX_GZ_BYTES:
        raise Hold("FEATURES_FILE_TOO_LARGE")
    if hashlib.sha256(blob).hexdigest() != (expected_sha256 or SHIPPED_SHA256):
        raise Hold("FEATURES_DIGEST_MISMATCH")
    with gzip.GzipFile(fileobj=io.BytesIO(blob)) as gz:
        raw = gz.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise Hold("FEATURES_JSON_TOO_LARGE")
    features = json.loads(raw)
    if features.get("schema") != SCHEMA:
        raise Hold("FEATURES_SCHEMA_MISMATCH")
    return features


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", required=True, type=Path, help="path to the pinned khipu.db")
    parser.add_argument("--check", action="store_true", help="compare with the shipped file")
    parser.add_argument("--knots", action="store_true", help="build the per-knot file instead")
    args = parser.parse_args(argv)
    target, pinned, built = ((KNOTS_SHIPPED, KNOTS_SHA256, build_knots) if args.knots
                             else (SHIPPED, SHIPPED_SHA256, build))
    blob = encode(built(args.db))
    sha = hashlib.sha256(blob).hexdigest()
    if args.check:
        same = blob == target.read_bytes() and sha == pinned
        print("REPLAY_MATCH" if same else f"HOLD: rebuilt {target.name} differs from the shipped file")
        return 0 if same else 1
    target.write_bytes(blob)
    print(f"wrote {target.name} bytes={len(blob)} sha256={sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
