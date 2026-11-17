"""Mandatory real-SDK smoke for the dedicated Gradio CI lane, not core-only installs."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
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
        self.assertEqual(gradio.__version__, "6.32.0")
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
        self.assertEqual(labels, ["Λ gate", "YARQA", "TileDigest", "TinyKhipu", "Moons", "MiniEmbed", "Anatomy", "Proof Loom 3D", "Receipts"])

    def test_szl_design_system_is_served_locally(self) -> None:
        self.assertIn(self.app.SZL_CSS_URL, self.app.HOLO_HEAD)
        self.assertNotIn("fonts.googleapis", self.app.HOLO_HEAD)
        css = httpx.get(f"{self.url}{self.app.SZL_CSS_URL}", timeout=15.0)
        css.raise_for_status()
        self.assertEqual(css.headers["content-type"].split(";")[0], "text/css")
        self.assertEqual(css.content, (self.app.SZL_DIR / "szl-design-system.css").read_bytes())

    def test_proof_loom_python_glb_contract(self) -> None:
        from szl_khipu.proof_loom import render
        path, receipt = render(18, "RR1", (2, 3))
        self.assertTrue(Path(path).exists())
        self.assertEqual(Path(path).read_bytes()[:4], b"glTF")
        self.assertEqual(receipt["model_qualification"], "NOT_ASSESSED")
        self.assertEqual(receipt["historical_claim"], "NOT_ESTABLISHED")
        self.assertIn(str(Path(path).parent), self.app.launch_demo.__globals__["PROOF_LOOM_DIR"])
        config = httpx.get(f"{self.url}config", timeout=15.0).json()
        self.assertEqual(
            len([c for c in config["components"] if c["type"] == "model3d"]), 1
        )

    def test_standalone_proof_loom_real_gradio_runtime(self) -> None:
        from scripts import publish_proofloom as publisher

        with tempfile.TemporaryDirectory(prefix="szl-proofloom-runtime-") as tmp:
            stage = Path(tmp)
            publisher._stage(stage, "a" * 40)
            spec = importlib.util.spec_from_file_location(
                "szl_proofloom_space_smoke", stage / "app.py"
            )
            standalone = importlib.util.module_from_spec(spec)
            with patch.object(sys, "path", [tmp] + sys.path):
                spec.loader.exec_module(standalone)
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                port = listener.getsockname()[1]
            try:
                _app, url, share = standalone.demo.launch(
                    server_name="127.0.0.1",
                    server_port=port,
                    prevent_thread_lock=True,
                    share=False,
                    ssr_mode=False,
                    show_error=False,
                    css=standalone.STYLE,
                    allowed_paths=[standalone.ARTIFACT_DIR],
                )
                self.assertIsNone(share)
                config = httpx.get(f"{url}config", timeout=15.0).json()
                self.assertEqual(config["title"], "Khipu Proof Loom")
                self.assertEqual(standalone.demo.delete_cache, (3600, 7200))
                self.assertEqual(standalone.demo._queue.max_size, 32)
                self.assertEqual(
                    len([c for c in config["components"] if c["type"] == "model3d"]), 1
                )
                expensive = [
                    event for event in config["dependencies"]
                    if event.get("api_name") in ("recompute", "discover")
                ]
                self.assertEqual(len(expensive), 2)
                self.assertTrue(all(
                    event.get("queue") is True
                    and event.get("trigger_mode") == "once"
                    for event in expensive
                ))
                # Gradio 6.x does NOT serialize concurrency_id/limit in public
                # /config. Verify the actual backend BlockFunction instead.
                backend = [
                    fn for fn in standalone.demo.fns.values()
                    if fn.api_name in ("recompute", "discover")
                ]
                self.assertEqual(len(backend), 2)
                self.assertTrue(all(
                    fn.concurrency_limit == 1
                    and fn.concurrency_id == "proof-loom-cpu"
                    for fn in backend
                ))
                opt_ins = [
                    part["props"] for part in config["components"]
                    if part["type"] == "checkbox"
                    and "Enable optional CPU symbolic training" in part["props"].get("label", "")
                ]
                self.assertEqual(len(opt_ins), 1)
                self.assertIs(opt_ins[0]["value"], False)
                scout_train = [
                    part["props"] for part in config["components"]
                    if part["type"] == "button"
                    and part["props"].get("value") == "Train CPU symbolic model and verify held-out"
                ]
                self.assertEqual(len(scout_train), 1)
                self.assertIs(scout_train[0]["interactive"], False)
                self.assertIs(standalone.scout_toggle(False)[1]["interactive"], False)
                self.assertIs(standalone.scout_toggle(True)[1]["interactive"], True)
                marker = (
                    'data-szl-source-sha="' + "a" * 40 +
                    '" data-szl-manifest-sha256="' +
                    hashlib.sha256((stage / "SOURCE.json").read_bytes()).hexdigest() + '"'
                )
                self.assertTrue(any(
                    c["type"] == "html" and marker in str(c.get("props", {}).get("value", ""))
                    for c in config["components"]
                ), "served UI must name exact staged source and manifest")
                client = Client(
                    url, verbose=False, analytics_enabled=False,
                    httpx_kwargs={"timeout": 15.0},
                )
                try:
                    response = client.predict(6, "RR1", "2,3", api_name="/recompute")
                    self.assertIn("FINITE MATCH", response[1])
                    self.assertIn("NOT ASSESSED", response[1])
                    # Default OFF must never invoke the fitter, even via API.
                    with patch.object(standalone, "scout_fit", side_effect=AssertionError("unexpected training")), (
                        patch.object(standalone, "scout_run_experiment", side_effect=AssertionError("unexpected replay"))
                    ):
                        disabled = client.predict("RR1", False, False, api_name="/discover")
                        self.assertIn("DISABLED", disabled)
                        self.assertNotIn("96/96", disabled)
                        self.assertEqual(
                            standalone.scout_option_state(False),
                            standalone.SCOUT_DISABLED,
                        )
                        self.assertIn("ARMED", standalone.scout_option_state(True))
                    research = client.predict("RR1", False, True, api_name="/discover")
                    self.assertIn("mod 5", research)
                    self.assertIn("96/96", research)
                    self.assertIn("not neural training", research)
                    self.assertIn("1,573", research)
                    corrupted = client.predict("RR1", True, True, api_name="/discover")
                    self.assertIn("HOLD", corrupted)
                    self.assertIn("No supported model", corrupted)
                    self.assertEqual(
                        standalone.scout_option_state(False),
                        standalone.SCOUT_DISABLED,
                    )
                finally:
                    client.close()
            finally:
                standalone.demo.close()

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
