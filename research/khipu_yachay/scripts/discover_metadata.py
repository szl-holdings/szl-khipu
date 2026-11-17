"""Operator-invoked, bounded khipu bibliography discovery; no full-text scraping.

Crawls ONLY Crossref's public bibliographic API for metadata, with a maximum
100 records per keyword. No pages, images or Indigenous materials are copied.
Never run automatically; output is append-only and source/rights marked.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

TERMS = ("khipu", "quipu", "Inka knotted cord")
ENDPOINT = "https://api.crossref.org/works"


def run(out: Path, rows: int = 20) -> dict:
    if not isinstance(rows, int) or not 1 <= rows <= 100:
        raise ValueError("MAX_ROWS")
    if out.exists():
        raise ValueError("EXISTING_OUTPUT")
    docs = {}
    for term in TERMS:
        query = urlencode({"query.bibliographic": term, "rows": rows,
                           "select": "DOI,title,author,published,URL"})
        req = Request(ENDPOINT + "?" + query,
                      headers={"User-Agent": "SZL-Khipu-Yachay-Research/0.1 (+https://github.com/szl-holdings/szl-khipu)"})
        with urlopen(req, timeout=15) as reply:
            if reply.status != 200 or reply.headers.get_content_type() != "application/json":
                raise ValueError("SOURCE_UNAVAILABLE")
            raw = reply.read(350000)
            if len(raw) >= 350000:
                raise ValueError("RESPONSE_BUDGET")
        for row in json.loads(raw)["message"]["items"]:
            doi = row.get("DOI")
            if not doi or not isinstance(doi, str) or len(doi) > 256:
                continue
            title = row.get("title", [""])
            title = title[0] if isinstance(title, list) and title else ""
            if not isinstance(title, str):
                title = ""
            link = row.get("URL", "")
            if not isinstance(link, str) or not link.startswith("https://"):
                link = "https://doi.org/" + doi
            docs[doi.lower()] = {
                "kind": "BIBLIOGRAPHIC_METADATA_ONLY", "doi": doi,
                "title": title[:300], "url": link, "discovered_with": term,
                "full_text_copied": False, "archaeological_claims_checked": False,
                "training_rights": "UNREVIEWED_DO_NOT_TRAIN",
                "source_api": ENDPOINT,
            }
    output = b"".join((json.dumps(x, sort_keys=True, ensure_ascii=False) + "\n").encode()
                      for _, x in sorted(docs.items()))
    with out.open("xb") as f:
        f.write(output)
        f.flush()
        import os
        os.fsync(f.fileno())
    return {"schema": "szl.khipu-yachay.metadata-discovery/v0",
            "retrieved_utc": datetime.now(timezone.utc).isoformat(),
            "requests": len(TERMS), "max_per_request": rows,
            "unique_dois": len(docs), "sha256": sha256(output).hexdigest(),
            "full_text_copied": False, "training_admitted": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rows", type=int, default=20)
    args = parser.parse_args()
    print(json.dumps(run(args.out, args.rows), indent=2))
