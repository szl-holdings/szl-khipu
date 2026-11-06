"""Execute the forbidden-domain workflow's own scan script in throwaway trees.

The previous step called ripgrep, which GitHub's Ubuntu runners do not ship,
and its `|| true` turned "rg: command not found" into "OK: no forbidden domain
references" on every run (e.g. run 41549121142). These tests run the exact
`run:` block from .github/workflows/forbidden-domain.yml, so a scanner that
cannot run fails the gate instead of passing it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "forbidden-domain.yml"
STEP = "Scan for forbidden domain references"
DOMAIN = "a11oy" + ".com"  # assembled so this file is not itself a hit


def _gnu_grep_with_pcre() -> bool:
    if not shutil.which("bash") or not shutil.which("grep"):
        return False
    probe = subprocess.run(
        ["grep", "-P", "(?<!-)x", "-"], input="x\n", capture_output=True, text=True, check=False
    )
    return probe.returncode == 0


def _scan_script() -> str:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    step = next(s for s in workflow["jobs"]["scan"]["steps"] if s.get("name") == STEP)
    return step["run"]


@unittest.skipUnless(
    _gnu_grep_with_pcre(),
    "needs bash and GNU grep with -P (PCRE), as on the ubuntu-latest runner the workflow uses",
)
class ForbiddenDomainGate(unittest.TestCase):
    def run_scan(self, tree: Path, path: str | None = None) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        if path is not None:
            env["PATH"] = path
        return subprocess.run(
            [shutil.which("bash") or "bash", "-c", _scan_script()],
            cwd=tree, env=env, capture_output=True, text=True, check=False,
        )

    def test_step_has_no_masking_or_ripgrep(self) -> None:
        script = _scan_script()
        self.assertNotIn("|| true", script)
        self.assertNotIn("rg ", script)
        self.assertIn("set -euo pipefail", script)

    def test_clean_tree_and_guard_contexts_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "README.md").write_text(
                f"Product: a-11-oy.com\nNever link {DOMAIN}; it is not a surface.\n", encoding="utf-8"
            )
            result = self.run_scan(Path(tmp))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK: no forbidden domain references", result.stdout)

    def test_unguarded_reference_fails_and_is_listed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "docs").mkdir()
            (Path(tmp) / "docs" / "page.md").write_text(f"Visit https://{DOMAIN} today\n", encoding="utf-8")
            result = self.run_scan(Path(tmp))
        self.assertEqual(result.returncode, 1)
        self.assertIn("::error::Forbidden domain references found", result.stdout)
        self.assertIn(f"docs/page.md:1:Visit https://{DOMAIN} today", result.stdout)
        self.assertNotIn("OK: no forbidden domain references", result.stdout)

    def test_git_directory_is_not_scanned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".git").mkdir()
            (Path(tmp) / ".git" / "COMMIT_EDITMSG").write_text(f"mention {DOMAIN}\n", encoding="utf-8")
            self.assertEqual(self.run_scan(Path(tmp)).returncode, 0)

    def test_missing_scanner_fails_instead_of_reporting_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "page.md").write_text(f"https://{DOMAIN}\n", encoding="utf-8")
            empty = Path(tmp) / "no-tools"
            empty.mkdir()
            result = self.run_scan(Path(tmp), path=str(empty))
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("OK: no forbidden domain references", result.stdout)

    def test_tracked_repository_tree_passes(self) -> None:
        # CI scans a clean checkout: copy exactly the tracked files, as checked out.
        listed = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, text=True, check=False
        )
        if listed.returncode != 0:
            self.skipTest("not a git checkout")
        with tempfile.TemporaryDirectory() as tmp:
            for name in filter(None, listed.stdout.split("\0")):
                source = ROOT / name
                if source.is_file() and not source.is_symlink():
                    target = Path(tmp) / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
            result = self.run_scan(Path(tmp))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
