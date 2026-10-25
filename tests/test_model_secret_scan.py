"""Run the publication workflow's actual secret scan on bounded SAMPLE files."""
import os
import shutil
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "model-publish-gate.yml"


class ModelSecretScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.name == "nt":
            git = shutil.which("git")
            if git:
                base = Path(git).resolve().parents[1]
                for candidate in (base / "bin" / "bash.exe", base / "usr" / "bin" / "bash.exe"):
                    if candidate.is_file():
                        cls.shell = str(candidate)
                        break
            if not hasattr(cls, "shell"):
                raise unittest.SkipTest("Git Bash is required for the Windows shell regression")
        else:
            cls.shell = shutil.which("bash")
            if not cls.shell:
                raise unittest.SkipTest("Bash is required for the workflow shell regression")
        lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
        start = lines.index("      - name: Secret pattern scan (stdlib)")
        if lines[start + 1] != "        run: |":
            raise AssertionError("The workflow scan must have an inline shell block")
        body = []
        for line in lines[start + 2:]:
            if line.startswith("          "):
                body.append(line[10:])
            elif line.strip():
                break
        if not body:
            raise AssertionError("The workflow scan block is empty")
        cls.scan_command = "\n".join(body) + "\n"

    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)

    def run_scan(self, command=None):
        return subprocess.run(
            [self.shell, "--noprofile", "--norc", "-e", "-o", "pipefail", "-c",
             command if command is not None else self.scan_command],
            cwd=self.folder, capture_output=True, timeout=20,
        )

    def test_clean_source_and_scanner_source_pass(self):
        (self.folder / "safe.txt").write_text("Ordinary SAMPLE fixture.\n", encoding="utf-8")
        (self.folder / "workflow.yml").write_bytes(WORKFLOW.read_bytes())
        (self.folder / "regression.py").write_bytes(Path(__file__).read_bytes())
        result = self.run_scan()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"")

    def assert_sample_blocked_without_echo(self, sample):
        nested = self.folder / "source"
        nested.mkdir()
        (nested / "sample.txt").write_text(sample, encoding="utf-8")
        result = self.run_scan()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(sample.encode(), result.stdout + result.stderr)

    def test_google_key_shape_blocks_without_echo(self):
        self.assert_sample_blocked_without_echo("AI" + "za" + "A" * 35)

    def test_github_token_shape_blocks_without_echo(self):
        self.assert_sample_blocked_without_echo("gh" + "p_" + "B" * 36)

    def test_api_token_shape_blocks_without_echo(self):
        self.assert_sample_blocked_without_echo("s" + "k-" + "C" * 20)

    def test_pem_header_blocks_without_echo(self):
        self.assert_sample_blocked_without_echo("-----BEGIN " + "PRIVATE KEY-----")

    def test_scan_input_error_blocks(self):
        # A real grep input error, without relying on POSIX permission bits on Windows.
        command = self.scan_command.replace('"$pattern" .', '"$pattern" missing-selected-input')
        self.assertNotEqual(command, self.scan_command)
        result = self.run_scan(command)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"Secret scan failed", result.stdout)

    def test_existing_git_metadata_exclusion_is_preserved(self):
        metadata = self.folder / ".git"
        metadata.mkdir()
        (metadata / "sample.txt").write_text("gh" + "p_" + "D" * 36, encoding="utf-8")
        self.assertEqual(self.run_scan().returncode, 0)
