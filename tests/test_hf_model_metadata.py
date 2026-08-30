from __future__ import annotations

import unittest
from pathlib import Path
import yaml



ROOT = Path(__file__).resolve().parents[1]
MODEL_CARD = ROOT / "atelier" / "hf" / "SZLHOLDINGS.md"
SPACE_CARD = ROOT / "atelier-space" / "cards" / "SZLHOLDINGS.md"


def _normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _frontmatter(text: str) -> dict[str, object]:
    parts = text.split("---", 2)
    if len(parts) != 3 or parts[0].strip():
        raise AssertionError("model card must begin with YAML frontmatter")
    metadata = yaml.safe_load(parts[1])
    if not isinstance(metadata, dict):
        raise AssertionError("model card frontmatter must be a YAML mapping")
    return metadata


class ModelMetadataContractTests(unittest.TestCase):
    def test_protected_model_card_copies_remain_in_parity(self) -> None:
        self.assertEqual(_normalized(MODEL_CARD), _normalized(SPACE_CARD))

    def test_historical_stub_declares_license_without_pipeline_tag(self) -> None:
        text = _normalized(MODEL_CARD)
        metadata = _frontmatter(text)

        self.assertEqual(metadata.get("license"), "apache-2.0")
        self.assertNotIn("pipeline_tag", metadata)
        self.assertIn("Not a checkpoint.", text)
        self.assertIn("Not a model.", text)


if __name__ == "__main__":
    unittest.main()
