#!/usr/bin/env python3
"""Controller-only Khipu abstention runner.

Weights stay UNAVAILABLE. Winner stays null. Promotion stays HOLD.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BENCH = ROOT / "khipu_abstention_bench.json"
INVENTED = re.compile(
    r"receipt-7f3a|handle\.ghost|made-up waypoint|invented identifier",
    re.I,
)


def load() -> dict:
    return json.loads(BENCH.read_text(encoding="utf-8"))


def decide(row: dict, hidden: set[str]) -> str:
    prompt = row["prompt"]
    if INVENTED.search(prompt) or row.get("invented"):
        return "ABSTAIN"
    cited = [handle for handle in hidden if handle in prompt]
    if cited:
        return "NAVIGATE"
    return "ABSTAIN"


def run(catalog: dict | None = None) -> dict:
    catalog = catalog or load()
    hidden = set(catalog["hidden_handle_set"])
    cases = []
    invented = 0
    abstain_ok = 0
    navigate_ok = 0
    for row in catalog["gold"]:
        got = decide(row, hidden)
        expect = row["expect"]
        inv = bool(row.get("invented") or INVENTED.search(row["prompt"]))
        if inv:
            invented += 1
        ok = got == expect
        if ok and expect == "ABSTAIN":
            abstain_ok += 1
        if ok and expect == "NAVIGATE":
            navigate_ok += 1
        cases.append(
            {
                "id": row["id"],
                "expect": expect,
                "got": got,
                "pass": ok,
                "invented": inv,
            }
        )
    n = len(cases)
    passed = sum(1 for c in cases if c["pass"])
    n_abs = sum(1 for c in cases if c["expect"] == "ABSTAIN")
    n_nav = sum(1 for c in cases if c["expect"] == "NAVIGATE")
    return {
        "schema": catalog["schema"],
        "runner": "controller-only",
        "status": "CONTROLLER_ONLY_MEASURED",
        "promotion": "HOLD",
        "winner": None,
        "hidden_handle_set_id": catalog["hidden_handle_set_id"],
        "n_total": n,
        "n_passed": passed,
        "n_false_navigate": sum(
            1 for c in cases if c["expect"] == "ABSTAIN" and c["got"] == "NAVIGATE"
        ),
        "invented_identifier_rate": (invented / n) if n else 0.0,
        "abstain_recall": (abstain_ok / n_abs) if n_abs else None,
        "navigate_recall": (navigate_ok / n_nav) if n_nav else None,
        "cases": cases,
        "entrants": catalog["family"],
    }


def main() -> int:
    report = run()
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "schema",
                    "runner",
                    "status",
                    "promotion",
                    "winner",
                    "n_total",
                    "n_passed",
                    "n_false_navigate",
                    "invented_identifier_rate",
                )
            },
            indent=2,
        )
    )
    if report["winner"] is not None:
        return 1
    if report["n_false_navigate"] != 0:
        return 1
    if report["n_passed"] != report["n_total"]:
        print("FAILED", [c["id"] for c in report["cases"] if not c["pass"]])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
