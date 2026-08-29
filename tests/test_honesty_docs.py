"""Honesty lock: cards never paint proven_trust true, joules, or a 1.5B train in this tree."""

from __future__ import annotations

import re
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
            if any(p in path.parts for p in (".venv", "node_modules", "__pycache__")):
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
        self.assertIn("sdk_version: 5.29.0", text)
        self.assertIn("app_file: app.py", text)

    def test_space_holographic_chrome(self) -> None:
        text = _read(ROOT / "spaces" / "app.py")
        self.assertIn("--proof:#3af4c8", text)
        self.assertIn("--gold:#e8c074", text)
        self.assertIn("--bg:#05070d", text)
        self.assertIn("footer { display: none", text)
        self.assertIn("Conjecture 1", text)
        self.assertIn("energy UNAVAILABLE", text)
        self.assertIn("system fonts", text.lower())
        self.assertNotIn("proven_trust=true", text)

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
        text = _read(ROOT / "hf" / "szl-khipu-kernels" / "README.md")
        self.assertIn("library_name: kernels", text)
        self.assertIn("get_kernel", text)
        self.assertIn("CUDA", text)
        self.assertIn("UNAVAILABLE", text)
        self.assertIn("LIVE", text)

    def test_tiny_and_agent_cards(self) -> None:
        tiny = _read(ROOT / "hf" / "TinyKhipu-Nano" / "README.md")
        agent = _read(ROOT / "hf" / "ReceiptAgent-Nano" / "README.md")
        self.assertIn("NAVIGATE", tiny)
        self.assertIn("ABSTAIN", tiny)
        self.assertIn("Not 1.5B", tiny)
        self.assertIn("4-way", agent)
        self.assertIn("kernel is truth", agent.lower())

    def test_never_claims_joules_measured(self) -> None:
        blob = "\n".join(
            _read(p)
            for p in ROOT.rglob("*.md")
            if not any(x in p.parts for x in (".venv", "node_modules"))
        )
        self.assertIsNone(re.search(r"energy_j\s*[:=]\s*[1-9]", blob))
        self.assertIn("never a fabricated joule", blob.lower())


if __name__ == "__main__":
    unittest.main()
