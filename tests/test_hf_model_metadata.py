from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_CARD = ROOT / "atelier" / "hf" / "SZLHOLDINGS.md"
SPACE_CARD = ROOT / "atelier-space" / "cards" / "SZLHOLDINGS.md"


def _normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _frontmatter(text: str) -> str:
    parts = text.split("---", 2)
    if len(parts) != 3 or parts[0].strip():
        raise AssertionError("model card must begin with YAML frontmatter")
    return parts[1]


class ModelMetadataContractTests(unittest.TestCase):
    def test_protected_model_card_copies_remain_in_parity(self) -> None:
        self.assertEqual(_normalized(MODEL_CARD), _normalized(SPACE_CARD))

    def test_historical_stub_declares_license_without_pipeline_tag(self) -> None:
        text = _normalized(MODEL_CARD)
        metadata = _frontmatter(text)

        self.assertIn("\nlicense: apache-2.0\n", f"\n{metadata}\n")
        self.assertNotIn("\npipeline_tag:", f"\n{metadata}\n")
        self.assertIn("Not a checkpoint.", text)
        self.assertIn("Not a model.", text)


if __name__ == "__main__":
    unittest.main()
