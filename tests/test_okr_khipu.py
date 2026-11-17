#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""OKR khipu sum-relation engine: decoding, relations, null model, scene, corpus pins.

The full deterministic rebuild needs the pinned OKR khipu.db; point SZL_OKR_DB at it
(or place it at research/okr_corpus/khipu.db, which is not committed). Everything
else is hermetic.
"""

import copy
import gzip
import hashlib
import importlib.util
import json
import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from szl_khipu import okr_khipu as ok

ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "research" / "okr_corpus"
CORPUS = CORPUS_DIR / "okr_corpus_v1.json.gz"
MANIFEST = CORPUS_DIR / "okr_corpus_v1.manifest.json"
REPORT = CORPUS_DIR / "okr_relations_v1.json"
BUILDER = CORPUS_DIR / "build_corpus.py"


def _builder():
    spec = importlib.util.spec_from_file_location("okr_build_corpus_under_test", BUILDER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _pinned_db():
    cands = [os.environ.get("SZL_OKR_DB"), str(CORPUS_DIR / "khipu.db")]
    for c in cands:
        if c and Path(c).is_file():
            return Path(c)
    return None


# ----------------------------------------------------------------- synthetic khipus


def knots_for(n):
    """Ascher decimal encoding: S knots for tens and up, L (2-9) or E (1) for units."""
    out = []
    digits = str(n)
    for place, d in enumerate(reversed(digits)):
        d = int(d)
        if not d:
            continue
        if place == 0:
            if d == 1:
                out.append({"type": "E", "value": 1, "turns": None, "pos": 30.0, "cl_ord": 1})
            else:
                out.append({"type": "L", "value": d, "turns": d, "pos": 30.0, "cl_ord": 1})
        else:
            for j in range(d):
                out.append({"type": "S", "value": 10 ** place, "turns": None,
                            "pos": 30.0 - 6.0 * place, "cl_ord": j + 1})
    return out


def cord(cid, value, ordinal, cluster, parent=100, kind="primary", level=1, group_class="",
         term="K", attach="R", length=40.0, color="", rgb=None):
    return {
        "id": cid, "parent": parent, "parent_kind": kind, "level": level, "attach": attach,
        "cluster": cluster, "cluster_ord": 1, "ordinal": ordinal, "attach_pos": 0.0,
        "length": length, "term": term, "group_class": group_class, "color": color, "rgb": rgb,
        "knots": knots_for(value) if value is not None else [],
    }


def synthetic():
    """One relation of each type, by construction (see test docstrings)."""
    cords = [
        cord(1, 7, 1, 1),
        cord(2, 5, 2, 1),
        cord(3, 12, 3, 9, level=-1, group_class="T"),     # top cord: 12 = 7 + 5     (R2)
        cord(4, 60, 4, 2),                                # head: 60 = 40 + 20        (R4)
        cord(5, 40, 5, 2, rgb=[0.2, 0.3, 0.4]),           # parent: 40 = 15 + 25      (R1)
        cord(6, 20, 6, 2),
        cord(7, 33, 7, 3),
        cord(8, 11, 8, 3),
        cord(9, 44, 9, 4, attach="V"),                    # 44 = sum of group 3       (R3)
        cord(10, 15, 1, 20, parent=5, kind="cord", level=2),
        cord(11, 25, 2, 20, parent=5, kind="cord", level=2),
    ]
    return {"id": 1, "okr_num": "SYN0001", "investigator_num": "", "other_names": "",
            "provenance": "synthetic", "region": "", "museum": "", "country": "",
            "primaries": [{"id": 100, "length": 50.0, "color": "", "rgb": None}], "cords": cords}


def by_id(k, cid):
    return next(c for c in k["cords"] if c["id"] == cid)


def summary(rels):
    return sorted((r["type"], r["target"], tuple(r["summands"])) for r in rels)


# ----------------------------------------------------------------- tests


class ValueDecoding(unittest.TestCase):
    def test_single_long_figure_eight(self):
        c = cord(1, 135, 1, 1)
        self.assertEqual([k["type"] for k in c["knots"]], ["L", "S", "S", "S", "S"])
        self.assertEqual(ok.cord_value(c), {"value": 135, "status": "known", "broken": False, "reason": None})
        self.assertEqual(ok.cord_value(cord(2, 1, 1, 1))["value"], 1)          # E knot = 1
        self.assertEqual(ok.cord_value(cord(3, 2001, 1, 1))["value"], 2001)    # S1000 x2 + E

    def test_unknown_knot_makes_cord_unknown_never_zero(self):
        c = cord(1, 135, 1, 1)
        c["knots"][0]["value"] = None
        self.assertEqual(ok.cord_value(c)["value"], None)
        self.assertEqual(ok.cord_value(c)["status"], "unknown")
        c["knots"][0]["value"] = 0                           # OKR stores 0 for unreadable knots
        self.assertIsNone(ok.cord_value(c)["value"])

    def test_knotless_is_zero_but_flagged(self):
        c = cord(1, None, 1, 1)
        self.assertEqual(ok.cord_value(c), {"value": 0, "status": "knotless", "broken": False, "reason": None})

    def test_broken_knotless_is_unknown(self):
        c = cord(1, None, 1, 1, term="B")
        d = ok.cord_value(c)
        self.assertIsNone(d["value"])
        self.assertEqual(d["reason"], "broken_knotless")
        b = cord(2, 23, 1, 1, term="B")
        self.assertEqual(ok.cord_value(b)["value"], 23)
        self.assertTrue(ok.cord_value(b)["broken"])

    def test_bad_knot_values_hold(self):
        c = cord(1, 5, 1, 1)
        c["knots"][0]["value"] = True
        with self.assertRaises(ok.OkrHold):
            ok.cord_value(c)
        c["knots"][0]["value"] = "5"
        with self.assertRaises(ok.OkrHold):
            ok.cord_value(c)
        with self.assertRaises(ok.OkrHold):
            ok.cord_value("not a cord")


class Relations(unittest.TestCase):
    def test_each_relation_type_found(self):
        rels = ok.find_relations(synthetic())
        self.assertEqual(summary(rels), [
            ("R1", 5, (10, 11)),
            ("R2", 3, (1, 2)),
            ("R3", 9, (7, 8)),
            ("R4", 4, (5, 6)),
        ])
        r1 = next(r for r in rels if r["type"] == "R1")
        self.assertEqual((r1["target_value"], r1["summand_values"]), (40, [15, 25]))
        self.assertFalse(r1["involves_broken_cord"])

    def test_corrupt_one_knot_relation_disappears(self):
        k = synthetic()
        by_id(k, 10)["knots"][0]["value"] = None          # subsidiary value now UNKNOWN
        self.assertNotIn("R1", {r["type"] for r in ok.find_relations(k)})
        k = synthetic()
        by_id(k, 10)["knots"] = knots_for(16)             # off by one: no longer a sum
        self.assertNotIn("R1", {r["type"] for r in ok.find_relations(k)})
        k = synthetic()
        by_id(k, 3)["knots"] = knots_for(13)
        self.assertNotIn("R2", {r["type"] for r in ok.find_relations(k)})

    def test_trivial_and_single_summand_not_counted(self):
        k = synthetic()
        for cid in (5, 10, 11):                          # 0 = 0 + 0
            by_id(k, cid)["knots"] = []
        self.assertNotIn("R1", {r["type"] for r in ok.find_relations(k)})
        k = synthetic()
        by_id(k, 5)["knots"] = knots_for(15)              # 15 = 15 + 0: equality, not a sum
        by_id(k, 11)["knots"] = []
        self.assertNotIn("R1", {r["type"] for r in ok.find_relations(k)})

    def test_r3_threshold_and_own_group_excluded(self):
        k = synthetic()
        by_id(k, 7)["knots"] = knots_for(5)
        by_id(k, 8)["knots"] = knots_for(4)
        by_id(k, 9)["knots"] = knots_for(9)               # 9 = 5 + 4 but target < 10
        self.assertNotIn("R3", {r["type"] for r in ok.find_relations(k)})

    def test_marker_and_orphan_cords_not_searched(self):
        k = synthetic()
        by_id(k, 9)["group_class"] = "M"
        self.assertNotIn("R3", {r["type"] for r in ok.find_relations(k)})
        k = synthetic()
        k["cords"].append(cord(50, 9, 1, 30, parent=None, kind="missing", level=2))
        self.assertEqual(len(ok.find_relations(k)), 4)

    def test_bad_input_holds(self):
        with self.assertRaises(ok.OkrHold):
            ok.find_relations("KH0001")
        with self.assertRaises(ok.OkrHold):
            ok.find_relations({"id": 1, "cords": "nope"})
        k = synthetic()
        k["cords"].append(copy.deepcopy(k["cords"][0]))
        with self.assertRaises(ok.OkrHold):
            ok.find_relations(k)
        k = synthetic()
        by_id(k, 10)["parent"] = 999
        with self.assertRaises(ok.OkrHold):
            ok.find_relations(k)
        k = synthetic()
        by_id(k, 1)["parent_kind"] = "sideways"
        with self.assertRaises(ok.OkrHold):
            ok.find_relations(k)
        k = synthetic()
        by_id(k, 1)["length"] = "40 cm"
        with self.assertRaises(ok.OkrHold):
            ok.scene(k)
        k = synthetic()
        k["primaries"] = ["P1"]
        with self.assertRaises(ok.OkrHold):
            ok.scene(k)


class NullModel(unittest.TestCase):
    def test_deterministic_and_well_formed(self):
        a = ok.null_model(synthetic(), trials=60, seed=7)
        b = ok.null_model(synthetic(), trials=60, seed=7)
        self.assertEqual(a, b)
        self.assertEqual(a["observed"], {"R1": 1, "R2": 1, "R3": 1, "R4": 1})
        for t in ok.RELATION_TYPES:
            self.assertGreaterEqual(a["p"][t], 1 / 61 - 1e-6)
            self.assertLessEqual(a["p"][t], 1.0)
            self.assertGreaterEqual(a["null_sd"][t], 0.0)
        mag = ok.null_model(synthetic(), trials=20, seed=7, strata="role_depth_magnitude")
        self.assertEqual(mag["strata"], "role_depth_magnitude")

    def test_unknown_values_stay_fixed(self):
        k = synthetic()
        by_id(k, 7)["knots"][0]["value"] = None
        res = ok.null_model(k, trials=30, seed=1)
        # two eligible groups (sizes 2 and 3) x seven known pendants, minus own-group pairs
        self.assertEqual(res["candidates"]["R3"], (7 - 2) + (7 - 3))

    def test_bad_trials_and_strata_hold(self):
        with self.assertRaises(ok.OkrHold):
            ok.null_model(synthetic(), trials=0)
        with self.assertRaises(ok.OkrHold):
            ok.null_model(synthetic(), trials=5, strata="everything")

    def test_corpus_statistics_pooled(self):
        corpus = {"khipus": [synthetic(), dict(synthetic(), id=2, okr_num="SYN0002")]}
        s1 = ok.corpus_statistics(corpus, trials=40, seed=3, strata="role_depth")
        s2 = ok.corpus_statistics(corpus, trials=40, seed=3, strata="role_depth")
        self.assertEqual(s1, s2)
        self.assertEqual(s1["observed"], {"R1": 2, "R2": 2, "R3": 2, "R4": 2})
        row = s1["by_strata"]["role_depth"]["R2"]
        self.assertTrue(1 / 41 - 1e-6 <= row["pooled_p"] <= 1.0)


class Scene(unittest.TestCase):
    def test_budget_bounds_and_arcs(self):
        s = ok.scene(synthetic())
        self.assertEqual(len(s["tubes"]), 1 + 11)
        roles = sorted({t["role"] for t in s["tubes"]})
        self.assertEqual(roles, ["pendant", "primary", "subsidiary", "top"])
        for p in [p for t in s["tubes"] for p in t["points"]] + [k["pos"] for k in s["knots"]]:
            for v in p:
                self.assertLessEqual(abs(v), 6.5)
        self.assertEqual({a["relation"] for a in s["arcs"]}, {"R1", "R2", "R3", "R4"})
        self.assertTrue(all(len(a["points"]) == 16 for a in s["arcs"]))
        self.assertTrue(all(a["points"][7][2] > a["points"][0][2] for a in s["arcs"]))
        tube5 = next(t for t in s["tubes"] if t["cord_id"] == 5)
        self.assertEqual(tube5["rgb"], [0.2, 0.3, 0.4])
        tube1 = next(t for t in s["tubes"] if t["cord_id"] == 1)
        self.assertEqual(tube1["rgb"], ok.GREY)           # no recorded colour -> grey, not invented
        self.assertEqual(len(s["bounds"]["min"]), 3)

    def test_truncation(self):
        s = ok.scene(synthetic(), max_cords=3, max_knots=2)
        self.assertEqual(s["meta"]["n_cords_drawn"], 3)
        self.assertTrue(s["meta"]["truncated_cords"])
        self.assertLessEqual(len(s["knots"]), 2)
        self.assertTrue(s["meta"]["truncated_knots"])
        with self.assertRaises(ok.OkrHold):
            ok.scene(synthetic(), max_cords=0)


class ShippedCorpus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.corpus = ok.load_corpus()

    def test_digest_matches_manifest_and_constant(self):
        digest = hashlib.sha256(CORPUS.read_bytes()).hexdigest()
        self.assertEqual(digest, self.manifest["corpus_sha256"])
        self.assertEqual(digest, ok.CORPUS_SHA256)
        raw = gzip.decompress(CORPUS.read_bytes())
        self.assertEqual(hashlib.sha256(raw).hexdigest(), self.manifest["corpus_json_sha256"])
        self.assertLess(CORPUS.stat().st_size, 3 * 1024 * 1024)
        self.assertEqual(self.manifest["source"]["db_sha256"], ok.OKR_DB_SHA256)
        self.assertEqual(self.manifest["source"]["commit"], ok.OKR_COMMIT)

    def test_counts_match_manifest(self):
        counts = self.manifest["counts"]
        self.assertEqual(len(self.corpus["khipus"]), counts["khipus"])
        self.assertEqual(sum(len(k["cords"]) for k in self.corpus["khipus"]), counts["cords"])
        self.assertEqual(sum(len(c["knots"]) for k in self.corpus["khipus"] for c in k["cords"]),
                         counts["knots"])

    def test_tampered_or_missing_corpus_holds(self):
        with self.assertRaises(ok.OkrHold):
            ok.load_corpus(CORPUS, expected_sha256="0" * 64)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ok.OkrHold):
                ok.load_corpus(Path(tmp) / "absent.json.gz")
            bad = Path(tmp) / "bad.json.gz"
            bad.write_bytes(b"not gzip")
            with self.assertRaises(ok.OkrHold):
                ok.load_corpus(bad)
            wrong = Path(tmp) / "wrong.json.gz"
            wrong.write_bytes(gzip.compress(json.dumps({"schema": "other"}).encode()))
            with self.assertRaises(ok.OkrHold):
                ok.load_corpus(wrong)
        with self.assertRaises(ok.OkrHold):
            ok.get_khipu(self.corpus, "KH9999")

    def test_known_khipu_and_listing(self):
        k = ok.get_khipu(self.corpus, "KH0217")
        self.assertEqual(k["investigator_num"], "AS199")
        rows = ok.list_khipus(self.corpus)
        self.assertEqual(len(rows), len(self.corpus["khipus"]))
        self.assertEqual({r["rank_basis"] for r in rows}, {"excess_over_null"})
        keys = [(-r["excess_over_null"], -r["n_relations"], -r["known_fraction"], r["okr_num"]) for r in rows]
        self.assertEqual(keys, sorted(keys))
        self.assertGreater(rows[0]["excess_over_null"], 0)

    def test_listing_without_report_ranks_by_count(self):
        corpus = {"khipus": [dict(synthetic(), id=2, okr_num="SYN0002", cords=[]), synthetic()]}
        rows = ok.list_khipus(corpus)
        self.assertEqual([r["okr_num"] for r in rows], ["SYN0001", "SYN0002"])
        self.assertEqual(rows[0]["n_relations"], 4)
        self.assertEqual(rows[0]["rank_basis"], "n_relations")

    def test_report_matches_engine(self):
        rep = ok.load_relations_report(corpus_sha256=ok.CORPUS_SHA256)
        self.assertEqual(rep["corpus_sha256"], ok.CORPUS_SHA256)
        self.assertEqual(rep["rules_version"], ok.RULES_VERSION)
        for k in self.corpus["khipus"]:
            entry = rep["by_id"][k["id"]]
            rels = ok.find_relations(k)
            counts = dict.fromkeys(ok.RELATION_TYPES, 0)
            for r in rels:
                counts[r["type"]] += 1
            self.assertEqual(entry["observed"], counts, k["okr_num"])
            self.assertEqual(entry["relations"],
                             [[r["type"], r["target"], r["summands"], r["target_value"]] for r in rels])
        k = ok.get_khipu(self.corpus, "KH0217")
        trials = rep["statistics"]["trials"]
        nm = ok.null_model(k, trials=trials, seed=rep["statistics"]["seed"])
        self.assertEqual(nm["p"], rep["by_id"][k["id"]]["null"]["role_depth"]["p"])
        self.assertEqual(nm["null_mean"], rep["by_id"][k["id"]]["null"]["role_depth"]["null_mean"])
        with self.assertRaises(ok.OkrHold):
            ok.load_relations_report(corpus_sha256="f" * 64)

    def test_report_headline_is_internally_consistent(self):
        rep = ok.load_relations_report()
        stats = rep["statistics"]
        for t in ok.RELATION_TYPES:
            total = sum(k["observed"][t] for k in rep["khipus"])
            self.assertEqual(stats["observed"][t], total)
            for strata in ok.NULL_STRATA:
                row = stats["by_strata"][strata][t]
                self.assertEqual(row["observed"], total)
                self.assertGreaterEqual(row["pooled_p"], stats["min_attainable_p"])

    def test_runtime_budget_on_largest_khipu(self):
        big = max(self.corpus["khipus"], key=lambda k: len(k["cords"]))
        t0 = time.perf_counter()
        ok.find_relations(big)
        s = ok.scene(big)
        dt = time.perf_counter() - t0
        self.assertLess(dt, 5.0)                          # generous: typical is well under 0.1 s
        self.assertLessEqual(s["meta"]["n_cords_drawn"], 1500)
        self.assertLessEqual(len(s["knots"]), 8000)
        card = ok.khipu_card(big, trials=20)
        self.assertEqual(card["null"]["source"], "live")
        self.assertIn("not decipherment", card["label"])


class Builder(unittest.TestCase):
    def _tiny_db(self, path: Path):
        con = sqlite3.connect(path)
        con.executescript(
            """
            CREATE TABLE ascher_color_dc (AS_COLOR_CD TEXT, COLOR_DESCR TEXT, R_DEC REAL, G_DEC REAL, B_DEC REAL);
            CREATE TABLE ascher_cord_color (color_id INTEGER, CORD_ID INTEGER, COLOR_CD_1 TEXT,
                FULL_COLOR TEXT, RANGE_BEG REAL, RANGE_END REAL, PCORD_FLAG INTEGER);
            CREATE TABLE cord_cluster (CLUSTER_ID INTEGER, GROUPING_CLASS TEXT);
            CREATE TABLE knot_cluster (CLUSTER_ID INTEGER, START_POS REAL);
            CREATE TABLE khipu_main (KHIPU_ID INTEGER, OKR_NUM TEXT, INVESTIGATOR_NUM TEXT, PROVENANCE TEXT,
                REGION TEXT, MUSEUM_NAME TEXT);
            CREATE TABLE primary_cord (KHIPU_ID INTEGER, PCORD_ID INTEGER, PCORD_LENGTH REAL);
            CREATE TABLE cord (KHIPU_ID INTEGER, CORD_ID INTEGER, PENDANT_FROM INTEGER, CORD_LEVEL INTEGER,
                ATTACHMENT_TYPE TEXT, CLUSTER_ID INTEGER, CLUSTER_ORDINAL INTEGER, CORD_ORDINAL INTEGER,
                ATTACH_POS REAL, CORD_LENGTH REAL, TERMINATION TEXT);
            CREATE TABLE knot (CORD_ID INTEGER, TYPE_CODE TEXT, knot_value_type INTEGER, CLUSTER_ID INTEGER,
                KNOT_ID INTEGER, KNOT_ORDINAL REAL, CLUSTER_ORDINAL REAL, NUM_TURNS REAL);
            INSERT INTO ascher_color_dc VALUES ('W', 'white', 0.9569, 0.9569, 0.9569);
            INSERT INTO ascher_cord_color VALUES (1, 30, 'W', 'W', 0, 20, 0);
            INSERT INTO cord_cluster VALUES (7, '');
            INSERT INTO knot_cluster VALUES (70, 4.5), (71, 12.0);
            INSERT INTO khipu_main VALUES (1, 'KH9001', 'XX001', '"Somewhere"', '', 'A
             Museum');
            INSERT INTO primary_cord VALUES (1, 20, 30.0);
            INSERT INTO cord VALUES (1, 30, 20, 1, 'R', 7, 1, 1, 0, 25.0, 'K'),
                                    (1, 31, 20, 1, 'V', 7, 2, 2, 0, 22.0, 'B');
            INSERT INTO knot VALUES (30, 'S', 10, 70, 1, 1, 1, 0), (30, 'L', 4, 71, 2, 2, 1, 4),
                                    (31, '', 0, 70, 3, 1, 1, 0), (999, 'S', 10, 70, 4, 1, 1, 0);
            """
        )
        con.commit()
        con.close()

    def test_hermetic_build_is_deterministic_and_gate_refuses(self):
        b = _builder()
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "khipu.db"
            self._tiny_db(db)
            csvp = Path(tmp) / "okr-kh-numbers.csv"
            csvp.write_text("OKR Number,Other Names,Country\nKH9001,XX001,Nowhere\n", encoding="utf-8")
            gz1, raw1, counts = b.build_corpus_bytes(db, csvp, ok)
            gz2, raw2, _ = b.build_corpus_bytes(db, csvp, ok)
            self.assertEqual(gz1, gz2)
            self.assertEqual(counts["knots_excluded_no_cord_row"], 1)
            self.assertEqual(counts["knots_unknown_value"], 1)
            doc = json.loads(raw1)
            k = doc["khipus"][0]
            self.assertEqual((k["okr"], k["prov"], k["museum"], k["country"]), ("KH9001", "Somewhere", "A Museum", "Nowhere"))
            c30 = dict(zip(ok.CORD_FIELDS, k["cords"][0]))
            self.assertEqual((c30["value"], c30["value_status"], c30["color"]), (14, "known", "W"))
            c31 = dict(zip(ok.CORD_FIELDS, k["cords"][1]))
            self.assertEqual((c31["value"], c31["value_status"]), (None, "unknown"))
            self.assertEqual(c31["knots"][0][0], "?")
            out = Path(tmp) / "c.json.gz"
            out.write_bytes(gz1)
            loaded = ok.load_corpus(out, expected_sha256=hashlib.sha256(gz1).hexdigest())
            self.assertEqual(loaded["khipus"][0]["cords"][0]["rgb"], [0.9569, 0.9569, 0.9569])
            rc = b.main(["--db", str(db), "--csv", str(csvp), "--out", str(Path(tmp) / "x.json.gz")])
            self.assertEqual(rc, 2)                       # not the pinned OKR sha256 -> refused
            self.assertFalse((Path(tmp) / "x.json.gz").exists())

    @unittest.skipUnless(_pinned_db(), "pinned OKR khipu.db not present; set SZL_OKR_DB to run the rebuild")
    def test_rebuild_from_pinned_db_equals_shipped_bytes(self):
        b = _builder()
        db = _pinned_db()
        gz, raw, counts = b.build_corpus_bytes(db, db.with_name("okr-kh-numbers.csv"), ok)
        self.assertEqual(gz, CORPUS.read_bytes())
        self.assertEqual(b.manifest_bytes(gz, raw, counts, ok), MANIFEST.read_bytes())


if __name__ == "__main__":
    unittest.main()
