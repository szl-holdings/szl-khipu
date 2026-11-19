"""Compare two pinned published catalogs; record disagreements without auto-merging."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
from lxml import html

SOURCES = {
    "okr": "https://github.com/khipulab/open-khipu-repository/blob/4039ca51f4de661d80d0160596309c983a62a9c7/data/okr-kh-numbers.csv",
    "field_guide_2024": "https://github.com/khipufieldguide/data-science-khipu-article/blob/a89c5dc1b8e412e3d0203719f76d5902563ab736/data/khipu_summary.csv",
    "live_index": "https://khipufieldguide.com/sketchbook/index.html",
    "live_catalog_KH0140": "https://www.khipufieldguide.com/catalog/KH0140.html",
    "live_catalog_KH0121": "https://www.khipufieldguide.com/catalog/KH0121.html",
}

def read_csv(p):
    with p.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def kh(x):
    return bool(re.fullmatch(r"KH\d{4}", x))

def live_coverage(path, okr):
    document = html.parse(str(path))
    tables = document.xpath('//table[contains(concat(" ", normalize-space(@class), " "), " sortable ")]')
    if len(tables) != 1:
        raise ValueError("Expected exactly one sortable Field Guide index table")
    aliases = defaultdict(set)
    okr_ids = {r["OKR Number"] for r in okr}
    for row in okr:
        for alias in row["Other Names"].split(","):
            if token := re.sub(r"\s+", "", alias).upper():
                aliases[token].add(row["OKR Number"])
    labels, non_kh = [], []
    for row in tables[0].xpath('./tr|./tbody/tr|./thead/tr'):
        cells = row.xpath('./td')
        if not cells:
            continue
        name_list = cells[0].xpath('.//a/text()')
        if len(name_list) != 1:
            raise ValueError("Expected a single artifact link per index row")
        label, raw_aliases = name_list[0].strip(), cells[1].text_content().strip()
        labels.append(label)
        if kh(label):
            continue
        candidate = set()
        fragment = re.fullmatch(r"(KH\d{4})[A-Z]", label)
        if fragment and fragment[1] in okr_ids:
            candidate.add(fragment[1])
        for value in [label, *raw_aliases.split(",")]:
            token = re.sub(r"\s+", "", value).upper()
            candidate.update(aliases.get(token, ()))
            if token in okr_ids:
                candidate.add(token)
        non_kh.append({"label": label, "aliases": raw_aliases, "candidate_okr_labels": sorted(candidate)})
    guide_ids = {x for x in labels if kh(x)}
    return {
        "index_sha256": sha(path),
        "display_rows": len(labels), "unique_exact_KH_labels": len(guide_ids),
        "shared_exact_KH_labels": len(guide_ids & okr_ids),
        "index_only_exact_KH_labels": sorted(guide_ids - okr_ids),
        "okr_labels_without_exact_display_label": sorted(okr_ids - guide_ids),
        "non_KH_display_rows": non_kh,
        "non_KH_display_rows_with_no_name_candidate": [r["label"] for r in non_kh if not r["candidate_okr_labels"]],
    }

def compare(okr_path, guide_path, live_index=None):
    okr, guide = read_csv(okr_path), read_csv(guide_path)
    okr_counts = Counter(r["OKR Number"] for r in okr)
    if any(not kh(k) or v != 1 for k, v in okr_counts.items()):
        raise ValueError("Expected unique KH identifiers in the pinned OKR register")
    by_key = defaultdict(list)
    for r in guide:
        by_key[r["okr_name"]].append(r)
    okr_ids = set(okr_counts)
    guide_ids = {k for k in by_key if kh(k)}
    focus = {"KH0121","KH0473","KH0140","KH0483"}
    return {
        **({"live_index": live_coverage(live_index, okr)} if live_index else {}),
        "status": "catalog identifier coverage only; no inference of artifact absence or novelty",
        "source_urls": SOURCES,
        "input_sha256": {"okr": sha(okr_path), "field_guide_2024": sha(guide_path)},
        "counts": {
            "okr_registry_rows": len(okr),
            "guide_article_rows": len(guide),
            "guide_unique_KH_labels": len(guide_ids),
            "guide_non_KH_label_rows": sum(len(v) for k,v in by_key.items() if not kh(k)),
            "shared_KH_labels": len(okr_ids & guide_ids),
            "guide_only_KH_labels": len(guide_ids-okr_ids),
            "okr_only_KH_labels": len(okr_ids-guide_ids),
        },
        "guide_repeated_KH_labels_not_auto_merged": {
            k:[r["kfg_name"] for r in v] for k,v in sorted(by_key.items()) if kh(k) and len(v)>1
        },
        "guide_only_KH_labels_not_claimed_absent_in_okr": sorted(guide_ids - okr_ids),
        "known_pairs": [
            {"ids":["KH0140","KH0483"],"decision":"documented duplicate; group for splitting; preserve source descriptions"},
            {"ids":["KH0121","KH0473"],"decision":"live Field Guide documents duplicate (index note 8); accession conflict in pinned catalogs; group conservatively for splitting; do not collapse original observations"},
        ],
        "focus_rows": {
            "okr": [{k:r[k] for k in ("OKR Number","Other Names","Collection Number","Comments")} for r in okr if r["OKR Number"] in focus],
            "field_guide_2024": [{k:r[k] for k in ("okr_name","kfg_name","museum_num")} for r in guide if r["okr_name"] in focus],
        },
    }

if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("okr", type=Path)
    p.add_argument("guide", type=Path)
    p.add_argument("--live-index", type=Path)
    a=p.parse_args()
    print(json.dumps(compare(a.okr, a.guide, a.live_index), indent=2, sort_keys=True))
