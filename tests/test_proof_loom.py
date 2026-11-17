"""Credential-free, offline negative controls for pure-Python Khipu 3D proof loom."""
import hashlib
import json
import struct
import unittest
from pathlib import Path

from szl_khipu import proof_loom as loom


class ProofLoomTests(unittest.TestCase):
    def test_known_rr_values(self):
        self.assertEqual((loom.witness(6, "RR1")["gap_count"], loom.witness(6, "RR2")["gap_count"]), (3, 2))
        self.assertEqual(loom.witness(0, "RR1")["gap_count"], 1)
        self.assertEqual(loom.witness(128, "RR1")["gap_count"], 519878)

    def test_all_coefficients_both_identities(self):
        for identity in ("RR1", "RR2"):
            for n in range(129):
                r = loom.witness(n, identity)
                self.assertEqual(r["gap_count"], r["residue_count"])

    def test_immutable_digest_and_claim_fences(self):
        r = loom.witness(19, "RR1", (3, 4))
        raw = {k: v for k, v in r.items() if k != "sha256"}
        b = json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        self.assertEqual(hashlib.sha256(b"szl-khipu-proofloom-v1\0" + b).hexdigest(), r["sha256"])
        self.assertFalse(r["signature_verified"])
        self.assertFalse(r["infinite_identity_proved_here"])
        self.assertFalse(r["external_hjo_lean_replayed"])
        self.assertEqual(r["historical_claim"], "NOT_ESTABLISHED")

    def test_bad_input_refused(self):
        for n in (True, -1, 129, 2.0, "2", None):
            with self.subTest(n=n), self.assertRaises(loom.EvidenceHold):
                loom.witness(n)
        with self.assertRaises(loom.EvidenceHold):
            loom.witness(1, "RR3")
        with self.assertRaises(loom.EvidenceHold):
            loom.witness(1, "RR1", (2, 4))
        with self.assertRaises(loom.EvidenceHold):
            loom.panel(2, "RR1", "99,100")

    def test_negative_control_wrong_modulus(self):
        self.assertNotEqual(loom._gap(15, 1), loom._residue(15, (1, 3)))

    def test_glb_format_and_geometry(self):
        path, _ = loom.render(18, "RR2", (3, 4))
        b = Path(path).read_bytes()
        magic, version, total = struct.unpack("<4sII", b[:12])
        self.assertEqual((magic, version, total), (b"glTF", 2, len(b)))
        length, kind = struct.unpack("<I4s", b[12:20])
        self.assertEqual(kind, b"JSON")
        j = json.loads(b[20:20 + length])
        size, kind = struct.unpack("<I4s", b[20 + length:28 + length])
        self.assertEqual(kind, b"BIN\0")
        self.assertEqual(j["buffers"][0]["byteLength"], size)
        self.assertEqual(len(j["meshes"][0]["primitives"]), 4)
        self.assertEqual(j["materials"][0]["name"], "math-torus-cyan")
        for view in j["bufferViews"]:
            self.assertLessEqual(view["byteOffset"] + view["byteLength"], size)
        self.assertLess(len(b), 3_000_000)

    def test_different_inputs_change_scene_and_receipt(self):
        p1, r1 = loom.render(18, "RR1", (2, 3))
        p2, r2 = loom.render(18, "RR2", (3, 4))
        self.assertNotEqual(p1, p2)
        self.assertNotEqual(r1["sha256"], r2["sha256"])
        self.assertNotEqual(Path(p1).read_bytes(), Path(p2).read_bytes())

    def test_readback_refuses_mutation(self):
        path, _ = loom.render(28, "RR1", (3, 5))
        original = Path(path).read_bytes()
        try:
            Path(path).write_bytes(original[:-1] + b"X")
            with self.assertRaisesRegex(loom.EvidenceHold, "RENDER_READBACK_MISMATCH"):
                loom.render(28, "RR1", (3, 5))
        finally:
            Path(path).write_bytes(original)

    def test_recorded_zero_is_not_missing(self):
        r = loom.witness(1, "RR2")
        self.assertEqual(r["gap_count"], 0)
        self.assertEqual(r["digital_cord"], {"present": True, "place_values": []})
        path, _ = loom.render(1, "RR2", (2, 3))
        self.assertTrue(Path(path).exists())

    def test_panel_presentation(self):
        path, html = loom.panel(6.0, "RR1", "2,3")
        self.assertTrue(Path(path).exists())
        self.assertIn("FINITE MATCH", html)
        self.assertIn("NOT ASSESSED", html)
        self.assertIn("does not reconstruct", html)


if __name__ == "__main__":
    unittest.main()
