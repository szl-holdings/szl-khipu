"""Mandatory real-SDK smoke for the dedicated Gradio CI lane, not core-only installs."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

import gradio
from gradio_client import Client
import httpx


ROOT = Path(__file__).resolve().parents[1]


class GradioRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cache = tempfile.TemporaryDirectory(prefix="khipu-gradio-smoke-")
        cls.addClassCleanup(cls.cache.cleanup)
        settings = patch.dict(
            os.environ,
            {"GRADIO_ANALYTICS_ENABLED": "False", "HF_HUB_OFFLINE": "1", "GRADIO_TEMP_DIR": cls.cache.name},
        )
        settings.start()
        cls.addClassCleanup(settings.stop)
        spec = importlib.util.spec_from_file_location("khipu_gradio_demo", ROOT / "spaces" / "app.py")
        cls.app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.app)
        cls.addClassCleanup(cls.app.demo.close)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        _app, cls.url, share_url = cls.app.launch_demo(
            server_name="127.0.0.1", server_port=port, prevent_thread_lock=True
        )
        if share_url is not None:
            raise AssertionError("The smoke test must never create a public sharing tunnel")
        cls.client = Client(cls.url, verbose=False, analytics_enabled=False, httpx_kwargs={"timeout": 15.0})
        cls.addClassCleanup(cls.client.close)

    def test_pinned_runtime_and_styling_config(self) -> None:
        self.assertEqual(gradio.__version__, "6.27.0")
        self.assertFalse(self.client.analytics_enabled)
        response = httpx.get(f"{self.url}config", timeout=15.0)
        response.raise_for_status()
        config = response.json()
        self.assertEqual(config["version"], gradio.__version__)
        self.assertEqual(config["title"], "SZL KHIPU")
        self.assertEqual(config["css"], self.app.HOLO_CSS)
        self.assertEqual(config["js"], self.app.HOLO_JS)
        self.assertEqual(config["head"], self.app.HOLO_HEAD)
        self.assertFalse(config["analytics_enabled"])
        self.assertTrue(config["enable_queue"])
        self.assertIs(self.app.demo.theme, self.app.THEME)
        self.assertFalse(self.app.demo.ssr_mode)
        labels = [item["props"].get("label") for item in config["components"] if item["type"] == "tabitem"]
        self.assertEqual(labels, ["Λ gate", "YARQA", "TileDigest", "TinyKhipu", "Moons", "MiniEmbed", "Anatomy", "Receipts"])

    def test_live_lambda_pass_and_fail_closed(self) -> None:
        passing = self.client.predict(*([1.0] * len(self.app.AXES)), api_name="/score_lambda")
        self.assertIn("advisory pass", passing)
        self.assertIn("Conjecture 1 OPEN", passing)
        blocked = self.client.predict(*([0.0] + [1.0] * (len(self.app.AXES) - 1)), api_name="/score_lambda")
        self.assertIn("BLOCKED", blocked)
        for result in (passing, blocked):
            self.assertIn("energy UNAVAILABLE", result)
            self.assertIn("proven_trust=false", result)

    def test_live_yarqa_and_tampered_tile_digest(self) -> None:
        yarqa = self.client.predict(3, api_name="/run_yarqa")
        self.assertIn("0.000e+00", yarqa)
        self.assertIn("CUDA UNAVAILABLE", yarqa)
        clean = self.client.predict(4, "clean", api_name="/run_digest")
        self.assertIn("TileDigest holds", clean)
        tampered = self.client.predict(4, "drop last K-tile", api_name="/run_digest")
        self.assertIn("TileDigest BROKEN", tampered)

    def test_receipt_chain_integrity(self) -> None:
        result = self.client.predict(api_name="/chain_status")
        self.assertIn("integrity, not authorship", result)
        self.assertIn("energy UNAVAILABLE", result)
        self.assertTrue(self.app.CHAIN.verify()[0])

    def test_live_reference_training_and_embedding(self) -> None:
        tiny = self.client.predict(api_name="/train_tiny")
        self.assertIn("plan-valid", tiny)
        self.assertIn("not 1.5B", tiny)
        moons = self.client.predict(api_name="/train_moons")
        self.assertIn("Two-moons MLP trained in this process", moons)
        self.assertIn("energy UNAVAILABLE", moons)
        embed = self.client.predict(api_name="/build_embed")
        self.assertIn("Hash+table embed. Not neural.", embed)
        self.assertIn("MiniEmbed-Nano", embed)

    def test_live_anatomy_advisory_and_fail_closed(self) -> None:
        advisory = self.client.predict(*([False] * 6), api_name="/run_anatomy")
        self.assertIn("5/5 LIVE", advisory)
        self.assertIn("advisory body", advisory)
        blocked = self.client.predict(True, *([False] * 5), api_name="/run_anatomy")
        self.assertIn("BLOCKED", blocked)
        for result in (advisory, blocked):
            self.assertIn("energy UNAVAILABLE", result)
            self.assertIn("proven_trust=false", result)


if __name__ == "__main__":
    unittest.main()
