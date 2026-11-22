#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Negative controls for the bounded Python GLB pre-serve readback."""
from __future__ import annotations

import importlib.util
import json
import struct
import unittest
from pathlib import Path

# Load this stdlib-only parser directly: package __init__ imports NumPy, but
# this structural contract must remain independently runnable without it.
PATH = Path(__file__).resolve().parents[1] / "szl_khipu" / "holo_glb.py"
SPEC = importlib.util.spec_from_file_location("holo_glb_structural_test", PATH)
glb = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(glb)


def sample():
    scene = glb.Scene("szl.holo.integrity-test")
    mat = scene.material("test", (0.4, 0.6, 0.8))
    scene.box((0, 0, 0), (1, 1, 1), mat)
    return scene.glb()


def rebuild(source, transform=None, raw_json=None):
    jlen = struct.unpack("<I", source[12:16])[0]
    payload = source[28 + jlen:]
    if raw_json is None:
        obj = json.loads(source[20:20 + jlen])
        if transform is not None:
            transform(obj)
        raw_json = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    raw_json += b" " * (-len(raw_json) % 4)
    total = 28 + len(raw_json) + len(payload)
    return (
        struct.pack("<4sII", b"glTF", 2, total)
        + struct.pack("<I4s", len(raw_json), b"JSON") + raw_json
        + struct.pack("<I4s", len(payload), b"BIN\0") + payload
    )


class ReadbackSafety(unittest.TestCase):
    def test_wellformed_scene_roundtrips(self):
        manifest = glb.parse_glb(sample())
        self.assertEqual(manifest["asset"]["version"], "2.0")
        self.assertEqual(len(manifest["buffers"]), 1)
        self.assertTrue(manifest["bufferViews"])

    def test_declared_json_length_cannot_escape_chunks(self):
        raw = bytearray(sample())
        raw[12:16] = struct.pack("<I", 0xfffffff8)
        with self.assertRaisesRegex(glb.HoloHold, "GLB_JSON_CHUNK_INVALID"):
            glb.parse_glb(bytes(raw))

    def test_binary_trailing_bytes_cannot_be_smuggled(self):
        raw = bytearray(sample() + b"\0\0\0\0")
        struct.pack_into("<I", raw, 8, len(raw))
        with self.assertRaisesRegex(glb.HoloHold, "GLB_BIN_CHUNK_INVALID"):
            glb.parse_glb(bytes(raw))

    def test_negative_or_boolean_view_offsets_refuse(self):
        for key, value in (("byteOffset", -2), ("byteLength", -1),
                           ("byteOffset", True), ("buffer", True)):
            with self.subTest(key=key, value=value):
                def change(obj):
                    obj["bufferViews"][0][key] = value
                with self.assertRaisesRegex(glb.HoloHold, "GLB_VIEW_OUT_OF_RANGE"):
                    glb.parse_glb(rebuild(sample(), transform=change))

    def test_duplicate_json_object_keys_refused(self):
        raw = sample()
        jlen = struct.unpack("<I", raw[12:16])[0]
        document = raw[20:20 + jlen].rstrip()
        injected = document.replace(b'"bufferViews":', b'"bufferViews":[],"bufferViews":', 1)
        with self.assertRaisesRegex(glb.HoloHold, "GLB_JSON_DUPLICATE_KEY"):
            glb.parse_glb(rebuild(raw, raw_json=injected))

    def test_json_nan_refused(self):
        with self.assertRaisesRegex(glb.HoloHold, "GLB_JSON_INVALID_NUMBER"):
            glb.parse_glb(rebuild(sample(), transform=lambda d: d["asset"].update(extra=float("nan"))))

    def test_missing_buffers_refused(self):
        def change(doc):
            doc["buffers"] = []
        with self.assertRaisesRegex(glb.HoloHold, "GLB_BIN_CHUNK_INVALID"):
            glb.parse_glb(rebuild(sample(), transform=change))


if __name__ == "__main__":
    unittest.main()
