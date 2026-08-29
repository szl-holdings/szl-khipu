"""CLI tests against the live package. Honesty: never fabricate a pass."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from szl_khipu.cli import WHAT_NOT, build_parser, main
from szl_khipu.doctrine import proven_trust


class CliParser(unittest.TestCase):
    def test_subcommands(self) -> None:
        help_text = build_parser().format_help()
        for name in ("train", "demo-lambda", "demo-yarqa", "demo-anatomy", "verify"):
            self.assertIn(name, help_text)

    def test_help_exits_zero(self) -> None:
        buf = io.StringIO()
        with patch("sys.stdout", buf), self.assertRaises(SystemExit) as ctx:
            main(["--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_what_not_forbids_one_point_five_b_and_joules(self) -> None:
        blob = " ".join(WHAT_NOT).lower()
        self.assertIn("not 1.5b", blob)
        self.assertIn("no fabricated joules", blob)
        self.assertIn("proven_trust is false", blob)
        self.assertIn("conjecture 1 open", blob)

    def test_proven_trust_locked_false(self) -> None:
        self.assertIs(proven_trust, False)

    def test_demo_lambda_advisory_and_zero_route(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["demo-lambda"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertFalse(payload["proven_trust"])
        self.assertEqual(payload["energy_status"], "UNAVAILABLE")
        self.assertEqual(payload["conjecture_1"], "OPEN")
        self.assertFalse(payload["blocked"])

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["demo-lambda", "--zero", "0"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["blocked"])
        self.assertEqual(payload["value"], 0.0)

    def test_demo_yarqa_leaked(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["demo-yarqa", "--n-canals", "3"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertLessEqual(payload["leaked"], 1e-9)
        self.assertEqual(payload["cuda"], "UNAVAILABLE")
        self.assertFalse(payload["proven_trust"])

    def test_demo_anatomy_fail_closed(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["demo-anatomy"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["live_count"], 5)
        self.assertFalse(payload["blocked"])
        self.assertFalse(payload["proven_trust"])
        self.assertEqual(payload["energy_status"], "UNAVAILABLE")
        self.assertIsNone(payload["energy_j"])
        self.assertEqual(payload["conjecture_1"], "OPEN")
        self.assertEqual(payload["locked_proven"], 8)

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["demo-anatomy", "--fabricate-joule"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["blocked"])
        self.assertIsNone(payload["energy_j"])

    def test_train_and_verify_receipt(self) -> None:
        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = main(["train", "--steps", "40", "--seed", "20260721", "--out", str(out)])
            self.assertEqual(rc, 0)
            npz = out / "tiny_khipu.npz"
            rec = out / "training_receipt.json"
            self.assertTrue(npz.exists())
            data = json.loads(rec.read_text())
            self.assertFalse(data["proven_trust"])
            self.assertIsNone(data["energy_j"])
            self.assertEqual(data["honesty"], "REPORTED")
            self.assertEqual(data["conjecture_1"], "OPEN")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = main(["verify", str(rec)])
            self.assertEqual(rc, 0)
            self.assertTrue(json.loads(buf.getvalue())["ok"])


if __name__ == "__main__":
    unittest.main()
