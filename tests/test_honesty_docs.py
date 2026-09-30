"""Honesty lock: cards never paint proven_trust true, joules, or a 1.5B train in this tree."""

from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    (ROOT / "README.md", "Conjecture 1"),
    (ROOT / "README.md", "energy UNAVAILABLE"),
    (ROOT / "README.md", "Not 1.5B"),
    (ROOT / "CARD.md", "proven_trust"),
    (ROOT / "CARD.md", "UNAVAILABLE"),
    (ROOT / "LICENSE", "Copyright 2026 SZL Holdings"),
    (ROOT / "CODEOWNERS", "@stephenlutar2-hash"),
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class HonestyDocs(unittest.TestCase):
    def test_no_proven_trust_true(self) -> None:
        for path in ROOT.rglob("*.md"):
            if any(p in path.parts for p in (".venv", "node_modules", "__pycache__", "atelier-space", "atelier")):
                continue
            text = _read(path)
            self.assertNotRegex(
                text,
                r"proven_trust\s*[:=]\s*true",
                msg=f"{path} paints proven_trust true",
            )

    def test_required_phrases(self) -> None:
        for path, phrase in REQUIRED:
            self.assertIn(phrase, _read(path), f"{path} missing {phrase!r}")

    def test_readme_frontmatter(self) -> None:
        text = _read(ROOT / "README.md")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("license: apache-2.0", text)
        self.assertIn("library_name: numpy", text)
        self.assertIn("governed-ai", text)
        self.assertIn("Knot the run. Hash the proof. Fail closed.", text)

    def test_space_yaml(self) -> None:
        text = _read(ROOT / "spaces" / "README.md")
        self.assertIn("title: SZL KHIPU", text)
        self.assertIn("emoji:", text)
        self.assertIn("sdk: gradio", text)
        version = re.search(r"^sdk_version: (\d+\.\d+\.\d+)$", text, re.MULTILINE)
        self.assertIsNotNone(version)
        sdk_version = version.group(1)
        self.assertGreaterEqual(tuple(map(int, sdk_version.split("."))), (6, 27, 0))
        self.assertEqual(int(sdk_version.split(".")[0]), 6)
        self.assertIn(f"gradio=={sdk_version}", _read(ROOT / "spaces" / "requirements.txt").splitlines())
        project = tomllib.loads(_read(ROOT / "pyproject.toml"))
        self.assertEqual(project["project"]["optional-dependencies"]["gradio"], ["gradio>=6.27.0,<7"])
        self.assertIn("app_file: app.py", text)

    def test_space_holographic_chrome(self) -> None:
        text = _read(ROOT / "spaces" / "app.py")
        # SZL KANCHAY founder tokens replace the legacy hologram hex (#05070d / #3af4c8 / #e8c074).
        self.assertIn("var(--bg)", text)
        self.assertIn("var(--accent)", text)
        self.assertIn("chip-conjecture", text)
        self.assertIn('SZL_DIR = ROOT / "szl_khipu" / "szl"', text)
        self.assertIn("footer { display: none", text)
        self.assertIn("Conjecture 1", text)
        self.assertIn("energy UNAVAILABLE", text)
        self.assertIn("system fonts", text.lower())
        self.assertNotIn("proven_trust=true", text)
        self.assertIn("evaluate_anatomy", text)
        self.assertIn("five-organ", text.lower())

    def test_readme_names_anatomy(self) -> None:
        text = _read(ROOT / "README.md")
        self.assertIn("evaluate_anatomy", text)
        self.assertIn("szl-holdings/anatomy", text)
        self.assertIn("Not a Three.js rehost", text)

    def test_readme_runtime_and_pricing_boundary(self) -> None:
        text = _read(ROOT / "README.md")
        self.assertNotIn("governed agent change management** in production", text)
        self.assertIn("does not itself prove or authorize a production deployment", text)
        self.assertNotIn("docs/pricing", text)
        self.assertIn("Pricing + SKUs:** not maintained in this repository", text)

    def test_pyproject(self) -> None:
        text = _read(ROOT / "pyproject.toml")
        self.assertIn('name = "szl-khipu"', text)
        self.assertIn('version = "0.1.0"', text)
        self.assertIn('requires-python = ">=3.11"', text)
        self.assertIn("numpy>=1.26", text)
        self.assertIn("gradio", text)
        self.assertIn("torch", text)
        self.assertIn("Apache-2.0", text)
        self.assertIn('szl-khipu = "szl_khipu.cli:main"', text)
        self.assertIn("Stephen P. Lutar Jr. / SZL Holdings", text)
        self.assertIn("0009-0001-0110-4173", text)
        for kw in ('"governed-ai"', '"khipu"', '"lambda-gate"', '"yarqa"', '"receipts"'):
            self.assertIn(kw, text)

    def test_kernel_card_get_kernel(self) -> None:
        import ast
        import copy

        text = _read(ROOT / "hf" / "szl-khipu-kernels" / "README.md")
        for phrase in (
            "library_name: kernels", "SOFTWARE", "advisory", "proven_trust=false",
            "Conjecture 1 OPEN", "CUDA", "UNAVAILABLE",
            "First-class kernel release qualification: UNKNOWN",
            "Artifact presence alone does not establish trained-model validity.",
            "uploads only this card", "do not establish", "package API parity",
            "not a successful loader or runtime test",
        ):
            self.assertIn(phrase, text)
        normalized = " ".join(text.split())
        self.assertIn("permits execution of the selected repository's Python", normalized)
        self.assertIn("does not verify hashes, publisher authorization or compatibility", normalized)
        self.assertIn("observations, not kernel publication approval", normalized)
        self.assertNotIn("LIVE", text)
        self.assertNotRegex(text, r"(?m)^\s*(?:GET|POST)\s+/api/")
        self.assertNotIn("Field leader", text)

        loaders = []
        for snippet in re.findall(r"```python\n(.*?)\n```", text, re.DOTALL):
            tree = ast.parse(snippet)
            calls = [node for node in ast.walk(tree)
                     if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                     and node.func.id == "get_kernel"]
            for call in calls:
                self.assertEqual(len(call.args), 1)
                self.assertIsInstance(call.args[0], ast.Constant)
                self.assertEqual(call.args[0].value, "SZLHOLDINGS/szl-khipu-kernels")
                keywords = {item.arg: item.value for item in call.keywords}
                self.assertEqual(set(keywords), {"revision", "trust_remote_code"})
                self.assertIsInstance(keywords["trust_remote_code"], ast.Constant)
                self.assertIs(keywords["trust_remote_code"].value, True)
                revision = keywords["revision"]
                self.assertIsInstance(revision, ast.Name)

                prefix = []
                for node in tree.body:
                    if isinstance(node, ast.ImportFrom) and node.module == "kernels":
                        self.assertEqual([item.name for item in node.names], ["get_kernel"])
                        break
                    if isinstance(node, ast.Import):
                        self.assertEqual([item.name for item in node.names], ["re"])
                        continue
                    self.assertIsInstance(node, (ast.Assign, ast.If))
                    prefix.append(node)
                else:
                    self.fail("Revision guard must precede the kernels import")
                assignments = [node for node in prefix if isinstance(node, ast.Assign)]
                self.assertEqual(len(assignments), 1)
                assignment = assignments[0]
                self.assertEqual(len(assignment.targets), 1)
                self.assertIsInstance(assignment.targets[0], ast.Name)
                self.assertEqual(assignment.targets[0].id, revision.id)
                self.assertIsInstance(assignment.value, ast.Constant)
                self.assertEqual(assignment.value.value, "")
                self.assertTrue(any(isinstance(node, ast.If) for node in prefix))
                # Evaluate only the pre-import guard using synthetic revisions.
                # A valid format fixture is not publisher approval or a Hub read.
                candidates = ("", "main", "v1", "a" * 39, "a" * 41, "A" * 40,
                              "a" * 39 + "g", "a" * 40 + "\n", " " + "a" * 40,
                              None, 123, "a" * 40)
                for candidate in candidates:
                    with self.subTest(revision=candidate):
                        fixture = copy.deepcopy(prefix)
                        fixture[0].value = ast.Constant(value=candidate)
                        module = ast.fix_missing_locations(ast.Module(body=fixture, type_ignores=[]))
                        namespace = {"re": re, "__builtins__": {"ValueError": ValueError}}
                        try:
                            exec(compile(module, "<kernel-card revision guard>", "exec"), namespace)
                        except (TypeError, ValueError):
                            self.assertNotEqual(candidate, "a" * 40)
                        else:
                            self.assertEqual(candidate, "a" * 40,
                                             "Invalid revision reached the provider import")
                            self.assertEqual(namespace[revision.id], candidate)
                loaders.append(call)
        self.assertEqual(len(loaders), 1, "Retain one guarded first-class kernel example")

    def test_tiny_and_agent_cards(self) -> None:
        tiny = _read(ROOT / "hf" / "TinyKhipu-Nano" / "README.md")
        agent = _read(ROOT / "hf" / "ReceiptAgent-Nano" / "README.md")
        moons = _read(ROOT / "hf" / "Moons-Nano" / "README.md")
        embed = _read(ROOT / "hf" / "MiniEmbed-Nano" / "README.md")
        self.assertTrue("NAVIGATE" in tiny and "ABSTAIN" in tiny)
        self.assertTrue("Not 1.5B" in tiny)
        self.assertTrue("4-way" in agent or "kernel is truth" in agent.lower())
        self.assertTrue("kernel is truth" in agent.lower() or "HARD_DENY" in agent)
        self.assertTrue("2→8→2" in moons or "2-8-2" in moons)
        self.assertTrue("Not 1.5B" in moons or "1.5B" in moons)
        self.assertTrue("V=64" in embed or "64 × 12" in embed or "64x12" in embed.lower())
        self.assertTrue("Not neural" in embed or "not a neural" in embed.lower())
        self.assertTrue("3290" in embed or "64 × 12" in embed)

    def test_never_claims_joules_measured(self) -> None:
        blob = "\n".join(
            _read(p)
            for p in ROOT.rglob("*.md")
            if not any(x in p.parts for x in (".venv", "node_modules", "atelier-space", "atelier"))
        )
        self.assertIsNone(re.search(r"energy_j\s*[:=]\s*[1-9]", blob))
        self.assertIn("never a fabricated joule", blob.lower())


if __name__ == "__main__":
    unittest.main()
