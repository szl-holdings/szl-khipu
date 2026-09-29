# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""SZL KANCHAY (founder direction) surface contract.

Exact vendored exports, the design system loaded first, no webfonts, no color
literals in surface files (theme-color metas excepted: CSS variables cannot
reach them, so they must carry the --bg token hex), and one coral moment.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = "szl-design-system.css"
# One byte-exact export per served root.
VENDORED = {
    # Package page (szl-khipu serve), Docker Space payload and Gradio demo share this copy.
    "szl_khipu/szl": {CSS, "logos/szl_favicon.svg"},
    "docs/szl": {CSS},
    "atelier-space/szl": {CSS},
}
# Every HTML surface and the stylesheets it must load, in load order.
PAGES = {
    "space/index.html": ("./szl/szl-design-system.css", "./szl-holo-v2.css"),
    "szl_khipu/page.html": ("./szl/szl-design-system.css",),
    "docs/index.html": ("./szl/szl-design-system.css",),
    "atelier-space/index.html": ("./szl/szl-design-system.css", "./styles.css"),
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
WEBFONT = re.compile(r"@font-face|\.woff2?\b|fonts\.googleapis|fonts\.gstatic|fontshare|use\.typekit", re.IGNORECASE)
BRAND_FACE = re.compile(r"\bInter\b|Roboto|Space Grotesk|Syncopate|IBM Plex Sans|Georgia|Times New Roman")
RETIRED = re.compile(r"kanchay\.css|kanchay-components|--color-a11oy-|\bkc-[a-z]")
THEME_COLOR = re.compile(r'<meta name="theme-color" content="(#[0-9A-Fa-f]{6})"')


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _bg_hex() -> str:
    css = _text(f"szl_khipu/szl/{CSS}")
    token = re.search(r"--bg:var\(--(color-space-900)\)", css).group(1)
    return re.search(rf"--{token}:(#[0-9A-Fa-f]{{6}})", css).group(1)


class SzlSurfaceContract(unittest.TestCase):
    def test_vendored_exports_are_byte_exact(self) -> None:
        sources = []
        for folder, files in VENDORED.items():
            root = ROOT / folder
            source = json.loads((root / "SOURCE.json").read_text(encoding="utf-8"))
            sources.append(source)
            self.assertEqual(source["name"], "szl-kanchay")
            self.assertEqual(source["version"], "1.1.0")
            present = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
            self.assertEqual(present, {"SOURCE.json", *files}, folder)
            for name in files:
                with self.subTest(folder=folder, file=name):
                    digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
                    self.assertEqual(digest, source["sha256"][name])
        self.assertTrue(all(source == sources[0] for source in sources))
        self.assertFalse(any(ROOT.rglob("kanchay/kanchay.css")), "the v1.0.0 export is withdrawn")

    def test_pages_load_the_design_system_first(self) -> None:
        link = re.compile(r'<link\s+rel="stylesheet"\s+href="([^"]+)"')
        for page, hrefs in PAGES.items():
            with self.subTest(page=page):
                links = link.findall(_text(page))
                self.assertEqual(links[0], "./szl/szl-design-system.css")
                self.assertEqual([href for href in links if href in hrefs], list(hrefs))

    def test_surfaces_carry_no_literals_webfonts_or_retired_tokens(self) -> None:
        bg = _bg_hex()
        for source in SURFACE_SOURCES:
            text = _text(source)
            with self.subTest(source=source):
                for value in THEME_COLOR.findall(text):
                    self.assertEqual(value.upper(), bg.upper())
                scanned = THEME_COLOR.sub("", text).replace(f"{bg} is --bg", "")
                self.assertEqual(COLOR_LITERAL.findall(scanned), [])
                self.assertIsNone(WEBFONT.search(text))
                self.assertEqual(BRAND_FACE.findall(text), [])
                self.assertEqual(RETIRED.findall(text), [])

    def test_coral_is_a_single_moment(self) -> None:
        # Coral (--accent) may appear only as the Gradio primary button, the atelier
        # active-nav marker and the orbit-rule node; the Space's is the rail's orbit mark.
        allowed = {"spaces/app.py", "atelier-space/styles.css"}
        for source in SURFACE_SOURCES:
            with self.subTest(source=source):
                if "var(--accent" in _text(source):
                    self.assertIn(source, allowed)
        self.assertEqual(_text("atelier-space/styles.css").count("var(--accent)"), 1)
        for page in ("szl_khipu/page.html", "docs/index.html"):
            self.assertEqual(_text(page).count('class="orbit-rule__node"'), 1)
            self.assertNotIn("btn-primary", _text(page))

    def test_package_ships_its_szl_export(self) -> None:
        project = tomllib.loads(_text("pyproject.toml"))
        patterns = project["tool"]["setuptools"]["package-data"]["szl_khipu"]
        root = ROOT / "szl_khipu"
        for path in (root / "szl").rglob("*"):
            if path.is_file():
                relative = path.relative_to(root).as_posix()
                with self.subTest(file=relative):
                    self.assertTrue(any(fnmatch.fnmatch(relative, p) for p in patterns))

    def test_gradio_demo_serves_the_package_export(self) -> None:
        text = _text("spaces/app.py")
        self.assertIn('SZL_DIR = ROOT / "szl_khipu" / "szl"', text)
        self.assertIn("allowed_paths=[str(SZL_DIR)]", text)
        self.assertIn('SZL_DIR / "szl-design-system.css"', text)


if __name__ == "__main__":
    unittest.main()
