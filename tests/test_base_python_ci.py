"""Exercise the actual generic CI install step without downloading dependencies."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class BasePythonInstallTests(unittest.TestCase):
    def run_install(self, manifest: str, *, pip_exit: int = 0, deferred: bool = False):
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/base-python-ci.yml").read_text()
        )
        step = next(
            row for row in workflow["jobs"]["test"]["steps"]
            if row.get("name") == "Install the package"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pyproject.toml").write_text(manifest)
            if deferred:
                (root / ".github").mkdir()
                (root / ".github/base-python-ci.defer").write_text("stale skip marker")
            shim = root / "python"
            shim.write_text(
                f"#!{sys.executable}\n"
                "import json, os, sys\n"
                "from pathlib import Path\n"
                "if sys.argv[1:4] == ['-m', 'pip', 'install']:\n"
                "    with open('pip-arguments.jsonl', 'a') as stream:\n"
                "        stream.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                "    sys.exit(int(os.environ['TEST_PIP_EXIT']))\n"
                f"os.execv({sys.executable!r}, [{sys.executable!r}, *sys.argv[1:]])\n"
            )
            shim.chmod(0o755)
            result = subprocess.run(
                ["bash", "-c", step["run"]], cwd=root,
                env={**os.environ, "PATH": f"{root}{os.pathsep}{os.environ['PATH']}",
                     "TEST_PIP_EXIT": str(pip_exit)},
                capture_output=True, text=True,
            )
            log = root / "pip-arguments.jsonl"
            calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
            return result, calls

    def test_installs_only_declared_test_extras(self):
        for names in (("dev",), ("test",), ("tests",), ("dev", "test", "tests")):
            with self.subTest(names=names):
                manifest = "[project.optional-dependencies]\n" + "\n".join(
                    f'"{name}" = ["example-{name}"]' for name in names
                )
                result, calls = self.run_install(manifest)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(calls, [["-m", "pip", "install", "-e", f'.[{",".join(names)}]']])

    def test_stale_deferral_marker_cannot_skip_dependency_install(self):
        result, calls = self.run_install(
            '[project.optional-dependencies]\ntest = []\n', deferred=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [["-m", "pip", "install", "-e", ".[test]"]])

    def test_unrelated_toml_keys_are_not_package_extras(self):
        result, calls = self.run_install('[tool.example]\ndev = ["not-an-extra"]\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [["-m", "pip", "install", "-e", "."]])

    def test_malformed_toml_stops_before_install(self):
        result, calls = self.run_install('[project.optional-dependencies]\ntest = [\n')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])

    def test_install_failure_stops_the_step(self):
        result, calls = self.run_install('[project.optional-dependencies]\ntest = []\n', pip_exit=17)
        self.assertEqual(result.returncode, 17)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
