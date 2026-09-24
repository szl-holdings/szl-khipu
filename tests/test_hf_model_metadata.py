from __future__ import annotations

import unittest
from pathlib import Path
import yaml



ROOT = Path(__file__).resolve().parents[1]
MODEL_CARD = ROOT / "atelier" / "hf" / "SZLHOLDINGS.md"
SPACE_CARD = ROOT / "atelier-space" / "cards" / "SZLHOLDINGS.md"
NANO_CARDS = ("MiniEmbed-Nano", "Moons-Nano", "ReceiptAgent-Nano", "TinyKhipu-Nano")
REFERENCE_CARDS = ("chakana", "qantu", "tinku", "waman")


def _normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _frontmatter(text: str) -> dict[str, object]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise AssertionError("model card must begin with YAML frontmatter")
    try:
        closing_delimiter = lines.index("---", 1)
    except ValueError as exc:
        raise AssertionError(
            "model card frontmatter must end with an exact YAML delimiter line"
        ) from exc
    metadata = yaml.safe_load("\n".join(lines[1:closing_delimiter]))
    if not isinstance(metadata, dict):
        raise AssertionError("model card frontmatter must be a YAML mapping")
    return metadata


class ModelMetadataContractTests(unittest.TestCase):
    def test_frontmatter_requires_exact_delimiter_lines(self) -> None:
        valid = "---\nlicense: apache-2.0\n---\nNot a model.\n"
        self.assertEqual(_frontmatter(valid).get("license"), "apache-2.0")

        for malformed in ("----", "---garbage", " ---"):
            with self.subTest(closing_delimiter=malformed):
                text = f"---\nlicense: apache-2.0\n{malformed}\nNot a model.\n"
                with self.assertRaisesRegex(AssertionError, "exact YAML delimiter"):
                    _frontmatter(text)

    def test_protected_model_card_copies_remain_in_parity(self) -> None:
        self.assertEqual(_normalized(MODEL_CARD), _normalized(SPACE_CARD))

    def test_historical_stub_declares_license_without_pipeline_tag(self) -> None:
        text = _normalized(MODEL_CARD)
        metadata = _frontmatter(text)

        self.assertEqual(metadata.get("license"), "apache-2.0")
        self.assertNotIn("pipeline_tag", metadata)
        self.assertIn("Not a checkpoint.", text)
        self.assertIn("Not a model.", text)

    def test_atlas_nano_cards_preserve_canonical_publisher_scope(self) -> None:
        for name in NANO_CARDS:
            canonical = [
                line.rstrip()
                for line in _normalized(ROOT / "hf" / name / "README.md").splitlines()
            ]
            for directory in (ROOT / "atelier" / "hf", ROOT / "atelier-space" / "cards"):
                with self.subTest(name=name, directory=directory):
                    copied = [
                        line.rstrip()
                        for line in _normalized(directory / f"{name}.md").splitlines()
                    ]
                    self.assertEqual(copied, canonical)

    def test_reference_cards_preserve_matching_document_copies(self) -> None:
        for name in REFERENCE_CARDS:
            with self.subTest(name=name):
                self.assertEqual(
                    _normalized(ROOT / "atelier" / "hf" / f"{name}.md"),
                    _normalized(ROOT / "atelier-space" / "cards" / f"{name}.md"),
                )

    def test_reference_cards_distinguish_artifact_presence_from_readiness(self) -> None:
        for name in NANO_CARDS + REFERENCE_CARDS:
            with self.subTest(name=name):
                text = _normalized(ROOT / "atelier" / "hf" / f"{name}.md")
                metadata = _frontmatter(text)
                self.assertEqual(metadata.get("license"), "apache-2.0")
                self.assertIn("test-fixture", metadata.get("tags", []))
                self.assertIn("Not a production model.", text)
                self.assertIn("config.json", text)
                self.assertIn("reported synthetic", text)
                self.assertIn("## Artifact evidence", text)
                self.assertNotIn("**Weights.** none", text)
                self.assertNotIn("- No weights.", text)


if __name__ == "__main__":
    unittest.main()
