#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Exact decimal sum relations in real khipus from the Open Khipu Repository (OKR).

Stdlib only (no numpy, no gradio) so the file also runs flat inside a Space.

Data: OKR ``data/khipu.db`` at commit 4039ca51f4de661d80d0160596309c983a62a9c7,
MIT licensed ("Copyright (c) 2022 Open Khipu Repository Team"),
DOI https://doi.org/10.5281/zenodo.18025748. The compact corpus shipped next to
this module is derived from that file by ``research/okr_corpus/build_corpus.py``.

What this module measures: how often a cord's knotted value equals the exact
sum of other cords' values (relation types R1..R4, see ``RELATION_RULES``) in
the pinned OKR records, compared with a within-khipu permutation null. It does
not decipher anything, and an exact sum observed here is a property of the
recorded transcription, not a proof about intent.

Fail-closed: malformed input raises ``OkrHold``. Unknown values stay ``None``;
they are never treated as zero. A digest match is integrity, not a signature.
"""

import gzip
import hashlib
import json
import math
import random
from pathlib import Path

__all__ = [
    "OkrHold",
    "CORPUS_SHA256",
    "OKR_COMMIT",
    "OKR_CSV_SHA256",
    "LONG_TYPES",
    "knot_family",
    "provenance_coverage",
    "CORPUS_FILENAME",
    "RELATIONS_FILENAME",
    "RELATION_TYPES",
    "RELATION_RULES",
    "DEFAULT_SEED",
    "default_corpus_path",
    "default_relations_path",
    "load_corpus",
    "load_relations_report",
    "list_khipus",
    "get_khipu",
    "cord_value",
    "cord_role",
    "find_relations",
    "null_model",
    "corpus_statistics",
    "build_relations_report",
    "scene",
    "khipu_card",
]

CORPUS_SCHEMA = "szl.okr_corpus/v1"
RELATIONS_SCHEMA = "szl.okr_relations/v1"
RULES_VERSION = "okr-sum-relations/v1"
CORPUS_FILENAME = "okr_corpus_v1.json.gz"
RELATIONS_FILENAME = "okr_relations_v1.json"
# sha256 of the shipped okr_corpus_v1.json.gz (tests assert the file matches).
CORPUS_SHA256 = "6ef204b641826b37c320509952ed4181e93865af20f1cdfefd7516a49cf8ad0d"

OKR_COMMIT = "4039ca51f4de661d80d0160596309c983a62a9c7"
OKR_DB_SHA256 = "607913034a0f478c5c792025d0c3cab8a9a8f05223ed6bc9c2990122a8c1c4db"
OKR_CSV_SHA256 = "d0453883762b2511f72bf48672a7c018084d67d59fe12a4a11bc3ab6b9708e5e"
OKR_DOI = "https://doi.org/10.5281/zenodo.18025748"
OKR_LICENSE = 'MIT, "Copyright (c) 2022 Open Khipu Repository Team"'

RELATION_TYPES = ("R1", "R2", "R3", "R4")
RELATION_RULES = {
    "R1": "subsidiary sum: a cord's value equals the sum of ALL its direct subsidiaries "
          "(>=2 subsidiaries, all values known, target > 0, >=2 nonzero summands)",
    "R2": "top-cord sum: a top cord's value equals the sum of 1-3 consecutive whole pendant "
          "groups that touch the top cord's position on the primary (>=2 pendants, all known, "
          "every group in a multi-group union nonzero, target > 0, >=2 nonzero summands)",
    "R3": "group-sum cord: a pendant's value equals the sum of all pendants of a different "
          "whole pendant group (group size >=2, all known, target >= 10, >=2 nonzero summands)",
    "R4": "in-group sum cord: the first or last pendant of a group (>=3 pendants) equals the "
          "sum of the other pendants of that group (all known, target > 0, >=2 nonzero summands)",
}
DEFAULT_SEED = 1981
NULL_STRATA = ("role_depth", "role_depth_magnitude")
MAX_UNION_GROUPS = 3
R3_MIN_TARGET = 10
MAX_GZ_BYTES = 16 * 1024 * 1024
MAX_JSON_BYTES = 96 * 1024 * 1024

CORD_FIELDS = (
    "id", "parent", "parent_kind", "level", "attach", "cluster", "cluster_ord", "ordinal",
    "attach_pos", "length", "term", "group_class", "color", "value", "value_status", "knots",
)
KNOT_FIELDS = ("type", "value", "turns", "pos", "cl_ord")
PRIMARY_FIELDS = ("id", "length", "color")
LONG_TYPES = ("L", "LL", "BL", "SP")
TOP_CLASSES = ("T", "TPA")
MARKER_CLASSES = ("M", "K", "X")
BROKEN_TERMS = ("B", "C")
GREY = [0.62, 0.62, 0.62]


def knot_family(code) -> str:
    """Drawing family for an OKR knot TYPE_CODE (knot_type_dc): long-knot forms
    (L, LL double long, BL belted long, SP spiral 'value like a long knot'),
    figure-eight forms (E, EE), single (S), else other. Display only; values
    always come from knot_value_type."""
    code = str(code or "").strip().upper()
    if code in LONG_TYPES:
        return "long"
    if code in ("E", "EE"):
        return "figure-eight"
    if code == "S":
        return "single"
    return "other"


class OkrHold(ValueError):
    """Fail-closed refusal: the input or artifact cannot be trusted as given."""


# --------------------------------------------------------------------------- paths


def _repo_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "research" / "okr_corpus"


def default_corpus_path() -> Path:
    flat = Path(__file__).with_name(CORPUS_FILENAME)
    if flat.is_file():
        return flat
    return _repo_dir() / CORPUS_FILENAME


def default_relations_path() -> Path:
    flat = Path(__file__).with_name(RELATIONS_FILENAME)
    if flat.is_file():
        return flat
    return _repo_dir() / RELATIONS_FILENAME


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------- values


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _knot_value(knot):
    if not isinstance(knot, dict):
        raise OkrHold("knot must be a dict")
    v = knot.get("value")
    if v is None:
        return None
    if not _is_int(v):
        raise OkrHold(f"knot value must be int or None, got {type(v).__name__}")
    return v if v > 0 else None


def cord_value(cord) -> dict:
    """Decimal value of one cord from its knots.

    Returns ``{"value": int|None, "status": "known"|"knotless"|"unknown",
    "broken": bool, "reason": str|None}``. Value is the sum of the knots'
    recorded decimal contributions (OKR ``knot_value_type``). Any knot whose
    contribution is missing or <= 0 makes the whole cord UNKNOWN (value None).
    A knotless cord is 0 with status ``knotless`` -- unless its end is broken
    or cut, in which case knots may have been lost and the value is UNKNOWN.
    """
    if not isinstance(cord, dict):
        raise OkrHold("cord must be a dict")
    knots = cord.get("knots") or []
    if not isinstance(knots, list):
        raise OkrHold("cord.knots must be a list")
    broken = cord.get("term") in BROKEN_TERMS
    if not knots:
        if broken:
            return {"value": None, "status": "unknown", "broken": True, "reason": "broken_knotless"}
        return {"value": 0, "status": "knotless", "broken": False, "reason": None}
    total = 0
    for k in knots:
        v = _knot_value(k)
        if v is None:
            return {"value": None, "status": "unknown", "broken": broken, "reason": "unknown_knot_value"}
        total += v
    return {"value": total, "status": "known", "broken": broken, "reason": None}


def cord_role(cord) -> str:
    """primary-attached role from structure: pendant | top | marker | subsidiary | orphan."""
    kind = cord.get("parent_kind")
    level = cord.get("level")
    if kind == "cord":
        return "subsidiary"
    if kind == "missing" and _is_int(level) and abs(level) >= 2:
        return "orphan"
    if level == -1 or cord.get("group_class") in TOP_CLASSES:
        return "top"
    if cord.get("group_class") in MARKER_CLASSES:
        return "marker"
    return "pendant"


# --------------------------------------------------------------------------- corpus


_CORPUS_CACHE: dict = {}
_REPORT_CACHE: dict = {}
_LIST_CACHE: dict = {}


def _expand_khipu(rec: dict, colors: dict) -> dict:
    if not isinstance(rec, dict):
        raise OkrHold("khipu record must be an object")
    for key in ("id", "okr", "cords", "primaries"):
        if key not in rec:
            raise OkrHold(f"khipu record missing {key!r}")
    if not _is_int(rec["id"]):
        raise OkrHold("khipu id must be int")
    cords = []
    for row in rec["cords"]:
        if not isinstance(row, list) or len(row) != len(CORD_FIELDS):
            raise OkrHold(f"khipu {rec['id']}: malformed cord row")
        c = dict(zip(CORD_FIELDS, row))
        if not _is_int(c["id"]):
            raise OkrHold(f"khipu {rec['id']}: cord id must be int")
        knots = []
        for krow in c["knots"]:
            if not isinstance(krow, list) or len(krow) != len(KNOT_FIELDS):
                raise OkrHold(f"cord {c['id']}: malformed knot row")
            knots.append(dict(zip(KNOT_FIELDS, krow)))
        c["knots"] = knots
        dec = cord_value(c)
        if dec["value"] != c["value"] or dec["status"] != c["value_status"]:
            raise OkrHold(f"cord {c['id']}: stored value disagrees with knot decoding")
        col = colors.get(c["color"]) if c["color"] else None
        c["rgb"] = list(col[:3]) if col else None
        cords.append(c)
    prims = []
    for row in rec["primaries"]:
        if not isinstance(row, list) or len(row) != len(PRIMARY_FIELDS):
            raise OkrHold(f"khipu {rec['id']}: malformed primary row")
        p = dict(zip(PRIMARY_FIELDS, row))
        col = colors.get(p["color"]) if p["color"] else None
        p["rgb"] = list(col[:3]) if col else None
        prims.append(p)
    return {
        "id": rec["id"],
        "okr_num": rec["okr"],
        "investigator_num": rec.get("inv") or "",
        "other_names": rec.get("alt") or "",
        "provenance": rec.get("prov") or "",
        "region": rec.get("region") or "",
        "museum": rec.get("museum") or "",
        "country": rec.get("country") or "",
        "primaries": prims,
        "cords": cords,
    }


def load_corpus(path=None, expected_sha256=None) -> dict:
    """Load and validate the compact OKR corpus (cached per path + digest).

    The shipped default file is always checked against ``CORPUS_SHA256``.
    """
    p = Path(path) if path is not None else default_corpus_path()
    if expected_sha256 is None and path is None:
        expected_sha256 = CORPUS_SHA256
    if not p.is_file():
        raise OkrHold(f"corpus not found: {p}")
    if p.stat().st_size > MAX_GZ_BYTES:
        raise OkrHold("corpus file larger than the bounded size")
    digest = _sha256_file(p)
    if expected_sha256 is not None and digest != expected_sha256:
        raise OkrHold(f"corpus digest mismatch: {digest} != {expected_sha256}")
    key = (str(p.resolve()), digest)
    if key in _CORPUS_CACHE:
        return _CORPUS_CACHE[key]
    try:
        with gzip.open(p, "rb") as fh:
            raw = fh.read(MAX_JSON_BYTES + 1)
    except (OSError, EOFError) as exc:
        raise OkrHold(f"corpus is not valid gzip: {exc}") from None
    if len(raw) > MAX_JSON_BYTES:
        raise OkrHold("decompressed corpus exceeds the bounded size")
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OkrHold(f"corpus is not valid JSON: {exc}") from None
    if not isinstance(doc, dict) or doc.get("schema") != CORPUS_SCHEMA:
        raise OkrHold("corpus schema mismatch")
    if tuple(doc.get("cord_fields") or ()) != CORD_FIELDS:
        raise OkrHold("corpus cord_fields mismatch")
    if tuple(doc.get("knot_fields") or ()) != KNOT_FIELDS:
        raise OkrHold("corpus knot_fields mismatch")
    if tuple(doc.get("primary_fields") or ()) != PRIMARY_FIELDS:
        raise OkrHold("corpus primary_fields mismatch")
    colors = doc.get("colors")
    if not isinstance(colors, dict):
        raise OkrHold("corpus colors table missing")
    khipus = [_expand_khipu(r, colors) for r in doc.get("khipus") or []]
    if not khipus:
        raise OkrHold("corpus has no khipus")
    out = {
        "schema": CORPUS_SCHEMA,
        "sha256": digest,
        "source": doc.get("source") or {},
        "colors": colors,
        "khipus": khipus,
        "by_id": {k["id"]: k for k in khipus},
        "by_okr": {k["okr_num"]: k for k in khipus},
    }
    _CORPUS_CACHE[key] = out
    return out


def get_khipu(corpus: dict, key) -> dict:
    """Look up a khipu by OKR number (``KH0079``) or integer OKR KHIPU_ID."""
    if not isinstance(corpus, dict) or "by_id" not in corpus:
        raise OkrHold("corpus must come from load_corpus()")
    if _is_int(key) and key in corpus["by_id"]:
        return corpus["by_id"][key]
    if isinstance(key, str):
        k = key.strip().upper()
        if k in corpus["by_okr"]:
            return corpus["by_okr"][k]
        if k.isdigit() and int(k) in corpus["by_id"]:
            return corpus["by_id"][int(k)]
    raise OkrHold(f"unknown khipu: {key!r}")


def load_relations_report(path=None, corpus_sha256=None) -> dict:
    """Read the precomputed corpus-wide relations report (cached)."""
    p = Path(path) if path is not None else default_relations_path()
    if not p.is_file():
        raise OkrHold(f"relations report not found: {p}")
    if p.stat().st_size > MAX_JSON_BYTES:
        raise OkrHold("relations report larger than the bounded size")
    digest = _sha256_file(p)
    key = (str(p.resolve()), digest)
    if key not in _REPORT_CACHE:
        try:
            doc = json.loads(p.read_bytes().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OkrHold(f"relations report is not valid JSON: {exc}") from None
        if not isinstance(doc, dict) or doc.get("schema") != RELATIONS_SCHEMA:
            raise OkrHold("relations report schema mismatch")
        if doc.get("rules_version") != RULES_VERSION:
            raise OkrHold("relations report was computed with different rules")
        doc["by_id"] = {k["id"]: k for k in doc.get("khipus") or []}
        doc["sha256"] = digest
        _REPORT_CACHE[key] = doc
    doc = _REPORT_CACHE[key]
    if corpus_sha256 is not None and doc.get("corpus_sha256") != corpus_sha256:
        raise OkrHold("relations report belongs to a different corpus")
    return doc


def _report_for(corpus):
    sha = corpus.get("sha256") if isinstance(corpus, dict) else None
    if not sha:
        return None
    try:
        return load_relations_report(corpus_sha256=sha)
    except OkrHold:
        return None


# --------------------------------------------------------------------------- structure


def _check_khipu(khipu) -> None:
    if not isinstance(khipu, dict):
        raise OkrHold("khipu must be a dict")
    if not _is_int(khipu.get("id")):
        raise OkrHold("khipu.id must be int")
    cords = khipu.get("cords")
    if not isinstance(cords, list):
        raise OkrHold("khipu.cords must be a list")
    seen = set()
    for c in cords:
        if not isinstance(c, dict) or not _is_int(c.get("id")):
            raise OkrHold("every cord needs an int id")
        if c["id"] in seen:
            raise OkrHold(f"duplicate cord id {c['id']}")
        seen.add(c["id"])
    for c in cords:
        if c.get("parent_kind") not in ("primary", "cord", "missing"):
            raise OkrHold(f"cord {c['id']}: parent_kind must be primary|cord|missing")
        if c["parent_kind"] == "cord" and (c.get("parent") not in seen or c.get("parent") == c["id"]):
            raise OkrHold(f"cord {c['id']}: parent cord not in khipu")
        if not _is_int(c.get("ordinal")):
            raise OkrHold(f"cord {c['id']}: ordinal must be int")
        for f in ("length", "attach_pos"):
            v = c.get(f)
            if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float))):
                raise OkrHold(f"cord {c['id']}: {f} must be a number")
    prims = khipu.get("primaries", [])
    if not isinstance(prims, list) or not all(isinstance(p, dict) for p in prims):
        raise OkrHold("khipu.primaries must be a list of dicts")


def _magnitude(v):
    return 0 if v == 0 else len(str(v))


class _Structure:
    """Topology of one khipu in index space; values are supplied separately."""

    def __init__(self, khipu):
        _check_khipu(khipu)
        cords = khipu["cords"]
        self.ids = [c["id"] for c in cords]
        idx = {cid: i for i, cid in enumerate(self.ids)}
        self.idx = idx
        self.roles = [cord_role(c) for c in cords]
        self.broken = [c.get("term") in BROKEN_TERMS for c in cords]
        decoded = [cord_value(c) for c in cords]
        self.values = [d["value"] for d in decoded]
        self.status = [d["status"] for d in decoded]
        n = len(cords)
        parent = [None] * n
        for i, c in enumerate(cords):
            if c["parent_kind"] == "cord":
                parent[i] = idx[c["parent"]]
        self.parent = parent
        root_role = [None] * n
        depth = [0] * n
        for i in range(n):
            j, d, hops = i, 1, 0
            while parent[j] is not None:
                j = parent[j]
                d += 1
                hops += 1
                if hops > n:
                    raise OkrHold("cycle in cord parent links")
            root_role[i] = self.roles[j]
            depth[i] = d
        self.root_role = root_role
        self.depth = depth
        known = [v is not None for v in self.values]
        self.known = known

        # R1 parents: >=2 direct children, parent + all children known, not in marker trees.
        children = {}
        for i in range(n):
            if parent[i] is not None:
                children.setdefault(parent[i], []).append(i)
        self.r1 = []
        for p in sorted(children):
            ch = sorted(children[p], key=lambda i: (cords[i]["ordinal"], self.ids[i]))
            if len(ch) < 2 or root_role[p] == "marker":
                continue
            if known[p] and all(known[i] for i in ch):
                self.r1.append((p, ch))

        # Primary sequences: level-1 cords per primary, in ordinal order.
        seqs = {}
        for i, c in enumerate(cords):
            if self.roles[i] in ("pendant", "top", "marker") and c["parent_kind"] != "cord":
                key = c.get("parent") if c["parent_kind"] == "primary" else None
                seqs.setdefault(key, []).append(i)
        self.groups = []  # list of member-index lists (pendant groups)
        self.group_known = []
        self.group_of = {}
        self.r2 = []  # (top index, [tuple of group indexes], ...)
        self.r4 = []  # (target, [others])
        self.pendants = []
        for key in sorted(seqs, key=lambda k: (k is None, k if k is not None else 0)):
            seq = sorted(seqs[key], key=lambda i: (cords[i]["ordinal"], self.ids[i]))
            pend = [i for i in seq if self.roles[i] == "pendant"]
            self.pendants.extend(pend)
            local = []
            for i in pend:
                cl = cords[i].get("cluster")
                if local and cords[self.groups[local[-1]][-1]].get("cluster") == cl:
                    self.groups[local[-1]].append(i)
                else:
                    self.groups.append([i])
                    local.append(len(self.groups) - 1)
                self.group_of[i] = local[-1]
            for t in seq:
                if self.roles[t] != "top" or not known[t] or not local:
                    continue
                tkey = (cords[t]["ordinal"], self.ids[t])
                ins = sum(1 for i in pend if (cords[i]["ordinal"], self.ids[i]) < tkey)
                prev_g = self.group_of[pend[ins - 1]] if ins > 0 else None
                next_g = self.group_of[pend[ins]] if ins < len(pend) else None
                if prev_g is not None and prev_g == next_g:
                    touch = {local.index(prev_g)}
                else:
                    touch = {local.index(g) for g in (prev_g, next_g) if g is not None}
                cands = []
                for a in range(len(local)):
                    for size in range(1, MAX_UNION_GROUPS + 1):
                        b = a + size - 1
                        if b >= len(local):
                            break
                        if any(a <= x <= b for x in touch):
                            cands.append(tuple(local[a:b + 1]))
                self.r2.append((t, cands))
        for g, members in enumerate(self.groups):
            self.group_known.append(all(known[i] for i in members))
        for g, members in enumerate(self.groups):
            if len(members) >= 3 and self.group_known[g]:
                self.r4.append((members[0], members[1:]))
                self.r4.append((members[-1], members[:-1]))
        self.r3_groups = [g for g, m in enumerate(self.groups) if len(m) >= 2 and self.group_known[g]]
        self.r3_targets = [i for i in self.pendants if known[i]]

    def candidates(self) -> dict:
        return {
            "R1": len(self.r1),
            "R2": sum(len(c) for _, c in self.r2),
            "R3": sum(len(self.r3_targets) - len(self.groups[g]) for g in self.r3_groups),
            "R4": len(self.r4),
        }

    def strata(self, kind: str):
        if kind not in NULL_STRATA:
            raise OkrHold(f"unknown null strata {kind!r}")
        out = {}
        for i, v in enumerate(self.values):
            if v is None:
                continue
            key = (self.root_role[i], self.roles[i] == "subsidiary", self.depth[i])
            if kind == "role_depth_magnitude":
                key = key + (_magnitude(v),)
            out.setdefault(key, []).append(i)
        return [out[k] for k in sorted(out, key=repr)]

    def iter_relations(self, vals):
        """Yield (type, target, summands tuple, groups tuple) for value vector ``vals``."""
        for p, ch in self.r1:
            tv = vals[p]
            if tv <= 0:
                continue
            s = 0
            nz = 0
            for i in ch:
                v = vals[i]
                s += v
                if v:
                    nz += 1
            if nz >= 2 and s == tv:
                yield ("R1", p, tuple(ch), ())
        gsum = []
        gnz = []
        for g, members in enumerate(self.groups):
            if self.group_known[g]:
                s = 0
                nz = 0
                for i in members:
                    v = vals[i]
                    s += v
                    if v:
                        nz += 1
                gsum.append(s)
                gnz.append(nz)
            else:
                gsum.append(None)
                gnz.append(0)
        for t, cands in self.r2:
            tv = vals[t]
            if tv <= 0:
                continue
            for union in cands:
                total = 0
                nz = 0
                size = 0
                ok = True
                for g in union:
                    s = gsum[g]
                    if s is None or (len(union) > 1 and s == 0):
                        ok = False
                        break
                    total += s
                    nz += gnz[g]
                    size += len(self.groups[g])
                if ok and size >= 2 and nz >= 2 and total == tv:
                    members = tuple(i for g in union for i in self.groups[g])
                    yield ("R2", t, members, union)
        if self.r3_groups:
            by_value = {}
            for i in self.r3_targets:
                v = vals[i]
                if v >= R3_MIN_TARGET:
                    by_value.setdefault(v, []).append(i)
            for g in self.r3_groups:
                s = gsum[g]
                if s < R3_MIN_TARGET or gnz[g] < 2:
                    continue
                for t in by_value.get(s, ()):
                    if self.group_of.get(t) != g:
                        yield ("R3", t, tuple(self.groups[g]), (g,))
        for t, rest in self.r4:
            tv = vals[t]
            if tv <= 0:
                continue
            s = 0
            nz = 0
            for i in rest:
                v = vals[i]
                s += v
                if v:
                    nz += 1
            if nz >= 2 and s == tv:
                yield ("R4", t, tuple(rest), (self.group_of[t],))

    def count(self, vals) -> dict:
        out = dict.fromkeys(RELATION_TYPES, 0)
        for rel in self.iter_relations(vals):
            out[rel[0]] += 1
        return out


def _value_vector(st: _Structure):
    return [v if v is not None else 0 for v in st.values]


def find_relations(khipu) -> list:
    """Exact sum relations (R1..R4) observed in one khipu's recorded values."""
    st = _Structure(khipu)
    vals = _value_vector(st)
    cords = khipu["cords"]
    out = []
    for typ, t, summ, groups in st.iter_relations(vals):
        ids = [st.ids[i] for i in summ]
        out.append({
            "type": typ,
            "target": st.ids[t],
            "summands": ids,
            "target_value": vals[t],
            "summand_values": [vals[i] for i in summ],
            "clusters": [cords[st.groups[g][0]].get("cluster") for g in groups],
            "involves_broken_cord": bool(st.broken[t] or any(st.broken[i] for i in summ)),
            "rule": RELATION_RULES[typ],
        })
    out.sort(key=lambda r: (r["type"], r["target"], r["summands"]))
    return out


# --------------------------------------------------------------------------- null model


def _khipu_seed(khipu_id: int, seed: int) -> int:
    h = hashlib.sha256(f"szl.okr_null/v1:{seed}:{khipu_id}".encode()).digest()
    return int.from_bytes(h[:8], "big")


def _null_counts(st: _Structure, khipu_id: int, trials: int, seed: int, strata: str):
    if not _is_int(trials) or trials < 1 or trials > 100000:
        raise OkrHold("trials must be an int in [1, 100000]")
    rng = random.Random(_khipu_seed(khipu_id, seed))
    groups = st.strata(strata)
    base = _value_vector(st)
    per_type = {t: [] for t in RELATION_TYPES}
    for _ in range(trials):
        vals = list(base)
        for members in groups:
            pool = [base[i] for i in members]
            rng.shuffle(pool)
            for i, v in zip(members, pool):
                vals[i] = v
        c = st.count(vals)
        for t in RELATION_TYPES:
            per_type[t].append(c[t])
    return per_type


def _mean_sd(xs):
    n = len(xs)
    m = sum(xs) / n
    var = sum((x - m) ** 2 for x in xs) / (n - 1) if n > 1 else 0.0
    return m, math.sqrt(var)


def _p_upper(obs, null):
    return (1 + sum(1 for x in null if x >= obs)) / (len(null) + 1)


def null_model(khipu, trials=200, seed=DEFAULT_SEED, strata="role_depth") -> dict:
    """Within-khipu permutation null for R1..R4.

    Known cord values are shuffled among cords of the same stratum (root role,
    subsidiary-or-not, depth; optionally also decimal magnitude); structure and
    unknown cords stay fixed. The identical relation search is rerun per trial.
    p = (1 + #{null >= observed}) / (trials + 1). Deterministic given ``seed``;
    the per-khipu RNG seed is derived from (seed, khipu id).
    """
    st = _Structure(khipu)
    obs = st.count(_value_vector(st))
    per_type = _null_counts(st, khipu["id"], trials, seed, strata)
    res = {
        "khipu_id": khipu["id"],
        "trials": trials,
        "seed": seed,
        "strata": strata,
        "candidates": st.candidates(),
        "observed": obs,
        "null_mean": {},
        "null_sd": {},
        "p": {},
    }
    for t in RELATION_TYPES:
        m, sd = _mean_sd(per_type[t])
        res["null_mean"][t] = round(m, 6)
        res["null_sd"][t] = round(sd, 6)
        res["p"][t] = round(_p_upper(obs[t], per_type[t]), 6)
    return res


def _bh_count(pvals, q=0.05):
    ps = sorted(pvals)
    m = len(ps)
    k = 0
    for i, p in enumerate(ps, 1):
        if p <= q * i / m:
            k = i
    return k


def _pooled_row(obs, tot):
    m, sd = _mean_sd(tot)
    return {
        "observed": obs,
        "null_mean": round(m, 4),
        "null_sd": round(sd, 4),
        "null_max": max(tot),
        "ratio_observed_to_null": round(obs / m, 3) if m > 0 else None,
        "z": round((obs - m) / sd, 2) if sd > 0 else None,
        "pooled_p": round(_p_upper(obs, tot), 6),
    }


def corpus_statistics(corpus, trials=1000, seed=DEFAULT_SEED, strata=NULL_STRATA, progress=None) -> dict:
    """Corpus-wide observed vs permutation-null totals per relation type.

    Slow (about a minute for the full corpus at 1000 trials x 2 strata); the
    shipped ``okr_relations_v1.json`` stores its result. The pooled test sums
    per-khipu null counts trial by trial (trial t of every khipu) and compares
    the sum with the observed total. Robustness row ``drop_top_khipu`` repeats
    the pooled test without the single khipu contributing most observed
    relations of that type, so one record cannot carry the corpus result alone.
    """
    khipus = corpus["khipus"] if isinstance(corpus, dict) and "khipus" in corpus else None
    if not isinstance(khipus, list):
        raise OkrHold("corpus must be a dict with a khipus list")
    if isinstance(strata, str):
        strata = (strata,)
    pre = []
    for k in khipus:
        st = _Structure(k)
        pre.append((st, st.count(_value_vector(st)), st.candidates()))
    top = {}
    for t in RELATION_TYPES:
        best = max(range(len(pre)), key=lambda i: (pre[i][1][t], -i)) if pre else None
        top[t] = best if best is not None and pre[best][1][t] > 0 else None
    per_khipu = []
    totals = {s: {t: [0] * trials for t in RELATION_TYPES} for s in strata}
    top_null = {s: {} for s in strata}
    observed = dict.fromkeys(RELATION_TYPES, 0)
    cand = dict.fromkeys(RELATION_TYPES, 0)
    with_rel = dict.fromkeys(RELATION_TYPES, 0)
    tested = dict.fromkeys(RELATION_TYPES, 0)
    pvals = {s: {t: [] for t in RELATION_TYPES} for s in strata}
    for n, (k, (st, obs, cands)) in enumerate(zip(khipus, pre)):
        entry = {"id": k["id"], "okr_num": k.get("okr_num", ""), "observed": obs,
                 "candidates": cands, "null": {}}
        for t in RELATION_TYPES:
            observed[t] += obs[t]
            cand[t] += cands[t]
            if obs[t]:
                with_rel[t] += 1
            if cands[t]:
                tested[t] += 1
        for s in strata:
            per_type = _null_counts(st, k["id"], trials, seed, s)
            summ = {"null_mean": {}, "null_sd": {}, "p": {}}
            for t in RELATION_TYPES:
                xs = per_type[t]
                acc = totals[s][t]
                for i, x in enumerate(xs):
                    acc[i] += x
                if top[t] == n:
                    top_null[s][t] = xs
                m, sd = _mean_sd(xs)
                p = _p_upper(obs[t], xs)
                summ["null_mean"][t] = round(m, 6)
                summ["null_sd"][t] = round(sd, 6)
                summ["p"][t] = round(p, 6)
                if cands[t]:
                    pvals[s][t].append(p)
            entry["null"][s] = summ
        per_khipu.append(entry)
        if progress is not None:
            progress(n + 1, len(khipus))
    by_strata = {}
    for s in strata:
        rows = {}
        for t in RELATION_TYPES:
            row = _pooled_row(observed[t], totals[s][t])
            row["khipus_tested"] = tested[t]
            row["khipus_p_le_0_01"] = sum(1 for p in pvals[s][t] if p <= 0.01)
            row["khipus_bh_q_0_05"] = _bh_count(pvals[s][t])
            if top[t] is not None:
                i = top[t]
                rest = [a - b for a, b in zip(totals[s][t], top_null[s][t])]
                drop = _pooled_row(observed[t] - pre[i][1][t], rest)
                drop["dropped_okr_num"] = khipus[i].get("okr_num", "")
                drop["dropped_observed"] = pre[i][1][t]
                row["drop_top_khipu"] = drop
            else:
                row["drop_top_khipu"] = None
            rows[t] = row
        by_strata[s] = rows
    return {
        "trials": trials,
        "seed": seed,
        "strata": list(strata),
        "min_attainable_p": round(1 / (trials + 1), 6),
        "khipus": len(khipus),
        "observed": observed,
        "candidates": cand,
        "khipus_with_relation": with_rel,
        "by_strata": by_strata,
        "per_khipu": per_khipu,
    }


def build_relations_report(corpus, trials=1000, seed=DEFAULT_SEED, progress=None) -> dict:
    """Deterministic JSON-able report: corpus statistics + per-khipu relation lists."""
    stats = corpus_statistics(corpus, trials=trials, seed=seed, progress=progress)
    rels_by_id = {}
    for k in corpus["khipus"]:
        rels_by_id[k["id"]] = [
            [r["type"], r["target"], r["summands"], r["target_value"]] for r in find_relations(k)
        ]
    khipus = []
    for e in stats.pop("per_khipu"):
        e = dict(e)
        e["n_relations"] = sum(e["observed"].values())
        e["relations"] = rels_by_id[e["id"]]
        khipus.append(e)
    return {
        "schema": RELATIONS_SCHEMA,
        "rules_version": RULES_VERSION,
        "rules": RELATION_RULES,
        "corpus_sha256": corpus.get("sha256"),
        "source": {"okr_commit": OKR_COMMIT, "okr_db_sha256": OKR_DB_SHA256, "doi": OKR_DOI,
                   "license": OKR_LICENSE},
        "label": "MEASURED on the pinned OKR records; permutation p-values; not decipherment",
        "statistics": stats,
        "relation_fields": ["type", "target", "summands", "target_value"],
        "khipus": khipus,
    }


# --------------------------------------------------------------------------- listing


def _known_fraction(khipu) -> float:
    cords = khipu["cords"]
    if not cords:
        return 0.0
    return sum(1 for c in cords if cord_value(c)["value"] is not None) / len(cords)


def list_khipus(corpus) -> list:
    """Khipus for a dropdown, best evidence first.

    With the shipped relations report (matching this corpus digest) rows rank
    by relations in excess of the permutation-null expectation
    (sum over types of max(0, observed - null mean)), so chance-level
    coincidences do not float to the top; otherwise by raw relation count.
    Ties: more relations, then a larger share of cords with known values, then
    OKR number. Each row says which basis ranked it (``rank_basis``).
    """
    if not isinstance(corpus, dict) or not isinstance(corpus.get("khipus"), list):
        raise OkrHold("corpus must be a dict with a khipus list")
    key = corpus.get("sha256")
    if key and key in _LIST_CACHE:
        return [dict(r) for r in _LIST_CACHE[key]]
    report = _report_for(corpus)
    rows = []
    for k in corpus["khipus"]:
        rep = report["by_id"].get(k["id"]) if report else None
        n_rel = rep["n_relations"] if rep is not None else len(find_relations(k))
        row = {
            "id": k["id"],
            "okr_num": k.get("okr_num", ""),
            "investigator_num": k.get("investigator_num", ""),
            "provenance": k.get("provenance", ""),
            "region": k.get("region", ""),
            "n_cords": len(k["cords"]),
            "n_knots": sum(len(c.get("knots") or []) for c in k["cords"]),
            "n_relations": n_rel,
            "known_fraction": round(_known_fraction(k), 4),
        }
        if rep is not None:
            nul = rep["null"]["role_depth"]
            row["excess_over_null"] = round(
                sum(max(0.0, rep["observed"][t] - nul["null_mean"][t]) for t in RELATION_TYPES), 3)
            tested = [nul["p"][t] for t in RELATION_TYPES if rep["candidates"][t]]
            row["min_p"] = min(tested) if tested else None
        rows.append(row)
    if rows and all("excess_over_null" in r for r in rows):
        for r in rows:
            r["rank_basis"] = "excess_over_null"
        rows.sort(key=lambda r: (-r["excess_over_null"], -r["n_relations"], -r["known_fraction"], r["okr_num"]))
    else:
        for r in rows:
            r["rank_basis"] = "n_relations"
        rows.sort(key=lambda r: (-r["n_relations"], -r["known_fraction"], r["okr_num"]))
    if key:
        _LIST_CACHE[key] = [dict(r) for r in rows]
    return rows


# --------------------------------------------------------------------------- scene


def _rgb(c):
    rgb = c.get("rgb")
    if isinstance(rgb, list) and len(rgb) == 3:
        return [round(float(x), 4) for x in rgb]
    return list(GREY)


def _bezier_arc(p0, p1, n=16):
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    h = min(4.0, 0.6 + 0.18 * math.hypot(dx, dy))
    ctrl = [(p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, max(p0[2], p1[2]) + h]
    pts = []
    for k in range(n):
        u = k / (n - 1)
        a, b, c = (1 - u) ** 2, 2 * (1 - u) * u, u * u
        pts.append([round(a * p0[j] + b * ctrl[j] + c * p1[j], 4) for j in range(3)])
    return pts


def scene(khipu, max_cords=1500, max_knots=8000) -> dict:
    """Schematic 3D primitives for one khipu (layout is illustrative, not measured).

    Primary cords run along +x; pendants hang toward -y with length from
    CORD_LENGTH (capped); top cords rise toward +y; recto/verso attachments get
    +z/-z offsets; subsidiaries branch from their parent at ATTACH_POS (or a
    default spacing) at an angle. Knots sit at their recorded cm position.
    Arcs rise in +z from each summand to the target of each relation.
    """
    _check_khipu(khipu)
    if not _is_int(max_cords) or not _is_int(max_knots) or max_cords < 1 or max_knots < 0:
        raise OkrHold("max_cords/max_knots must be positive ints")
    cords = khipu["cords"]
    roles = {c["id"]: cord_role(c) for c in cords}
    prims = khipu.get("primaries") or []
    prim_ids = [p.get("id") for p in prims]

    # Level-1 sequences per primary key (unknown parent -> first primary, schematic only).
    seqs = {}
    for c in cords:
        if c["parent_kind"] == "cord" or roles[c["id"]] == "orphan":
            continue
        key = c.get("parent") if c["parent_kind"] == "primary" and c.get("parent") in prim_ids else None
        seqs.setdefault(key, []).append(c)
    keys = [p for p in prim_ids if p in seqs] + [p for p in prim_ids if p not in seqs]
    if None in seqs:
        keys.append(None)

    # Draw order: level-1 cords by primary then ordinal, then subsidiaries breadth-first.
    children = {}
    for c in cords:
        if c["parent_kind"] == "cord":
            children.setdefault(c["parent"], []).append(c)
    for v in children.values():
        v.sort(key=lambda c: (c.get("ordinal", 0), c["id"]))
    order = []
    for key in keys:
        order.extend(sorted(seqs.get(key, []), key=lambda c: (c.get("ordinal", 0), c["id"])))
    queue = list(order)
    qi = 0
    while qi < len(queue):
        for ch in children.get(queue[qi]["id"], []):
            queue.append(ch)
        qi += 1
    truncated_cords = len(queue) > max_cords
    drawn = queue[:max_cords]

    lengths = [min(float(c.get("length") or 0), 120.0) for c in cords]
    cap = max([x for x in lengths if x > 0] or [40.0])
    y_primary = 2.0
    down_span = 7.5
    up_span = 3.5

    def scaled_len(c):
        L = float(c.get("length") or 0)
        if L <= 0:
            ks = [float(k.get("pos") or 0) for k in c.get("knots") or []]
            L = (max(ks) + 3.0) if ks else cap * 0.5
        return min(L, 120.0), min(L, 120.0) / cap

    # x positions along the primaries (raw units, normalised later).
    xraw = {}
    cursor = 0.0
    prim_spans = []
    for key in keys:
        seq = sorted(seqs.get(key, []), key=lambda c: (c.get("ordinal", 0), c["id"]))
        start = cursor
        use_pos = bool(seq) and all(float(c.get("attach_pos") or 0) > 0 for c in seq)
        for n, c in enumerate(seq):
            if use_pos:
                x = start + float(c["attach_pos"])
            else:
                if n and c.get("cluster") != seq[n - 1].get("cluster"):
                    cursor += 1.5
                cursor += 1.0
                x = cursor
            xraw[c["id"]] = x
        end = max([xraw[c["id"]] for c in seq] or [start]) + 1.0
        prim_spans.append((key, start, end))
        cursor = end + 3.0
    all_x = [s for _, s, _ in prim_spans] + [e for _, _, e in prim_spans] + list(xraw.values())
    xmin, xmax = (min(all_x), max(all_x)) if all_x else (0.0, 1.0)
    span = (xmax - xmin) or 1.0
    sx = 12.0 / span
    n_level1 = max(1, len(xraw))
    step = 12.0 / max(n_level1, 12)

    def X(x):
        return -6.0 + (x - xmin) * sx

    tubes = []
    knots_out = []
    anchors = {}
    geom = {}
    for key, s, e in prim_spans:
        p = next((p for p in prims if p.get("id") == key), None)
        tubes.append({
            "points": [[round(X(s), 4), y_primary, 0.0], [round(X(e), 4), y_primary, 0.0]],
            "radius": 0.06, "rgb": _rgb(p or {}), "role": "primary",
            "cord_id": key if _is_int(key) else -1,
        })
    zoff = {"R": 0.12, "V": -0.12}
    sib_index = {}
    for c in drawn:
        role = roles[c["id"]]
        L_cm, frac = scaled_len(c)
        if c["parent_kind"] != "cord":
            x0 = X(xraw[c["id"]])
            z0 = zoff.get(c.get("attach"), 0.0)
            start = [x0, y_primary, z0]
            if role == "top":
                end = [x0, y_primary + up_span * frac, z0]
            else:
                end = [x0, y_primary - down_span * frac, z0]
            draw_role = "top" if role == "top" else "pendant"
        else:
            par = geom.get(c["parent"])
            if par is None:
                continue
            ps, pe, pL = par
            k = sib_index.get(c["parent"], 0)
            sib_index[c["parent"]] = k + 1
            ap = float(c.get("attach_pos") or 0)
            f = ap / pL if (ap > 0 and pL > 0) else min(0.1 + 0.08 * k, 0.6)
            f = max(0.0, min(f, 1.0))
            start = [ps[j] + (pe[j] - ps[j]) * f for j in range(3)]
            up = pe[1] > ps[1]
            dy = (up_span if up else down_span) * frac * 0.85
            end = [start[0] + 0.45 * step + 0.15, start[1] + (dy if up else -dy), start[2] + 0.04 * (k + 1)]
            draw_role = "subsidiary"
        geom[c["id"]] = (start, end, L_cm)
        tubes.append({
            "points": [[round(v, 4) for v in start], [round(v, 4) for v in end]],
            "radius": 0.035 if draw_role == "pendant" or draw_role == "top" else 0.025,
            "rgb": _rgb(c), "role": draw_role, "cord_id": c["id"],
        })
        anchors[c["id"]] = [start[j] + (end[j] - start[j]) * 0.12 for j in range(3)]
    truncated_knots = False
    for c in drawn:
        g = geom.get(c["id"])
        if g is None:
            continue
        start, end, L_cm = g
        for kn in c.get("knots") or []:
            if len(knots_out) >= max_knots:
                truncated_knots = True
                break
            pos = float(kn.get("pos") or 0) + 0.4 * max(0, int(kn.get("cl_ord") or 1) - 1)
            f = max(0.0, min(pos / L_cm if L_cm > 0 else 0.5, 1.0))
            v = kn.get("value")
            knots_out.append({
                "pos": [round(start[j] + (end[j] - start[j]) * f, 4) for j in range(3)],
                "type": kn.get("type") or "?",
                "family": knot_family(kn.get("type")),
                "value": v if _is_int(v) and v > 0 else None,
                "turns": kn.get("turns"),
                "cord_id": c["id"],
                "rgb": _rgb(c),
            })
    arcs = []
    for r in find_relations(khipu):
        ids = [r["target"]] + r["summands"]
        if not all(i in anchors for i in ids):
            continue
        tgt = anchors[r["target"]]
        for sid in r["summands"]:
            if sid == r["target"]:
                continue
            arcs.append({
                "points": _bezier_arc(anchors[sid], tgt),
                "relation": r["type"], "target": r["target"], "summands": r["summands"],
                "from": sid,
            })
    pts = [p for t in tubes for p in t["points"]] + [k["pos"] for k in knots_out] + \
          [p for a in arcs for p in a["points"]]
    if pts:
        lo = [min(p[j] for p in pts) for j in range(3)]
        hi = [max(p[j] for p in pts) for j in range(3)]
    else:
        lo, hi = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
    return {
        "tubes": tubes,
        "knots": knots_out,
        "arcs": arcs,
        "bounds": {"min": [round(v, 4) for v in lo], "max": [round(v, 4) for v in hi]},
        "meta": {
            "layout": "schematic (positions from ordinals/ATTACH_POS, lengths from CORD_LENGTH, capped)",
            "n_cords_total": len(cords),
            "n_cords_drawn": len(drawn),
            "truncated_cords": truncated_cords,
            "truncated_knots": truncated_knots,
            "skipped_orphans": sum(1 for c in cords if roles[c["id"]] == "orphan"),
            "rgb_source": "OKR ascher_color_dc; grey where no colour is recorded",
        },
    }


# --------------------------------------------------------------------------- card


def provenance_coverage(corpus, report) -> dict:
    """How much of the corpus, and of the R2 top-cord evidence, comes from
    records whose provenance is blank or literally 'Unknown' in OKR."""
    if not isinstance(corpus, dict) or not isinstance(report, dict):
        raise OkrHold("corpus and relations report are required")
    if report.get("corpus_sha256") != corpus.get("sha256"):
        raise OkrHold("relations report belongs to a different corpus")
    prov = {k["id"]: str(k.get("provenance") or "").strip() for k in corpus["khipus"]}
    blank = {i for i, p in prov.items() if not p}
    unknown = {i for i, p in prov.items() if p.lower() == "unknown"}
    unsourced = blank | unknown
    r2 = {row["id"]: row["observed"]["R2"] for row in report["khipus"] if row["observed"]["R2"]}
    return {
        "records": len(prov),
        "provenance_blank": len(blank),
        "provenance_unknown": len(unknown),
        "identified_records": len(prov) - len(unsourced),
        "r2_total": sum(r2.values()),
        "r2_khipus": len(r2),
        "r2_from_unsourced": sum(v for i, v in r2.items() if i in unsourced),
        "r2_unsourced_khipus": sum(1 for i in r2 if i in unsourced),
    }


def khipu_card(khipu, trials=200, seed=DEFAULT_SEED, report=None) -> dict:
    """Short factual summary. Null p-values come from the precomputed report when it
    matches this khipu, else a live bounded null run with ``trials`` permutations."""
    _check_khipu(khipu)
    cords = khipu["cords"]
    roles = [cord_role(c) for c in cords]
    dec = [cord_value(c) for c in cords]
    rels = find_relations(khipu)
    counts = dict.fromkeys(RELATION_TYPES, 0)
    for r in rels:
        counts[r["type"]] += 1
    rep = None
    if isinstance(report, dict):
        rep = (report.get("by_id") or {}).get(khipu["id"])
        if rep is not None and rep.get("observed") != counts:
            rep = None
    if rep is not None:
        nul = rep["null"]["role_depth"]
        null = {"source": "precomputed", "trials": report["statistics"]["trials"],
                "p": nul["p"], "null_mean": nul["null_mean"], "candidates": rep["candidates"]}
    else:
        nm = null_model(khipu, trials=trials, seed=seed)
        null = {"source": "live", "trials": trials, "p": nm["p"], "null_mean": nm["null_mean"],
                "candidates": nm["candidates"]}
    return {
        "okr_num": khipu.get("okr_num", ""),
        "investigator_num": khipu.get("investigator_num", ""),
        "other_names": khipu.get("other_names", ""),
        "provenance": khipu.get("provenance", ""),
        "museum": khipu.get("museum", ""),
        "region": khipu.get("region", ""),
        "country": khipu.get("country", ""),
        "n_cords": len(cords),
        "n_pendants": roles.count("pendant"),
        "n_top": roles.count("top"),
        "n_subsidiary": roles.count("subsidiary"),
        "n_marker": roles.count("marker"),
        "n_knots": sum(len(c.get("knots") or []) for c in cords),
        "n_value_known": sum(1 for d in dec if d["status"] == "known"),
        "n_value_knotless": sum(1 for d in dec if d["status"] == "knotless"),
        "n_value_unknown": sum(1 for d in dec if d["status"] == "unknown"),
        "relations": counts,
        "null": null,
        "label": "MEASURED from the pinned OKR transcription; within-khipu permutation null; "
                 "not decipherment",
        "source": f"Open Khipu Repository @ {OKR_COMMIT[:12]} ({OKR_DOI}), MIT",
    }
