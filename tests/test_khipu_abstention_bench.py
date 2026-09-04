import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "frontier"))
import run_khipu_abstention as runner


def test_abstention_bench_has_no_invented_winner() -> None:
    data = json.loads((ROOT / "frontier" / "khipu_abstention_bench.json").read_text(encoding="utf-8"))
    assert data["schema"] == "szl.khipu-abstention-bench/v1"
    assert data["winner"] is None
    assert data["promotion"] == "HOLD"
    assert data["status"] == "CONTROLLER_ONLY_MEASURED"
    abstain = next(row for row in data["family"] if row["hub_id"].endswith("abstain"))
    assert abstain.get("eligible") is False
    assert abstain.get("status") == "QUARANTINED"
    assert "invented_identifier_rate" in data["required_measurements"]
    assert data["hidden_handle_set_id"] == "khipu-hidden-2026-09-04"
    ids = {row["hub_id"] for row in data["family"]}
    assert "SZLHOLDINGS/SZL-Khipu-1.5B" in ids
    assert "SZLHOLDINGS/khipu-r3" in ids
    assert len(data["gold"]) >= 16


def test_controller_only_runner_is_clean() -> None:
    report = runner.run()
    assert report["winner"] is None
    assert report["promotion"] == "HOLD"
    assert report["n_false_navigate"] == 0
    assert report["n_passed"] == report["n_total"]
    assert report["n_total"] >= 16
    assert report["invented_identifier_rate"] > 0
