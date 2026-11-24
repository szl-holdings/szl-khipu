"""Validate the MOS examples and the time-field migration contract."""

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "materiality.schema.json").read_text(encoding="utf-8"))
EXAMPLES = json.loads((ROOT / "examples/mos-example.json").read_text(encoding="utf-8"))


class MaterialitySchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Draft202012Validator.check_schema(SCHEMA)
        checker = FormatChecker()
        # Fail explicitly rather than letting an unavailable optional format pass.
        if "date-time" not in checker.checkers:
            raise RuntimeError("Install jsonschema[format] to validate date-time values")
        cls.validator = Draft202012Validator(SCHEMA, format_checker=checker)

    def setUp(self):
        self.record = copy.deepcopy(EXAMPLES["records"][0])

    def test_fictional_examples_validate(self):
        self.assertIn("fictional", EXAMPLES["_notice"])
        for record in EXAMPLES["records"]:
            with self.subTest(record=record["record_id"]):
                self.validator.validate(record)

    def test_v02_requires_explicit_observation_timing(self):
        del self.record["observed_at"]
        self.assertIn("recorded_at", self.record)
        self.assertFalse(self.validator.is_valid(self.record))

    def test_v02_accepts_date_instant_or_unknown_without_recorded_at(self):
        del self.record["recorded_at"]
        for value in ("2026-02-01", "2026-02-01T09:30:00-05:00", None):
            with self.subTest(value=value):
                self.record["observed_at"] = value
                self.validator.validate(self.record)

    def test_observed_at_rejects_guesswork_and_malformed_time(self):
        for value in (
            "unknown", "", "2026", "2026-02-30", "2026-02-30T09:30:00Z",
            "2026-02-01T09:30:00", "2026-02-01T09:30:00+24:00", 0,
        ):
            with self.subTest(value=value):
                self.record["observed_at"] = value
                self.assertFalse(self.validator.is_valid(self.record))

    def test_recording_requires_an_instant_when_supplied(self):
        for value in (None, "2026-02-01", "2026-02-01T09:30:00"):
            with self.subTest(value=value):
                self.record["recorded_at"] = value
                self.assertFalse(self.validator.is_valid(self.record))

    def test_legacy_v01_records_remain_valid_without_observed_at(self):
        self.record["schema_version"] = "mos/0.1"
        del self.record["observed_at"]
        self.validator.validate(self.record)
        del self.record["recorded_at"]
        self.validator.validate(self.record)

    def test_unknown_schema_version_fails(self):
        self.record["schema_version"] = "mos/99.0"
        self.assertFalse(self.validator.is_valid(self.record))


if __name__ == "__main__":
    unittest.main()
