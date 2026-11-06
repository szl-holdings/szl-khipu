"""CLI tests against the live package. Honesty: never fabricate a pass."""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import unittest
from contextlib import chdir, redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from szl_khipu.cli import DEFAULT_RUN_DIR, WHAT_NOT, build_parser, main
from szl_khipu.doctrine import proven_trust

ROOT = Path(__file__).resolve().parents[1]


def _run(argv: list[str]) -> tuple[int, dict, dict]:
    """Run the CLI; return (rc, stdout JSON or {}, stderr JSON or {})."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = main(argv)
    return rc, (json.loads(out.getvalue()) if out.getvalue() else {}), (
        json.loads(err.getvalue()) if err.getvalue() else {}
    )


class CliParser(unittest.TestCase):
    def test_subcommands(self) -> None:
        help_text = build_parser().format_help()
        for name in ("train", "demo-lambda", "demo-yarqa", "demo-anatomy", "demo-tiledigest", "verify", "serve"):
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


class VerifyFailsClosed(unittest.TestCase):
    """`verify` must recompute every declared digest over bytes that exist."""

    def test_documented_relative_run_dir_detects_tamper_and_deletion(self) -> None:
        # The README flow: a cwd-relative --out, then verify by relative path.
        # Before the fix the receipt recorded "runs/x/tiny_khipu.npz", verify looked
        # for runs/x/runs/x/tiny_khipu.npz, skipped the missing file and said ok.
        with TemporaryDirectory() as tmp, chdir(tmp):
            rc, _out, _err = _run(["train", "--steps", "40", "--out", "runs/x"])
            self.assertEqual(rc, 0)
            receipt = Path("runs/x/training_receipt.json")
            self.assertEqual(json.loads(receipt.read_text())["weights"], "tiny_khipu.npz")
            rc, out, _err = _run(["verify", str(receipt)])
            self.assertEqual(rc, 0)
            self.assertTrue(out["ok"])
            self.assertEqual([Path(v["file"]).name for v in out["verified"]], ["tiny_khipu.npz"])

            npz = Path("runs/x/tiny_khipu.npz")
            npz.write_bytes(npz.read_bytes() + b"X")
            rc, out, err = _run(["verify", str(receipt)])
            self.assertEqual((rc, out), (1, {}))
            self.assertFalse(err["ok"])
            self.assertIn("sha256 mismatch", err["reason"])

            npz.unlink()
            rc, out, err = _run(["verify", str(receipt)])
            self.assertEqual((rc, out), (1, {}))
            self.assertIn("declared file is missing", err["reason"])

    def test_receipt_verifies_after_the_run_directory_moves(self) -> None:
        with TemporaryDirectory() as tmp, chdir(tmp):
            self.assertEqual(_run(["train", "--steps", "40", "--out", "a"])[0], 0)
            shutil.move("a", "b")
            rc, out, _err = _run(["verify", "b/training_receipt.json"])
            self.assertEqual(rc, 0)
            self.assertTrue(out["ok"])

    def test_legacy_cwd_relative_weights_path_is_still_digest_checked(self) -> None:
        # Earlier `train --out artifacts` wrote weights="artifacts/tiny_khipu.npz".
        with TemporaryDirectory() as tmp:
            run = Path(tmp) / "artifacts"
            run.mkdir()
            blob = run / "tiny_khipu.npz"
            blob.write_bytes(b"legacy weights")
            receipt = run / "training_receipt.json"
            receipt.write_text(json.dumps({
                "weights": "artifacts/tiny_khipu.npz",
                "sha256": hashlib.sha256(b"legacy weights").hexdigest(),
                "proven_trust": False, "energy_j": None,
            }))
            rc, out, _err = _run(["verify", str(receipt)])
            self.assertEqual(rc, 0)
            self.assertEqual(Path(out["verified"][0]["file"]), blob)
            blob.write_bytes(b"swapped weights")
            self.assertEqual(_run(["verify", str(receipt)])[0], 1)

    def test_committed_export_receipt_verifies_all_four_archives(self) -> None:
        rc, out, _err = _run(["verify", str(ROOT / "artifacts" / "TRAINING_RECEIPT.json")])
        self.assertEqual(rc, 0)
        self.assertEqual(
            sorted(Path(v["file"]).name for v in out["verified"]),
            ["mini_embed.npz", "moons.npz", "receipt_agent.npz", "tiny_khipu.npz"],
        )

    def test_artifact_entries_fail_closed(self) -> None:
        good = hashlib.sha256(b"bytes").hexdigest()
        cases = {
            "missing file": ({"artifacts": {"gone.npz": {"sha256": good}}}, "declared file is missing"),
            "malformed digest": ({"artifacts": {"a.npz": {"sha256": "abc"}}}, "malformed sha256"),
            "empty digest": ({"artifacts": {"a.npz": {"sha256": ""}}}, "malformed sha256"),
            "escaping name": ({"artifacts": {"../a.npz": {"sha256": good}}}, "escapes the receipt directory"),
            "nothing to verify": ({"honesty": "REPORTED"}, "no artifact digest"),
            "digest without weights": ({"sha256": good}, "without a weights path"),
            "artifacts not an object": ({"artifacts": ["a.npz"]}, "must be an object"),
            "fabricated joule": ({"energy_j": 1.0, "artifacts": {"a.npz": {"sha256": good}}}, "fabricated joule"),
            "proven trust": ({"proven_trust": True}, "proven_trust true is forbidden"),
        }
        for label, (payload, reason) in cases.items():
            with self.subTest(label), TemporaryDirectory() as tmp:
                (Path(tmp) / "a.npz").write_bytes(b"bytes")
                receipt = Path(tmp) / "r.json"
                receipt.write_text(json.dumps(payload))
                rc, out, err = _run(["verify", str(receipt)])
                self.assertEqual((rc, out), (1, {}))
                self.assertFalse(err["ok"])
                self.assertIn(reason, err["reason"])

    def test_unreadable_receipt_fails_closed(self) -> None:
        with TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "r.json"
            receipt.write_text("{not json")
            rc, _out, err = _run(["verify", str(receipt)])
            self.assertEqual(rc, 1)
            self.assertIn("unreadable receipt", err["reason"])

    def test_default_run_dir_never_targets_committed_artifacts(self) -> None:
        args = build_parser().parse_args(["train"])
        self.assertEqual(Path(args.out), DEFAULT_RUN_DIR)
        self.assertFalse(DEFAULT_RUN_DIR.is_absolute())
        self.assertNotIn("artifacts", DEFAULT_RUN_DIR.parts)
        self.assertEqual(Path(build_parser().parse_args(["verify"]).receipt).parent, DEFAULT_RUN_DIR)


if __name__ == "__main__":
    unittest.main()
