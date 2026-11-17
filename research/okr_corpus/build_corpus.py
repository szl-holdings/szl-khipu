#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Deterministic builder for the compact OKR khipu corpus (and its relations report).

    python3 -I research/okr_corpus/build_corpus.py --db PATH/khipu.db \
        --out research/okr_corpus/okr_corpus_v1.json.gz [--relations] [--check]

Refuses any khipu.db whose SHA-256 differs from the pinned OKR commit. The
database is opened read-only and every text field is treated as untrusted
data (normalised, length-capped, never executed or interpreted). Output is
byte-identical across runs: sorted keys, fixed separators, gzip mtime=0.

Source: Open Khipu Repository, data/khipu.db @ 4039ca51f4de661d80d0160596309c983a62a9c7
(MIT, "Copyright (c) 2022 Open Khipu Repository Team", DOI 10.5281/zenodo.18025748).
"""

import argparse
import csv
import gzip
import hashlib
import importlib.util
import io
import json
import math
import sqlite3
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
ENGINE_PATH = REPO / "szl_khipu" / "okr_khipu.py"

PINNED_DB_SHA256 = "607913034a0f478c5c792025d0c3cab8a9a8f05223ed6bc9c2990122a8c1c4db"
PINNED_CSV_SHA256 = "d0453883762b2511f72bf48672a7c018084d67d59fe12a4a11bc3ab6b9708e5e"
OKR_COMMIT = "4039ca51f4de661d80d0160596309c983a62a9c7"
OKR_REPO = "https://github.com/khipulab/open-khipu-repository"
BUILDER_VERSION = "okr-corpus-builder/v1"
TEXT_CAP = 200


def _load_engine():
    # Loaded by path so the builder does not import the szl_khipu package (numpy).
    spec = importlib.util.spec_from_file_location("okr_khipu_engine", ENGINE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_text(x) -> str:
    """Untrusted text -> printable, single-line, capped string."""
    if x is None:
        return ""
    s = str(x)
    s = "".join(ch if unicodedata.category(ch)[0] != "C" else " " for ch in s)
    s = " ".join(s.split())
    if len(s) >= 2 and s[0] == s[-1] == '"':
        s = s[1:-1].strip()
    return s[:TEXT_CAP]


def _int(x):
    if x is None or x == "":
        return None
    try:
        return int(x)
    except (TypeError, ValueError):
        try:
            return int(float(x))
        except (TypeError, ValueError):
            return None


def _num(x, nd=2):
    if x is None or x == "":
        return 0.0
    try:
        v = round(float(x), nd)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(v):
        return 0.0
    return v + 0.0


def _knot_type(t) -> str:
    t = clean_text(t).upper()
    if t in ("", "''", '""'):
        return "?"
    return t


def read_csv(path: Path) -> dict:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    out = {}
    for r in rows:
        num = clean_text(r.get("OKR Number"))
        if num:
            out[num] = {"alt": clean_text(r.get("Other Names")), "country": clean_text(r.get("Country"))}
    return out


def extract(db_path: Path, csv_path: Path, engine) -> tuple:
    uri = db_path.resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        q = con.execute
        csv_meta = read_csv(csv_path)

        colors_dc = {}
        for code, descr, r, g, b in q("SELECT AS_COLOR_CD, COLOR_DESCR, R_DEC, G_DEC, B_DEC FROM ascher_color_dc"):
            code = clean_text(code)
            if code and r is not None and g is not None and b is not None:
                colors_dc[code] = [round(float(r), 4), round(float(g), 4), round(float(b), 4), clean_text(descr)]

        # Dominant colour per cord: longest recorded range, then earliest, then row id.
        best = {}
        for cid, color_id, c1, full, beg, end, pflag in q(
            "SELECT CORD_ID, color_id, COLOR_CD_1, FULL_COLOR, RANGE_BEG, RANGE_END, PCORD_FLAG FROM ascher_cord_color"
        ):
            code1 = clean_text(c1)
            label = clean_text(full) or code1
            if not label:
                continue
            span = (float(end or 0) - float(beg or 0))
            key = (-span, float(beg or 0), _int(color_id) or 0)
            k = (int(pflag or 0), cid)
            if k not in best or key < best[k][0]:
                best[k] = (key, label, code1)
        color_table = {}
        cord_color = {}
        prim_color = {}
        for (pflag, cid), (_, label, code1) in best.items():
            (prim_color if pflag else cord_color)[cid] = label
            if label not in color_table and code1 in colors_dc:
                r, g, b, descr = colors_dc[code1]
                color_table[label] = [r, g, b, descr if label == code1 else f"{descr} (first component of {label})"]

        group_class = {}
        for cl, gc in q("SELECT CLUSTER_ID, GROUPING_CLASS FROM cord_cluster"):
            group_class[cl] = clean_text(gc).upper()

        kc_pos = {}
        for clid, start in q("SELECT CLUSTER_ID, START_POS FROM knot_cluster"):
            kc_pos[clid] = _num(start)

        khipus = {}
        for row in q("SELECT KHIPU_ID, OKR_NUM, INVESTIGATOR_NUM, PROVENANCE, REGION, MUSEUM_NAME FROM khipu_main"):
            kid, okr, inv, prov, region, museum = row
            okr = clean_text(okr)
            meta = csv_meta.get(okr, {})
            khipus[int(kid)] = {
                "id": int(kid), "okr": okr, "inv": clean_text(inv), "prov": clean_text(prov),
                "region": clean_text(region), "museum": clean_text(museum),
                "alt": meta.get("alt", ""), "country": meta.get("country", ""),
                "primaries": [], "cords": [],
            }

        prim_owner = {}
        for kid, pid, plen in q("SELECT KHIPU_ID, PCORD_ID, PCORD_LENGTH FROM primary_cord ORDER BY KHIPU_ID, PCORD_ID"):
            kid, pid = int(kid), int(pid)
            prim_owner[pid] = kid
            if kid in khipus:
                khipus[kid]["primaries"].append([pid, _num(plen), prim_color.get(pid, "")])

        cord_rows = list(q(
            "SELECT KHIPU_ID, CORD_ID, PENDANT_FROM, CORD_LEVEL, ATTACHMENT_TYPE, CLUSTER_ID, CLUSTER_ORDINAL, "
            "CORD_ORDINAL, ATTACH_POS, CORD_LENGTH, TERMINATION FROM cord ORDER BY KHIPU_ID, CORD_ID"
        ))
        cord_owner = {int(r[1]): int(r[0]) for r in cord_rows}

        knots_by_cord = {}
        orphan_knots = 0
        knot_unknown = 0
        knot_nonstandard = 0
        for cid, typ, kval, clid, kid_, kord, clord, turns in q(
            "SELECT CORD_ID, TYPE_CODE, knot_value_type, CLUSTER_ID, KNOT_ID, KNOT_ORDINAL, CLUSTER_ORDINAL, NUM_TURNS FROM knot"
        ):
            if cid not in cord_owner:
                orphan_knots += 1
                continue
            t = _knot_type(typ)
            v = _int(kval)
            if v is None or v <= 0:
                v = None
                knot_unknown += 1
            else:
                s = str(v)
                if not (s[0] in "123456789" and set(s[1:]) <= {"0"}):
                    knot_nonstandard += 1
            nt = _int(turns)
            nt = nt if (t in ("L", "LL", "BL", "SP") and nt is not None and nt > 0) else None
            pos = kc_pos.get(clid)
            ko = _num(kord) if kord is not None else float("inf")
            knots_by_cord.setdefault(cid, []).append(
                ((pos if pos is not None else float("inf"), _int(clord) or 0, ko, _int(kid_) or 0),
                 [t, v, nt, pos, _int(clord)])
            )

        stats = {"parent_kind": {}, "value_status": {}, "unknown_reason": {}, "role": {}}
        for kid, cid, pf, lvl, att, cl, clo, ordn, apos, clen, term in cord_rows:
            kid, cid = int(kid), int(cid)
            pf = _int(pf)
            if pf is not None and prim_owner.get(pf) == kid:
                pkind, parent = "primary", pf
            elif pf is not None and cord_owner.get(pf) == kid and pf != cid:
                pkind, parent = "cord", pf
            else:
                pkind, parent = "missing", None
            knots = [k for _, k in sorted(knots_by_cord.get(cid, []), key=lambda e: e[0])]
            rec = {
                "id": cid, "parent": parent, "parent_kind": pkind, "level": _int(lvl),
                "attach": clean_text(att).upper(), "cluster": _int(cl), "cluster_ord": _int(clo),
                "ordinal": _int(ordn) if _int(ordn) is not None else 0,
                "attach_pos": _num(apos), "length": _num(clen), "term": clean_text(term).upper(),
                "group_class": group_class.get(_int(cl), ""), "color": cord_color.get(cid, ""),
                "knots": [dict(zip(engine.KNOT_FIELDS, k)) for k in knots],
            }
            dec = engine.cord_value(rec)
            rec["value"] = dec["value"]
            rec["value_status"] = dec["status"]
            role = engine.cord_role(rec)
            for name, val in (("parent_kind", pkind), ("value_status", dec["status"]), ("role", role)):
                stats[name][val] = stats[name].get(val, 0) + 1
            if dec["reason"]:
                stats["unknown_reason"][dec["reason"]] = stats["unknown_reason"].get(dec["reason"], 0) + 1
            row = [rec[f] for f in engine.CORD_FIELDS if f != "knots"] + [knots]
            if kid not in khipus:
                raise SystemExit(f"cord {cid} references unknown khipu {kid}")
            khipus[kid]["cords"].append(row)
    finally:
        con.close()

    used_colors = {c[engine.CORD_FIELDS.index("color")] for k in khipus.values() for c in k["cords"]}
    used_colors |= {p[2] for k in khipus.values() for p in k["primaries"]}
    colors = {k: v for k, v in color_table.items() if k in used_colors}
    ordered = [khipus[k] for k in sorted(khipus, key=lambda i: (khipus[i]["okr"], i))]
    counts = {
        "khipus": len(ordered),
        "khipus_without_cords": sum(1 for k in ordered if not k["cords"]),
        "primary_cords": sum(len(k["primaries"]) for k in ordered),
        "cords": sum(len(k["cords"]) for k in ordered),
        "knots": sum(len(c[-1]) for k in ordered for c in k["cords"]),
        "knots_excluded_no_cord_row": orphan_knots,
        "knots_unknown_value": knot_unknown,
        "knots_nonstandard_value": knot_nonstandard,
        "cords_by_parent_kind": dict(sorted(stats["parent_kind"].items())),
        "cords_by_value_status": dict(sorted(stats["value_status"].items())),
        "cords_unknown_by_reason": dict(sorted(stats["unknown_reason"].items())),
        "cords_by_role": dict(sorted(stats["role"].items())),
        "color_labels": len(colors),
    }
    return ordered, colors, counts


DECODING_RULES = [
    "cord value = sum of OKR knot.knot_value_type (each knot's recorded decimal contribution) over the cord's knots",
    "knot_value_type NULL or <= 0 -> that knot's value is unknown (stored null) -> the cord value is UNKNOWN (null), never 0",
    "a cord with no knot rows has value 0 and value_status 'knotless'",
    "a knotless cord whose termination is B (broken) or C (cut) is UNKNOWN (reason broken_knotless): knots may be lost",
    "a broken cord that has knots keeps its recorded sum (value_status 'known'); relations flag involves_broken_cord",
    "knot type '' or \"''\" is stored as '?'; its recorded value is kept when > 0",
    "knot turns are NUM_TURNS for long-type knots (L, LL, BL, SP) when > 0, else null",
    "knot pos = knot_cluster.START_POS in cm from the cord's attachment; knot_cluster.TOTAL_VALUE and END_POS are not used (0 or NULL throughout)",
    "parent: PENDANT_FROM equal to a primary_cord.PCORD_ID of the same khipu -> 'primary'; equal to a CORD_ID of the same khipu -> 'cord'; otherwise 'missing'",
    "role: parent cord -> subsidiary; CORD_LEVEL -1 or cluster GROUPING_CLASS T/TPA -> top; GROUPING_CLASS M/K/X -> marker; |level|>=2 with missing parent -> orphan; else pendant",
    "colour: dominant (longest) ascher_cord_color range; rgb from ascher_color_dc for its first colour code; absent -> no rgb (renderers use neutral grey)",
    "knots with no matching cord row are excluded and counted",
    "text fields: control characters removed, whitespace collapsed, surrounding quotes stripped, capped at 200 chars",
]


def build_corpus_bytes(db: Path, csv_path: Path, engine) -> tuple:
    khipus, colors, counts = extract(db, csv_path, engine)
    doc = {
        "schema": engine.CORPUS_SCHEMA,
        "source": {
            "repository": OKR_REPO, "commit": OKR_COMMIT, "db_path": "data/khipu.db",
            "db_sha256": PINNED_DB_SHA256, "csv_path": "data/okr-kh-numbers.csv",
            "csv_sha256": PINNED_CSV_SHA256, "license": engine.OKR_LICENSE, "doi": engine.OKR_DOI,
        },
        "cord_fields": list(engine.CORD_FIELDS),
        "knot_fields": list(engine.KNOT_FIELDS),
        "primary_fields": list(engine.PRIMARY_FIELDS),
        "colors": colors,
        "khipus": khipus,
    }
    raw = json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0, compresslevel=9) as gz:
        gz.write(raw)
    return buf.getvalue(), raw, counts


def manifest_bytes(gz: bytes, raw: bytes, counts: dict, engine) -> bytes:
    man = {
        "schema": "szl.okr_corpus_manifest/v1",
        "builder": BUILDER_VERSION,
        "source": {
            "repository": OKR_REPO,
            "commit": OKR_COMMIT,
            "db_url": f"https://raw.githubusercontent.com/khipulab/open-khipu-repository/{OKR_COMMIT}/data/khipu.db",
            "db_sha256": PINNED_DB_SHA256,
            "csv_url": f"https://raw.githubusercontent.com/khipulab/open-khipu-repository/{OKR_COMMIT}/data/okr-kh-numbers.csv",
            "csv_sha256": PINNED_CSV_SHA256,
        },
        "corpus_file": engine.CORPUS_FILENAME,
        "corpus_sha256": hashlib.sha256(gz).hexdigest(),
        "corpus_json_sha256": hashlib.sha256(raw).hexdigest(),
        "corpus_bytes": len(gz),
        "counts": counts,
        "decoding_rules": DECODING_RULES,
        "license": "Data: MIT, Copyright (c) 2022 Open Khipu Repository Team (see LICENSE-OKR.txt). "
                   "Builder code: Apache-2.0, SZL Holdings.",
        "doi": engine.OKR_DOI,
        "integrity_note": "sha256 digests are integrity checks, not signatures",
    }
    return (json.dumps(man, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def relations_bytes(corpus_path: Path, corpus_sha: str, engine, trials: int, verbose: bool) -> bytes:
    corpus = engine.load_corpus(corpus_path, expected_sha256=corpus_sha)

    def progress(i, n):
        if verbose and (i % 50 == 0 or i == n):
            print(f"  null model {i}/{n}", file=sys.stderr, flush=True)

    rep = engine.build_relations_report(corpus, trials=trials, progress=progress)
    return (json.dumps(rep, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", required=True, type=Path, help="path to OKR data/khipu.db (pinned sha256)")
    ap.add_argument("--csv", type=Path, default=None, help="path to okr-kh-numbers.csv (default: next to --db)")
    ap.add_argument("--out", type=Path, default=HERE / "okr_corpus_v1.json.gz")
    ap.add_argument("--manifest", type=Path, default=None)
    ap.add_argument("--relations", nargs="?", const=HERE / "okr_relations_v1.json", type=Path, default=None,
                    help="also build the relations report (slow); optional output path")
    ap.add_argument("--trials", type=int, default=1000)
    ap.add_argument("--check", action="store_true", help="re-derive and compare bytes with the files on disk")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)

    engine = _load_engine()
    csv_path = a.csv or a.db.with_name("okr-kh-numbers.csv")
    if not a.db.is_file():
        print(f"REFUSED: db not found: {a.db}", file=sys.stderr)
        return 2
    if not csv_path.is_file():
        print(f"REFUSED: csv not found: {csv_path}", file=sys.stderr)
        return 2
    got = sha256_file(a.db)
    if got != PINNED_DB_SHA256:
        print(f"REFUSED: db sha256 {got} != pinned {PINNED_DB_SHA256}", file=sys.stderr)
        return 2
    got = sha256_file(csv_path)
    if got != PINNED_CSV_SHA256:
        print(f"REFUSED: csv sha256 {got} != pinned {PINNED_CSV_SHA256}", file=sys.stderr)
        return 2

    gz, raw, counts = build_corpus_bytes(a.db, csv_path, engine)
    if a.check and a.out.is_file():
        # Content is what must reproduce. A different zlib build may emit a
        # different (equally valid) gzip stream for identical JSON; in that case
        # the shipped, digest-pinned stream is used for the manifest/report check.
        shipped = a.out.read_bytes()
        try:
            same_content = gzip.decompress(shipped) == raw
        except OSError:
            same_content = False
        if same_content and shipped != gz:
            print("NOTE: decompressed corpus JSON is byte-identical; gzip stream differs "
                  "(zlib build) — checking against the shipped pinned stream", file=sys.stderr)
            gz = shipped
    man = manifest_bytes(gz, raw, counts, engine)
    man_path = a.manifest or a.out.with_name(a.out.name.replace(".json.gz", "") + ".manifest.json")
    corpus_sha = hashlib.sha256(gz).hexdigest()

    if a.check:
        ok = True
        for path, data, label in ((a.out, gz, "corpus"), (man_path, man, "manifest")):
            if not path.is_file() or path.read_bytes() != data:
                ok = False
                print(f"MISMATCH: {label} {path}", file=sys.stderr)
                if label == "corpus" and path.is_file():
                    try:
                        same_json = gzip.decompress(path.read_bytes()) == raw
                    except OSError:
                        same_json = False
                    if same_json:
                        print("  decompressed JSON is identical; only the gzip stream differs "
                              "(different zlib build)", file=sys.stderr)
            else:
                print(f"OK: {label} {path} sha256={hashlib.sha256(data).hexdigest()}")
        if a.relations is not None:
            rel = relations_bytes(a.out, corpus_sha, engine, a.trials, a.verbose)
            if not a.relations.is_file() or a.relations.read_bytes() != rel:
                ok = False
                print(f"MISMATCH: relations {a.relations}", file=sys.stderr)
            else:
                print(f"OK: relations {a.relations} sha256={hashlib.sha256(rel).hexdigest()}")
        return 0 if ok else 1

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_bytes(gz)
    man_path.write_bytes(man)
    print(f"wrote {a.out} ({len(gz)} bytes) sha256={corpus_sha}")
    print(f"wrote {man_path}")
    if a.relations is not None:
        rel = relations_bytes(a.out, corpus_sha, engine, a.trials, a.verbose)
        a.relations.write_bytes(rel)
        print(f"wrote {a.relations} ({len(rel)} bytes) sha256={hashlib.sha256(rel).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
