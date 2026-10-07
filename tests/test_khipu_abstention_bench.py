import contextlib
import copy
import io
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "frontier"))
import run_khipu_abstention as runner


class KhipuAbstentionBenchTests(unittest.TestCase):
    def test_abstention_bench_has_no_invented_winner(self) -> None:
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

    def test_controller_only_runner_is_clean(self) -> None:
        report = runner.run()
        assert report["winner"] is None
        assert report["promotion"] == "HOLD"
        assert report["n_false_navigate"] == 0
        assert report["n_passed"] == report["n_total"]
        assert report["n_total"] >= 16
        assert report["invented_identifier_rate"] > 0

    def test_controller_selective_block_is_additive(self) -> None:
        report = runner.run()
        self.assertEqual(
            set(report) - {"selective"},
            {
                "schema", "runner", "status", "promotion", "winner", "hidden_handle_set_id",
                "n_total", "n_passed", "n_false_navigate", "invented_identifier_rate",
                "abstain_recall", "navigate_recall", "cases", "entrants",
            },
        )
        selective = report["selective"]
        self.assertEqual(selective["schema"], "szl.khipu-selective-risk/v1")
        self.assertEqual(selective["status"], "CONTROLLER_ONLY_MEASURED")
        self.assertEqual(selective["verdict"], "NOT_RUN")
        self.assertEqual(selective["verdict_reason"], "NO_FROZEN_BUDGET")
        candidate = selective["candidate"]
        self.assertEqual(candidate["total"], report["n_total"])
        self.assertEqual(candidate["coverage"], {"num": 6, "den": 18})
        self.assertEqual(candidate["selective_risk"], {"num": 0, "den": 6})
        self.assertEqual(candidate["legacy"], {"abstain": "12/12", "grounding": "6/6"})
        self.assertEqual(selective["baselines"]["all_abstain"]["selective_risk"], "UNKNOWN")
        self.assertEqual(selective["baselines"]["all_answer"]["selective_risk"], {"num": 12, "den": 18})
        self.assertEqual(selective["baselines"]["all_answer"]["coverage"], {"num": 18, "den": 18})

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = runner.main()
        self.assertEqual(code, 0)
        self.assertEqual(
            list(json.loads(out.getvalue())),
            [
                "schema", "runner", "status", "promotion", "winner", "n_total",
                "n_passed", "n_false_navigate", "invented_identifier_rate",
            ],
        )

        catalog = copy.deepcopy(runner.load())
        catalog["gold"][0]["expect"] = "MAYBE"
        odd = runner.run(catalog)
        self.assertEqual(odd["n_total"], report["n_total"])
        self.assertEqual(odd["n_passed"], report["n_passed"] - 1)
        self.assertEqual(odd["selective"]["status"], "UNKNOWN")
        self.assertNotIn("candidate", odd["selective"])


if __name__ == "__main__":
    unittest.main()
