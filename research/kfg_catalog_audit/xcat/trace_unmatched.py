"""Trace eight unmatched cross-catalog positives to pinned KFG SQL and CSV.
Run alongside compare.py's read-only inputs and result.json.
Usage: python trace_unmatched.py > unmatched_trace.json
"""
import csv
import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HASHES = {
    "KFG_DB.SQL": "a0171bf18a3c6652a818b079050d72a6e0ecb535ec0923a680979072d491221b",
    "corpus.json.gz": "6ef204b641826b37c320509952ed4181e93865af20f1cdfefd7516a49cf8ad0d",
    "sum_top_cords_relation.csv": "e51a52330663f529285b71c4e55a5563571f5b4469749a91dd2ea1eec8173832",
}
SQL_ATOM = r"(?:'(?:[^'\\]|\\.|'')*'|[^,()]+)"
SQL_ROW = re.compile(r"\((" + SQL_ATOM + r"(?:," + SQL_ATOM + r")*)\)")
SQL_FIELD = re.compile(SQL_ATOM)
TABLE_WIDTH = {"cord": 22, "cord_cluster": 16, "knot": 13}

def need(condition, description):
    if not condition:
        raise ValueError(description)

def sql_rows(body, width):
    previous = 0
    for match in SQL_ROW.finditer(body):
        need(body[previous:match.start()] in ("", ","), "non-row text in SQL INSERT")
        previous = match.end()
        cells = SQL_FIELD.findall(match.group(1))
        need(len(cells) == width, "unexpected SQL table width")
        yield cells
    need(previous == len(body), "incomplete SQL INSERT")

def trace():
    for name, digest in HASHES.items():
        need(hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, f"unexpected hash: {name}")
    source_result = Path("result.json").read_bytes()
    unmatched = json.loads(source_result)["rows_okr_only"]
    need(len(unmatched) == 8, "expected eight cross-catalog positives")
    object_ids = {r["object_id"] for r in unmatched}
    with gzip.open("corpus.json.gz", "rt", encoding="utf-8") as f:
        corpus = json.load(f)
    idx = {key: i for i, key in enumerate(corpus["cord_fields"])}
    okr_cords = {r["id"]: {q[0]: q for q in r["cords"]} for r in corpus["khipus"] if r["id"] in object_ids}
    with open("sum_top_cords_relation.csv", newline="", encoding="utf-8") as f:
        export = defaultdict(list)
        for csv_row in csv.DictReader(f):
            export[int(csv_row["khipu_id"]), int(csv_row["cluster_id"])].append(csv_row)

    clusters = {}
    same_primary = defaultdict(list)
    members = defaultdict(list)
    sql_cords = {}
    knot_values = defaultdict(list)
    tracked_cords = set()
    with open("KFG_DB.SQL", encoding="utf-8") as f:
        for line in f:
            match = re.match(r"INSERT INTO `(cord|cord_cluster|knot)` VALUES ", line)
            if not match:
                continue
            table = match.group(1)
            for row in sql_rows(line[match.end():].rstrip("\r\n;"), TABLE_WIDTH[table]):
                if table in ("cord", "cord_cluster"):
                    obj = int(row[1])
                    if obj not in object_ids:
                        continue
                    if table == "cord" and row[10] != "NULL":
                        cord, group = map(int, (row[2], row[10]))
                        tracked_cords.add(cord)
                        sql_cords[obj, cord] = row
                        members[obj, group].append(cord)
                    elif table == "cord_cluster" and int(row[8]) in (1, -1):
                        primary, group, ordinal = map(int, (row[2], row[3], row[4]))
                        clusters[obj, group] = primary
                        same_primary[obj, primary].append((ordinal, group))
                elif int(row[1]) in tracked_cords:
                    knot_values[int(row[1])].append(None if row[5] == "NULL" else int(row[5]))

    def value(cord):
        raw = knot_values[cord]
        return None if None in raw else sum(raw)

    detailed = []
    for record in unmatched:
        obj, top, summands, target_value = (
            record["object_id"], record["top_cord_id"], record["summand_ids"], record["value"]
        )
        ids = [top, *summands]
        cords = okr_cords[obj]
        top_cluster = cords[top][idx["cluster"]]
        summand_clusters = {cords[i][idx["cluster"]] for i in summands}
        need(len(summand_clusters) == 1, "SZL trace expects one cluster per row")
        summand_cluster = summand_clusters.pop()
        need(all((obj, i) in sql_cords for i in ids), "cord absent from pinned KFG SQL")
        need(members[obj, top_cluster] == [top], "SQL target cluster does not have exactly its matched cord")
        need(sorted(members[obj, summand_cluster]) == summands, "SQL summand cluster cord set differs")
        values = [value(i) for i in ids]
        need(values == [cords[i][idx["value"]] for i in ids], "SQL knot decimal sums differ from OKR values")
        need(values[0] == sum(values[1:]) == target_value, "SQL values do not reproduce equality")
        primary = clusters[obj, top_cluster]
        sequence = [cluster for _, cluster in sorted(same_primary[obj, primary])]
        actual_top = sequence.index(top_cluster)
        actual_summand = sequence.index(summand_cluster)
        hits = export[obj, top_cluster]
        need(len(hits) <= 1, "ambiguous CSV target rows")
        export_evidence = None
        if not hits:
            category = "target_cluster_absent_from_relation_export"
        else:
            row = hits[0]
            tp, sp, tv, sv = map(int, (row["cluster_position"], row["summand_cluster_position"], row["top_cord_value"], row["summand_value"]))
            target_at_pos, summand_at_pos = sequence[tp], sequence[sp]
            candidate_ids = sorted(members[obj, summand_at_pos])
            candidate_values = [value(i) for i in candidate_ids]
            flag = row["is_exact_sum"] == "True"
            pos_match = target_at_pos == top_cluster
            group_match = candidate_ids == summands
            if flag != (tv == sv):
                category = "flag_arithmetic_inconsistency_same_group" if pos_match and group_match else "flag_arithmetic_inconsistency_different_group"
            elif tv == sv:
                category = "exact_export_position_anchor_mismatch" if not pos_match else "exact_export_different_equal_group"
                if pos_match:
                    need(not group_match and sum(candidate_values) == target_value, "expected other equal-value group")
            else:
                category = "near_match_different_group" if pos_match else "near_match_position_anchor_mismatch"
            export_evidence = dict(row_number=int(row[""]), target_position=tp, summand_position=sp,
                target_value=tv, summand_value=sv, exact_flag=flag, declared_summand_count=int(row["num_summand_cords"]),
                sql_cluster_at_declared_target_position=target_at_pos,
                sql_cluster_at_declared_summand_position=summand_at_pos,
                sql_summand_position_cord_ids=candidate_ids,
                sql_summand_position_cord_values=candidate_values,
                target_position_anchored=pos_match, same_summand_ids_at_csv_positions=pos_match and group_match)
        interposed = []
        for group in sequence[min(actual_top, actual_summand)+1:max(actual_top, actual_summand)]:
            for cord in members[obj, group]:
                interposed.append(dict(cluster_id=group, cord_id=cord,
                    okr_level=cords[cord][idx["level"]] if cord in cords else None,
                    okr_group_class=cords[cord][idx["group_class"]] if cord in cords else None))
        detailed.append({**record, "category": category, "pinned_kfg_sql": dict(
            target_cluster=top_cluster, summand_cluster=summand_cluster,
            target_position=actual_top, summand_position=actual_summand,
            same_complete_cord_ids=True, target_value=values[0], summand_values=values[1:],
            knotless_sql_cord_ids=[i for i in ids if not knot_values[i]], between_clusters=interposed),
            "pinned_kfg_relation_export": export_evidence})
    return dict(source_result_sha256=hashlib.sha256(source_result).hexdigest(),
        input_hashes=HASHES, unmatched_rows=len(unmatched),
        shared_sql_full_group_and_exact_value_rows=len(detailed),
        category_counts=dict(sorted(Counter(r["category"] for r in detailed).items())),
        interpretation="SQL arithmetic on preselected SZL candidates, not a KFG algorithm rerun or independent validation. The published relation CSV is not a negative-label or eligible-candidate census.",
        rows=detailed)

if __name__ == "__main__":
    print(json.dumps(trace(), indent=2))
