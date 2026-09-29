# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""SZL Kanchay surface contract: exact vendored exports, local fonts, no color literals."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONTS = {
    "fonts/SpaceGrotesk-latin.woff2",
    "fonts/Inter-latin.woff2",
    "fonts/JetBrainsMono-latin.woff2",
}
# One byte-exact export per served root.
VENDORED = {
    # Package page (szl-khipu serve), Docker Space payload and Gradio demo share this copy.
    "szl_khipu/kanchay": {"kanchay.css", "kanchay-components.css"},
    "docs/kanchay": {"kanchay.css", "kanchay-components.css"},
    "atelier-space/kanchay": {"kanchay.css"},
}
# Every HTML surface and the stylesheets it must load, in load order.
PAGES = {
    "space/index.html": (
        "./kanchay/kanchay.css",
        "./kanchay/kanchay-components.css",
        "./szl-holo-v2.css",
    ),
    "szl_khipu/page.html": ("./kanchay/kanchay.css", "./kanchay/kanchay-components.css"),
    "docs/index.html": ("./kanchay/kanchay.css", "./kanchay/kanchay-components.css"),
    "atelier-space/index.html": ("./kanchay/kanchay.css", "./styles.css"),
}
SURFACE_SOURCES = (
    *PAGES,
    "space/szl-holo-v2.css",
    "space/szl-holo-v2.js",
    "atelier-space/styles.css",
    "atelier-space/app.js",
    "spaces/app.py",
)
COLOR_LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?)\(")
FONT_CDN = re.compile(r"fonts\.googleapis|fonts\.gstatic|use\.typekit|fonts\.bunny", re.IGNORECASE)
LEGACY_FACES = re.compile(r"Georgia|IBM Plex|Cascadia|Segoe|Menlo|Consolas|Times New Roman")


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class KanchaySurfaceContract(unittest.TestCase):
    def test_vendored_exports_are_byte_exact(self) -> None:
        sources = []
        for folder, stylesheets in VENDORED.items():
            root = ROOT / folder
            source = json.loads((root / "SOURCE.json").read_text(encoding="utf-8"))
            sources.append(source)
            self.assertEqual(source["name"], "szl-kanchay")
            self.assertEqual(source["version"], "1.0.0")
            present = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
            self.assertEqual(present, {"SOURCE.json", *stylesheets, *FONTS}, folder)
            for name in present - {"SOURCE.json"}:
                with self.subTest(folder=folder, file=name):
                    digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
                    self.assertEqual(digest, source["sha256"][name])
        self.assertTrue(all(source == sources[0] for source in sources))

    def test_pages_load_kanchay_first_and_no_font_cdn(self) -> None:
        link = re.compile(r'<link\s+rel="stylesheet"\s+href="([^"]+)"')
        for page, hrefs in PAGES.items():
            with self.subTest(page=page):
                links = link.findall(_text(page))
                self.assertEqual(links[0], "./kanchay/kanchay.css")
                self.assertEqual([href for href in links if href in hrefs], list(hrefs))
        for source in SURFACE_SOURCES:
            with self.subTest(source=source):
                self.assertIsNone(FONT_CDN.search(_text(source)))

    def test_surfaces_carry_no_color_literals_or_legacy_faces(self) -> None:
        for source in SURFACE_SOURCES:
            text = _text(source)
            with self.subTest(source=source):
                self.assertEqual(COLOR_LITERAL.findall(text), [])
                self.assertEqual(LEGACY_FACES.findall(text), [])

    def test_package_ships_its_kanchay_export(self) -> None:
        project = tomllib.loads(_text("pyproject.toml"))
        patterns = project["tool"]["setuptools"]["package-data"]["szl_khipu"]
        root = ROOT / "szl_khipu"
        for path in (root / "kanchay").rglob("*"):
            if path.is_file():
                relative = path.relative_to(root).as_posix()
                with self.subTest(file=relative):
                    self.assertTrue(any(fnmatch.fnmatch(relative, p) for p in patterns))

    def test_gradio_demo_serves_the_package_export(self) -> None:
        text = _text("spaces/app.py")
        self.assertIn('KANCHAY_DIR = ROOT / "szl_khipu" / "kanchay"', text)
        self.assertIn("allowed_paths=[str(KANCHAY_DIR)]", text)
        self.assertIn('KANCHAY_DIR / "kanchay.css"', text)


if __name__ == "__main__":
    unittest.main()
