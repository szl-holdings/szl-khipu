"""The hash-locked CI install sets must match what the packages declare.

CI installs every dependency from requirements/ci/*.txt with --require-hashes
(OpenSSF Scorecard Pinned-Dependencies), then the package itself with
--no-deps. These tests fail when a lock drifts from pyproject.toml, from the
Gradio demo's own pins, or from the workflows that consume it, and name the
command that regenerates it.
"""

from __future__ import annotations

import importlib.util
import re
import tomllib
import unittest
from pathlib import Path

import yaml
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / "requirements" / "ci"
WORKFLOWS = ROOT / ".github" / "workflows"


def _project(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))["project"]


def _declared(path: Path, *extras: str) -> set[str]:
    project = _project(path)
    rows = list(project.get("dependencies", []))
    for extra in extras:
        rows += project["optional-dependencies"][extra]
    return {str(Requirement(row)) for row in rows}


def _input(name: str) -> tuple[set[str], list[str]]:
    """Requirement strings and `-r` includes of requirements/ci/<name>.in."""
    reqs, includes = set(), []
    for line in (CI / f"{name}.in").read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("-r "):
            includes.append(line[3:].strip())
        else:
            reqs.add(str(Requirement(line)))
    return reqs, includes


def _lock(name: str) -> dict[str, list[tuple[Requirement, int]]]:
    """Pinned requirements (possibly several per name, split by marker) with their hash counts."""
    text = (CI / f"{name}.txt").read_text(encoding="utf-8")
    pins: dict[str, list[tuple[Requirement, int]]] = {}
    current = None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[0].isspace():
            current = Requirement(line.rstrip("\\").strip())
            pins.setdefault(canonicalize_name(current.name), []).append((current, 0))
        elif line.strip().startswith("--hash=sha256:") and current is not None:
            req, count = pins[canonicalize_name(current.name)][-1]
            pins[canonicalize_name(current.name)][-1] = (req, count + 1)
    return pins


def _pinned_version(req: Requirement) -> str:
    (spec,) = req.specifier
    if spec.operator != "==":
        raise AssertionError(f"{req} is not an exact pin")
    return spec.version


def _regen(name: str) -> str:
    return (
        f"uv pip compile requirements/ci/{name}.in --universal --python-version 3.11 "
        f"--generate-hashes -o requirements/ci/{name}.txt"
    )


LOCKS = {
    # lock name: (inputs it must mirror, workflow, job, working directory or None)
    "test": (_declared(ROOT / "pyproject.toml", "test"), "ci.yml", "test", None),
    "gradio-demo": (_declared(ROOT / "pyproject.toml", "test", "gradio"), "ci.yml", "gradio-demo", None),
    "hub": (_declared(ROOT / "pyproject.toml", "hub"), "publish-hf.yml", "hub", None),
    "khipu-x1": (
        _declared(ROOT / "hardware" / "khipu-x1" / "pyproject.toml", "dev"),
        "khipu-x1-reference.yml",
        "conformance",
        "hardware/khipu-x1",
    ),
}


class CiRequirementLocks(unittest.TestCase):
    def test_inputs_mirror_the_declared_dependencies(self) -> None:
        for name, (declared, *_rest) in LOCKS.items():
            with self.subTest(lock=name):
                reqs, includes = _input(name)
                self.assertEqual(reqs, declared, f"edit requirements/ci/{name}.in, then: {_regen(name)}")
                self.assertEqual(includes, ["../../spaces/requirements.txt"] if name == "gradio-demo" else [])

    def test_every_pin_is_exact_hashed_and_satisfies_its_input(self) -> None:
        for name in LOCKS:
            reqs, _ = _input(name)
            pins = _lock(name)
            with self.subTest(lock=name):
                header = (CI / f"{name}.txt").read_text(encoding="utf-8").splitlines()[:2]
                self.assertIn(f"uv pip compile requirements/ci/{name}.in", header[1])
                self.assertIn("--generate-hashes", header[1])
            for rows in pins.values():
                for req, hashes in rows:
                    with self.subTest(lock=name, pin=str(req)):
                        _pinned_version(req)
                        self.assertGreater(hashes, 0)
            for row in reqs:
                wanted = Requirement(row)
                with self.subTest(lock=name, input=row):
                    rows = pins.get(canonicalize_name(wanted.name))
                    self.assertTrue(rows, f"{wanted.name} missing from the lock; regenerate: {_regen(name)}")
                    for req, _hashes in rows:
                        self.assertIn(_pinned_version(req), wanted.specifier, _regen(name))

    def test_gradio_lock_matches_the_demo_pins(self) -> None:
        # Dependabot bumps spaces/requirements.txt; CI must then test that exact
        # Gradio, not an older locked one.
        pins = _lock("gradio-demo")
        for line in (ROOT / "spaces" / "requirements.txt").read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            wanted = Requirement(line)
            with self.subTest(pin=line):
                rows = pins.get(canonicalize_name(wanted.name))
                self.assertTrue(rows, _regen("gradio-demo"))
                for req, _hashes in rows:
                    self.assertIn(_pinned_version(req), wanted.specifier, _regen("gradio-demo"))

    def test_workflows_install_the_locks_with_hashes(self) -> None:
        for name, (_declared_set, workflow, job, workdir) in LOCKS.items():
            with self.subTest(lock=name, workflow=workflow):
                data = yaml.safe_load((WORKFLOWS / workflow).read_text(encoding="utf-8"))
                runs = "\n".join(
                    step.get("run", "") for step in data["jobs"][job]["steps"] if isinstance(step, dict)
                )
                lock = f"requirements/ci/{name}.txt"
                if workdir:
                    lock = "../" * len(Path(workdir).parts) + lock
                self.assertRegex(runs, rf"python -m pip install --require-hashes -r {re.escape(lock)}\b")
                self.assertIn("python -m pip install --no-deps -e .", runs)
                for line in runs.splitlines():
                    if re.search(r"\bpip install\b", line):
                        self.assertTrue(
                            "--require-hashes" in line or "--no-deps -e ." in line,
                            f"unhashed install in {workflow}:{job}: {line.strip()}",
                        )

    def test_dependabot_keeps_the_locks_current(self) -> None:
        updates = yaml.safe_load((ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8"))["updates"]
        self.assertIn(
            "/requirements/ci",
            [u.get("directory") for u in updates if u.get("package-ecosystem") == "pip"],
        )

    def test_gradio_lock_pins_patched_pillow(self) -> None:
        # GHSA-8g5g-8vmr-9782 (and every other Pillow advisory still covering
        # 12.3.0) is fixed in 13.0.0. Gradio 6.31.0's pillow<13 bound hides that
        # release from a normal resolve, so the lock carries an override.
        pins = _lock("gradio-demo")
        versions = {_pinned_version(req) for req, _hashes in pins["pillow"]}
        self.assertEqual(versions, {"13.0.0"})
        header = (CI / "gradio-demo.txt").read_text(encoding="utf-8").splitlines()[1]
        self.assertIn("--overrides requirements/ci/pillow-security-override.txt", header)
        override = (CI / "pillow-security-override.txt").read_text(encoding="utf-8")
        self.assertIn("pillow==13.0.0", override)
        self.assertIn("GHSA-8g5g-8vmr-9782", override)

    def test_gradio_job_installs_the_pillow_override_without_resolving(self) -> None:
        data = yaml.safe_load((WORKFLOWS / "ci.yml").read_text(encoding="utf-8"))
        runs = "\n".join(
            step.get("run", "") for step in data["jobs"]["gradio-demo"]["steps"] if isinstance(step, dict)
        )
        self.assertIn(
            "python -m pip install --require-hashes -r requirements/ci/gradio-demo.txt --no-deps",
            runs,
        )
        self.assertIn("python scripts/check_gradio_demo_deps.py", runs)
        spec = importlib.util.spec_from_file_location(
            "check_gradio_demo_deps", ROOT / "scripts" / "check_gradio_demo_deps.py"
        )
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        allowed = checker.ALLOWED
        self.assertEqual(checker.unexpected(allowed + "\n", 1), [])
        self.assertEqual(checker.unexpected("", 0), [])
        self.assertTrue(checker.unexpected(allowed + "\nnumpy 1.0 has requirement x, but you have y.\n", 1))
        self.assertTrue(checker.unexpected("", 1))
        self.assertTrue(checker.unexpected("something else\n", 0))


if __name__ == "__main__":
    unittest.main()
