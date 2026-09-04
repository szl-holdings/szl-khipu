import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_abstention_bench_has_no_invented_winner() -> None:
    data = json.loads((ROOT / "frontier" / "khipu_abstention_bench.json").read_text(encoding="utf-8"))
    assert data["schema"] == "szl.khipu-abstention-bench/v1"
    assert data["winner"] is None
    assert data["promotion"] == "HOLD"
    assert data["status"] == "NOT_RUN"
    abstain = next(row for row in data["family"] if row["hub_id"].endswith("abstain"))
    assert abstain.get("eligible") is False
    assert "invented_identifier_rate" in data["required_measurements"]
    ids = {row["hub_id"] for row in data["family"]}
    assert "SZLHOLDINGS/SZL-Khipu-1.5B" in ids
    assert "SZLHOLDINGS/khipu-r3" in ids
