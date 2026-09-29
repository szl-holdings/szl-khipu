# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""SZL KHIPU holographic Gradio 6 demo.

Chrome is SZL KANCHAY, founder direction (vendored byte-for-byte in szl_khipu/szl/):
space-navy operator ground, one silver orbit arc, one coral primary per tab, status
as worded chips, receipts as .receipt. Kernels stay live NumPy. sdk remains gradio.
YAML emoji is Hub metadata only. System fonts. No Google Fonts. Gradio still
injects iframe-resizer.
"""

from __future__ import annotations

import html
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
if not (ROOT / "szl_khipu").is_dir() and (ROOT.parent / "szl_khipu").is_dir():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))
# SZL KANCHAY (founder direction), vendored once in the package and served read-only.
SZL_DIR = ROOT / "szl_khipu" / "szl"

import gradio as gr  # noqa: E402
import numpy as np  # noqa: E402

from szl_khipu import (  # noqa: E402
    YUYAY_AXES,
    YUYAY_FLOORS,
    UnifiedReceiptChain,
    evaluate_anatomy,
    evaluate_lambda,
    run_tile_grid,
    yarqa_attn,
)
from szl_khipu.doctrine import DOCTRINE  # noqa: E402
from szl_khipu.train import moons, tiny_khipu  # noqa: E402
from szl_khipu.train import mini_embed as mini_embed_mod  # noqa: E402

CHAIN = UnifiedReceiptChain()
AXES = list(YUYAY_AXES)
FLOORS = list(YUYAY_FLOORS)


def _pretty(name: str) -> str:
    return re.sub(r"([a-z])([A-Z])", r"\1 \2", name).lower()


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _mint(kernel: str, op: str, payload: dict) -> int:
    CHAIN.emit(kernel, op, payload)
    _ok, depth, _brk = CHAIN.verify()
    return int(depth)


def _lrow(kind: str, title: str, detail: str, tag: str) -> str:
    mark = {"ok": "✓", "false": "✗", "part": "◐", "conj": "⬡"}.get(kind, "⬡")
    return (
        f'<div class="lrow">'
        f'<div class="mark {kind}">{mark}</div>'
        f"<div>"
        f'<p class="t">{_esc(title)}</p>'
        f'<p class="d">{detail}</p>'
        f'<span class="tag">{_esc(tag)}</span>'
        f"</div></div>"
    )


HEADER = """
<div class="holo-wrap">
  <header>
    <div class="eyebrow">SZL Holdings · KHIPU · public kernel surface</div>
    <div class="glyph">Λ</div>
    <h1>Knot the run. Hash the proof. Fail closed.</h1>
    <p class="lede">
      Live NumPy kernels wearing the estate hologram — not default Gradio chrome,
      not a FlashAttention rehost, not Qwen, not 1.5B. Uniqueness of Λ is
      <em>Conjecture 1</em>. A pass here is advisory. Gold means OPEN. Proof teal
      means LIVE. Nothing on this page is a joule, a cubin, or a theorem.
    </p>
    <div class="badges">
      <span class="chip chip-conjecture">status <b>CONJECTURE-1</b></span>
      <span class="chip">trust ceiling <b>0.97</b> · never 100%</span>
      <span class="chip">proven_trust <b>false</b></span>
      <span class="chip chip-unavailable">energy <b>UNAVAILABLE</b></span>
      <span class="chip chip-live">CPU numpy <b>LIVE</b></span>
      <span class="chip chip-unavailable">CUDA <b>UNAVAILABLE</b></span>
      <span class="chip">system fonts · no Google Fonts</span>
    </div>
  </header>
  <section class="identity" aria-label="Evidence identity">
    <div>
      <h2>Evidence identity</h2>
      <p><b>LIVE</b> means this Space executes the published <code>szl-khipu</code> package
      on CPU. It does not upgrade Conjecture 1, measure energy, or train 1.5B.</p>
    </div>
    <div>
      <dl>
        <dt>source</dt><dd>szl-holdings/szl-khipu</dd>
        <dt>doctrine</dt><dd>v11 LOCKED · 749 / 14 / 163 · kernel c7c0ba17</dd>
        <dt>locked-8</dt><dd>F1 F4 F7 F11 F12 F18 F19 F22</dd>
        <dt>failure</dt><dd>UNAVAILABLE; no cached joule, no CUDA stand-in</dd>
      </dl>
    </div>
  </section>
  <div class="ledger static-ledger">
    <div class="lrow"><div class="mark conj">⬡</div><div>
      <p class="t">Λ uniqueness — OPEN CONJECTURE 1</p>
      <p class="d">Any two aggregators satisfying A1–A4 agree on every input. OPEN (sorry). Advisory always.</p>
      <span class="tag">never a theorem · never green</span>
    </div></div>
    <div class="lrow"><div class="mark false">✗</div><div>
      <p class="t">Unconditional uniqueness — machine-checked FALSE</p>
      <p class="d">A maxAgg counterexample refutes unconditional uniqueness. Kept on the record — not hidden.</p>
      <span class="tag">lutar-lean Uniqueness.lean · F23</span>
    </div></div>
    <div class="lrow"><div class="mark part">◐</div><div>
      <p class="t">Conditional Theorem U — PROVEN (axiom-free)</p>
      <p class="d">Under its stated conditions. Strictly weaker than the conjecture. Never rounded up to it.</p>
      <span class="tag">conditional · proven</span>
    </div></div>
    <div class="lrow"><div class="mark ok">✓</div><div>
      <p class="t">CPU kernels — LIVE</p>
      <p class="d">Λ WGM, YARQA, TinyKhipu, moons 2→8→2, MiniEmbed-Nano V=64 d=12, five-organ anatomy, SHA-256 chain. CUDA UNAVAILABLE.</p>
      <span class="tag">numpy 0.1.0 · this process</span>
    </div></div>
  </div>
</div>
"""

FOOTER = """
<footer class="holo-foot">
  <div>Source: <a href="https://github.com/szl-holdings/szl-khipu" target="_blank" rel="noopener">szl-holdings/szl-khipu</a>
   · Hub <a href="https://huggingface.co/SZLHOLDINGS/szl-khipu" target="_blank" rel="noopener">SZLHOLDINGS/szl-khipu</a>
   · hologram language from <a href="https://huggingface.co/spaces/SZLHOLDINGS/lambda-gate-holo" target="_blank" rel="noopener">lambda-gate-holo</a>.</div>
  <div>SZL Holdings · governed AI you can prove · Λ = Conjecture 1, never a theorem · trust ceiling 0.97 · energy UNAVAILABLE · never a fabricated joule.</div>
</footer>
"""

HOLO_CSS = """
/* SZL KANCHAY, founder direction: szl-design-system.css (loaded in HOLO_HEAD)
   defines every token and the .chip/.receipt classes used here. Dark operator
   surface; the one coral moment per view is the tab's primary button. */
:root, .gradio-container { color-scheme: dark; }
html, body, .gradio-container, .gradio-container.light, .gradio-container.dark,
.contain, .app, .main, .wrap, .body-background-fill {
  background: var(--bg) !important;
  color: var(--text) !important;
  font-family: var(--font-body) !important;
}
html, body { min-height: 100%; margin: 0; }
.gradio-container {
  max-width: 1040px !important;
  margin: 0 auto !important;
  padding: 18px 16px 56px !important;
  position: relative;
  isolation: isolate;
}
/* The orbit motif: one faint silver arc at the -22deg tilt. No node here; coral is the primary action. */
.gradio-container::after{
  content:""; position:fixed; z-index:-1; pointer-events:none;
  top:6%; right:-8%; width:min(54vw,760px); aspect-ratio:1.9/1;
  border:1px solid color-mix(in srgb, var(--color-silver-300) 22%, transparent);
  border-radius:var(--radius-full); transform:rotate(-22deg);
}

/* Crush default Gradio chrome. */
footer { display: none !important; }
footer.svelte-1lyswbr, .built-with, #footer,
button[aria-label="Settings"], button[aria-label="Use via API"],
button[aria-label="View API"], .settings, .api-docs,
.gradio-container > footer, a[href="https://gradio.app"],
a[href="https://www.gradio.app"] { display: none !important; }

.block, .form, .panel, .tabitem, .tabs, .tab-wrapper,
.gr-panel, .gr-box, .gr-padded, .gr-input-label,
div.styler, .wrap > .contain {
  background: transparent !important;
  border-color: var(--border) !important;
  box-shadow: none !important;
}
.block {
  background: var(--surface) !important;
  border: var(--border-hairline) solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
  padding: 4px !important;
}
label, .label-wrap, .block-label, span.label-text, .block-info {
  color: var(--text-sub) !important;
  font: var(--weight-semibold) var(--text-xs)/1.4 var(--font-body) !important;
  letter-spacing: var(--tracking-caps) !important;
  text-transform: uppercase !important;
}
input, textarea, select {
  background: var(--bg-deep) !important;
  color: var(--text) !important;
  border: var(--border-hairline) solid var(--color-gray-400) !important;
  border-radius: var(--radius-md) !important;
}
input:focus-visible, textarea:focus-visible, select:focus-visible {
  outline: none !important;
  border-color: var(--focus) !important;
  box-shadow: var(--shadow-focus) !important;
}
input[type=range], input[type=checkbox] { accent-color: var(--color-silver-300) !important; }

button.primary, button.primary.svelte-1ipelgc, .primary {
  background: var(--accent) !important;
  color: var(--accent-ink) !important;
  border: var(--border-hairline) solid var(--accent) !important;
  border-radius: var(--radius-md) !important;
  font: var(--weight-semibold) var(--text-sm)/1 var(--font-body) !important;
  letter-spacing: .005em !important;
  text-transform: none !important;
  min-height: 44px !important;
  box-shadow: none !important;
}
button.primary:hover { background: var(--accent-hover) !important; border-color: var(--accent-hover) !important; }
button.lg, button.sm, button { cursor: pointer; }
:where(a, button, [role="tab"], summary):focus-visible {
  outline: var(--border-focus) solid transparent !important;
  box-shadow: var(--shadow-focus) !important;
}

.tab-nav, .tabitem, .tabs > div:first-child {
  border-color: var(--border) !important;
  background: transparent !important;
}
.tab-nav button, button[role="tab"] {
  color: var(--text-sub) !important;
  background: transparent !important;
  font: var(--weight-medium) var(--text-sm)/1.4 var(--font-body) !important;
  letter-spacing: 0 !important;
  text-transform: none !important;
  border-radius: 0 !important;
  min-height: 44px !important;
}
.tab-nav button:hover, button[role="tab"]:hover { color: var(--text) !important; }
.tab-nav button.selected, button[role="tab"].selected, button[role="tab"][aria-selected="true"] {
  color: var(--text) !important;
  border-bottom: 2px solid var(--text) !important;
  background: color-mix(in srgb, var(--text) 6%, transparent) !important;
}

/* Markdown prose reads as paragraph text; hologram HTML keeps its own roles. */
.prose:not(.holo-html), .prose:not(.holo-html) * { color: var(--text-sub) !important; }
.prose code, code {
  font-family: var(--font-mono) !important;
  font-size: var(--text-xs) !important;
  color: var(--text) !important;
  background: var(--bg-deep) !important;
  padding: 1px 5px !important;
  border-radius: var(--radius-sm) !important;
}

/* Hologram chrome (injected HTML). */
.holo-wrap, .holo-html { color: var(--text); }
.holo-wrap header { border-bottom: var(--border-hairline) solid var(--border); padding-bottom: 16px; margin-bottom: 18px; }
/* Hologram HTML sits on --surface, where --text-ghost misses AA (4.27): use --text-sub. */
.holo-wrap .eyebrow { margin: 0; color: var(--text-sub); }
.glyph { font-family: var(--font-display); font-weight: var(--weight-semibold); font-size: var(--text-2xl); line-height: 1; color: var(--text-sub); margin: .4em 0 0; }
.holo-wrap h1 { font-family: var(--font-display); font-size: clamp(var(--text-xl), 3.6vw, var(--text-3xl)); line-height: var(--leading-tight); margin: .25em 0 .2em; letter-spacing: var(--tracking-tight); color: var(--text); font-weight: var(--weight-bold); text-wrap: balance; }
.lede { color: var(--text-sub); max-width: var(--measure); margin: .35em 0 0; font-size: var(--text-base); line-height: var(--leading-normal); }
.badges { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
.badges .chip { white-space: nowrap; }
.chip b { font-weight: var(--weight-semibold); }
/* Gradio's `.gradio-container-<ver> .prose *` repaints every descendant with the body
   color; restore the design system's worded status inks inside hologram HTML. */
.holo-html .chip, .holo-html .receipt { color: var(--text-sub); }
.holo-html .chip-live, .holo-html .chip-proven { color: var(--color-success-light); }
.holo-html .chip-conjecture, .holo-html .chip-simulated { color: var(--color-warning-light); }
.holo-html .chip-sorry, .holo-html .chip-unavailable { color: var(--color-error-light); }
.holo-html .chip b { color: inherit; }
.holo-html .receipt__label { color: var(--text-sub); }
.holo-html .receipt__root { color: var(--text); }
.badge { white-space: nowrap; }
.identity { display: grid; grid-template-columns: 1.1fr .9fr; gap: 12px; margin: 18px 0 18px; }
.identity > div { border: var(--border-hairline) solid var(--border); border-radius: var(--radius-lg); background: var(--surface); padding: 15px; }
.identity h2 { margin: 0 0 7px; font-family: var(--font-display); font-weight: var(--weight-semibold); font-size: var(--text-base); letter-spacing: var(--tracking-tight); color: var(--text); }
.identity p { margin: 0; color: var(--text-sub); font-size: var(--text-sm); }
.identity dl { display: grid; grid-template-columns: auto 1fr; gap: 5px 12px; margin: 0; font: var(--text-xs)/1.5 var(--font-mono); }
.identity dt { color: var(--text-sub); }
.identity dd { margin: 0; color: var(--text); overflow-wrap: anywhere; }
.ledger { display: grid; grid-template-columns: 1fr; gap: 12px; }
.static-ledger { margin-bottom: 8px; }
.lrow { border: var(--border-hairline) solid var(--border); border-radius: var(--radius-lg); background: var(--surface); padding: 13px 15px; display: grid; grid-template-columns: auto 1fr; gap: 14px; align-items: start; }
.mark { font-size: var(--text-lg); line-height: 1.2; width: 26px; text-align: center; }
.mark.ok { color: var(--color-success-light); }
.mark.false { color: var(--color-error-light); }
.mark.part { color: var(--text-sub); }
.mark.conj { color: var(--color-warning-light); }
.lrow .t { font-family: var(--font-display); font-size: var(--text-base); letter-spacing: var(--tracking-tight); color: var(--text); margin: 0 0 3px; font-weight: var(--weight-semibold); }
.lrow .d { color: var(--text-sub); font-size: var(--text-sm); margin: 0; max-width: none; }
.lrow .d .receipt { margin-left: var(--space-1); vertical-align: middle; }
.lrow .tag { font: var(--weight-semibold) 10px/14px var(--font-mono); letter-spacing: var(--tracking-caps); text-transform: uppercase; color: var(--text-sub); display: inline-block; margin-top: 5px; border: var(--border-hairline) solid var(--border); padding: 1px 7px; border-radius: var(--radius-sm); }
.metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 12px; }
.metric { border: var(--border-hairline) solid var(--border); border-radius: var(--radius-lg); background: var(--surface); padding: 12px 14px; }
.metric .k { font: var(--weight-semibold) var(--text-xs)/1.4 var(--font-body); letter-spacing: var(--tracking-caps); text-transform: uppercase; color: var(--text-sub); }
.metric .v { font: var(--weight-semibold) var(--text-2xl)/1.1 var(--font-mono); color: var(--text); margin-top: 4px; font-variant-numeric: tabular-nums lining-nums; }
.metric .v.ok { color: var(--color-success-light); }
.metric .v.conj { color: var(--color-warning-light); }
.metric .v.false { color: var(--color-error-light); }
/* .hero here is a result panel, not the design system's hero band. */
.holo-html .hero { isolation: auto; border: var(--border-hairline) solid var(--border); border-radius: var(--radius-lg); background: var(--surface); padding: 16px 18px; margin: 0 0 12px; position: relative; overflow: hidden; }
.hero .k { font: var(--weight-semibold) var(--text-xs)/1.4 var(--font-body); letter-spacing: var(--tracking-caps); text-transform: uppercase; color: var(--text-sub); }
.hero .statement { font-size: var(--text-lg); color: var(--text); margin: .4em 0 0; line-height: var(--leading-normal); font-variant-numeric: tabular-nums lining-nums; max-width: none; }
.verdict { display: inline-block; font: var(--weight-medium) var(--text-xs)/1.5 var(--font-mono); padding: 2px 10px; border-radius: var(--radius-sm); border: var(--border-hairline) solid var(--border); color: var(--color-warning-light); background: var(--surface-alt); margin-top: 10px; }
.verdict.ok { color: var(--color-success-light); }
.verdict.false { color: var(--color-error-light); }
.holo-foot { margin-top: 28px; border-top: var(--border-hairline) solid var(--border); padding-top: 16px; color: var(--text-sub); font: var(--text-xs)/1.7 var(--font-mono); }
.holo-foot a { color: var(--link); text-decoration: none; }
.holo-foot a:hover { color: var(--link-hover); text-decoration: underline; }
.lab-lede { color: var(--text-sub); font-size: var(--text-sm); max-width: var(--measure); margin: 4px 0 12px; }
@media (max-width: 640px) {
  .identity, .metrics { grid-template-columns: 1fr; }
  .lrow { grid-template-columns: 32px minmax(0, 1fr); }
  .badges .chip, .badge { white-space: normal; }
  .gradio-container { padding: 12px 10px 40px !important; }
}

:root, .dark, .gradio-container {
  --body-background-fill: var(--bg) !important;
  --body-text-color: var(--text) !important;
  --background-fill-primary: var(--surface) !important;
  --background-fill-secondary: var(--bg-deep) !important;
  --border-color-primary: var(--border) !important;
  --block-background-fill: var(--surface) !important;
  --block-border-color: var(--border) !important;
  --block-label-text-color: var(--text-sub) !important;
  --block-title-text-color: var(--text) !important;
  --button-primary-background-fill: var(--accent) !important;
  --button-primary-text-color: var(--accent-ink) !important;
  --button-primary-background-fill-hover: var(--accent-hover) !important;
  --color-accent: var(--text-sub) !important;
  --color-accent-soft: color-mix(in srgb, var(--text) 8%, transparent) !important;
  --input-background-fill: var(--bg-deep) !important;
  --input-border-color: var(--color-gray-400) !important;
  --slider-color: var(--color-silver-300) !important;
  --link-text-color: var(--link) !important;
  --neutral-950: var(--bg) !important;
  --neutral-900: var(--bg-deep) !important;
  --neutral-800: var(--surface) !important;
  --neutral-700: var(--surface-raised) !important;
}
"""

HOLO_JS = """
function() {
  document.documentElement.setAttribute('data-theme', 'dark');
  document.documentElement.classList.add('dark');
  if (document.body) document.body.classList.add('dark');
  document.documentElement.style.background = 'var(--bg)';
}
"""

# Gradio serves the vendored folder read-only through allowed_paths (see launch_demo).
SZL_CSS_URL = "gradio_api/file=" + quote((SZL_DIR / "szl-design-system.css").as_posix(), safe="/:")
HOLO_HEAD = f"""
<meta name="color-scheme" content="dark">
<!-- theme-color cannot read CSS variables: #030F29 is --bg (--color-space-900). -->
<meta name="theme-color" content="#030F29">
<link rel="stylesheet" href="{html.escape(SZL_CSS_URL, quote=True)}">
<style>html,body{{background:var(--bg)!important;color:var(--text)!important}}</style>
"""

# Gradio's theme API takes font lists; these mirror --font-body / --font-mono exactly.
THEME = gr.themes.Base(
    primary_hue="slate",
    secondary_hue="slate",
    neutral_hue="slate",
    font=["system-ui", "-apple-system", "Segoe UI", "Helvetica Neue", "Liberation Sans", "Arial", "sans-serif"],
    font_mono=[
        "ui-monospace", "SF Mono", "Cascadia Code", "JetBrains Mono", "IBM Plex Mono",
        "Liberation Mono", "Menlo", "Consolas", "monospace",
    ],
)
try:
    THEME = THEME.set(
        body_background_fill="var(--bg)",
        body_background_fill_dark="var(--bg)",
        body_text_color="var(--text)",
        body_text_color_dark="var(--text)",
        background_fill_primary="var(--surface)",
        background_fill_primary_dark="var(--surface)",
        background_fill_secondary="var(--bg-deep)",
        background_fill_secondary_dark="var(--bg-deep)",
        border_color_primary="var(--border)",
        border_color_primary_dark="var(--border)",
        block_background_fill="var(--surface)",
        block_background_fill_dark="var(--surface)",
        block_border_color="var(--border)",
        block_border_color_dark="var(--border)",
        button_primary_background_fill="var(--accent)",
        button_primary_background_fill_dark="var(--accent)",
        button_primary_text_color="var(--accent-ink)",
        button_primary_text_color_dark="var(--accent-ink)",
        button_primary_background_fill_hover="var(--accent-hover)",
        button_primary_background_fill_hover_dark="var(--accent-hover)",
        input_background_fill="var(--bg-deep)",
        input_background_fill_dark="var(--bg-deep)",
        slider_color="var(--color-silver-300)",
        slider_color_dark="var(--color-silver-300)",
        link_text_color="var(--link)",
        link_text_color_dark="var(--link)",
        checkbox_background_color_selected="var(--surface-raised)",
        checkbox_background_color_selected_dark="var(--surface-raised)",
        checkbox_border_color_selected="var(--text-sub)",
        checkbox_border_color_selected_dark="var(--text-sub)",
        color_accent="var(--text-sub)",
        color_accent_soft="color-mix(in srgb, var(--text) 8%, transparent)",
    )
except ValueError:
    pass


def score_lambda(*values: float) -> str:
    axes = [float(v) for v in values]
    ev = evaluate_lambda(axes)
    depth = _mint("lambda", "score", {"value": float(ev["value"]), "blocked": bool(ev["blocked"])})
    blocked = bool(ev["blocked"])
    value = float(ev["value"])
    kind = "false" if blocked else "conj"
    verdict_cls = "false" if blocked else ""
    verdict = "BLOCKED" if blocked else "advisory pass · Conjecture 1 OPEN"
    axiom_bits = []
    for a in ev["axioms"]:
        color = "var(--color-error-light)" if not a["ok"] else "var(--color-success-light)"
        word = "fail" if not a["ok"] else "ok"
        axiom_bits.append(
            f'<span class="badge">{_esc(a["id"])} {_esc(a["detail"])} '
            f'<b style="color:{color}">{word}</b></span>'
        )
    axiom_html = "".join(axiom_bits)
    return (
        f'<div class="hero">'
        f'<span class="k">Λ weighted geometric mean · 13 Yuyay axes · Σw=1</span>'
        f'<p class="statement">Λ = <b>{value:.6f}</b></p>'
        f'<span class="verdict {verdict_cls}">{_esc(verdict)}</span>'
        f"</div>"
        f'<div class="badges" style="margin:0 0 12px">{axiom_html}</div>'
        + _lrow(
            kind,
            ev["reason"],
            f"chain depth {depth} · proven_trust=false · energy UNAVAILABLE · uniqueness OPEN",
            "advisory · never a theorem",
        )
    )


def run_yarqa(n_canals: float) -> str:
    n = int(n_canals)
    rng = np.random.default_rng(7)
    seq, dim = 12, 4
    q = rng.standard_normal((seq, dim))
    k = rng.standard_normal((seq, dim))
    v = rng.standard_normal((seq, dim))
    _out, _probs, leaked = yarqa_attn(q, k, v, n)
    leak = float(leaked)
    depth = _mint("yarqa", "attn", {"n_canals": n, "leaked": leak})
    ok = leak <= 1e-9
    kind = "ok" if ok else "false"
    return (
        f'<div class="metrics">'
        f'<div class="metric"><div class="k">n_canals</div><div class="v">{n}</div></div>'
        f'<div class="metric"><div class="k">leaked</div>'
        f'<div class="v {"ok" if ok else "false"}">{leak:.3e}</div></div>'
        f'<div class="metric"><div class="k">bound</div><div class="v">1e-9</div></div>'
        f"</div>"
        + _lrow(
            kind,
            "Attend only inside each canal. Cross-canal leak is a chain break.",
            f"CUDA UNAVAILABLE · not SageAttention · chain depth {depth}",
            "original compartment attention",
        )
    )


def run_digest(br: float, tamper_label: str) -> str:
    tamper = {"clean": 0, "claim coarser Br": 1, "drop last K-tile": 2}.get(tamper_label, 0)
    y = run_tile_grid(8, 4, int(br), int(br), tamper)
    depth = _mint(
        "tiledigest",
        "seal",
        {"Br": int(br), "gridBreaks": y["gridBreaks"], "cover": y["cover"], "ranDig": y["ranDig"]},
    )
    ok = y["gridBreaks"] == 0
    kind = "ok" if ok else "false"
    return (
        f'<div class="metrics">'
        f'<div class="metric"><div class="k">gridBreaks</div>'
        f'<div class="v {"ok" if ok else "false"}">{y["gridBreaks"]}</div></div>'
        f'<div class="metric"><div class="k">cover</div><div class="v">{y["cover"]}</div></div>'
        f'<div class="metric"><div class="k">tiles</div><div class="v">{y["tileCount"]}</div></div>'
        f"</div>"
        + _lrow(
            kind,
            "TileDigest holds" if ok else "TileDigest BROKEN · claimed grid is not the schedule that ran",
            f"ran {y['ranDig']} · claim {y['claimDig']} · chain depth {depth} · not Dao CUDA",
            "schedule receipt · residual is a different pin",
        )
    )


def train_tiny() -> str:
    _w, ev = tiny_khipu.train(seed=20260721, steps=280)
    depth = _mint("tiny_khipu", "train", dict(ev))
    plan = float(ev["plan_valid"])
    abstain = float(ev["abstain"])
    hall = ev["hallucinated"]
    hall_n = int(hall) if float(hall) == int(hall) else hall
    hall_cls = "ok" if float(hall) == 0 else "false"
    return (
        f'<div class="metrics">'
        f'<div class="metric"><div class="k">plan-valid</div>'
        f'<div class="v ok">{plan * 100:.0f}%</div></div>'
        f'<div class="metric"><div class="k">abstain</div>'
        f'<div class="v ok">{abstain * 100:.0f}%</div></div>'
        f'<div class="metric"><div class="k">hallucinated</div>'
        f'<div class="v {hall_cls}">{_esc(hall_n)}</div></div>'
        f"</div>"
        + _lrow(
            "ok" if float(hall) == 0 else "false",
            "NAVIGATE or ABSTAIN silhouette. Cited IDs hard-filtered to the offered set.",
            f"chain depth {depth} · a few thousand floats · not Qwen · not 1.5B · honesty REPORTED",
            f"doctrine {DOCTRINE['version']}",
        )
    )


def train_moons() -> str:
    _w, ev = moons.train(seed=20260721, steps=400)
    depth = _mint("moons", "train", dict(ev))
    acc = float(ev["acc"])
    loss = float(ev["loss"])
    return (
        f'<div class="metrics">'
        f'<div class="metric"><div class="k">acc</div>'
        f'<div class="v ok">{acc * 100:.0f}%</div></div>'
        f'<div class="metric"><div class="k">loss</div>'
        f'<div class="v">{loss:.3f}</div></div>'
        f'<div class="metric"><div class="k">shape</div><div class="v">2→8→2</div></div>'
        f"</div>"
        + _lrow(
            "ok",
            "Two-moons MLP trained in this process. Silhouette, not a foundation model.",
            f"chain depth {depth} · acc REPORTED · not 1.5B · energy UNAVAILABLE",
            "CPU numpy LIVE",
        )
    )


def build_embed() -> str:
    emb = mini_embed_mod.build(seed=20260721)
    vec = emb.embed("knot the run")
    depth = _mint("mini_embed", "build", {"V": int(emb.V), "D": int(emb.D)})
    return (
        f'<div class="metrics">'
        f'<div class="metric"><div class="k">V</div><div class="v">{int(emb.V)}</div></div>'
        f'<div class="metric"><div class="k">d</div><div class="v">{int(emb.D)}</div></div>'
        f'<div class="metric"><div class="k">||v||</div>'
        f'<div class="v ok">{float(np.linalg.norm(vec)):.3f}</div></div>'
        f"</div>"
        + _lrow(
            "ok",
            "Hash+table embed. Not neural. Not the 3290×128 MiniEmbed on szl-kernels.",
            f"chain depth {depth} · L2 rows · no analogy score · CUDA UNAVAILABLE",
            "MiniEmbed-Nano",
        )
    )


def run_anatomy(
    zero_heart: bool,
    leak_canal: bool,
    tamper_chain: bool,
    fabricate_joule: bool,
    break_skeleton: bool,
    willay_fire: bool,
) -> str:
    ev = evaluate_anatomy(
        zero_heart=bool(zero_heart),
        leak_canal=bool(leak_canal),
        tamper_chain=bool(tamper_chain),
        fabricate_joule=bool(fabricate_joule),
        break_skeleton=bool(break_skeleton),
        willay_fire=bool(willay_fire),
        seed=11,
    )
    depth = _mint(
        "anatomy",
        "cycle",
        {
            "live_count": int(ev["live_count"]),
            "blocked": bool(ev["blocked"]),
        },
    )
    blocked = bool(ev["blocked"])
    live = int(ev["live_count"])
    kind = "false" if blocked else "ok"
    verdict_cls = "false" if blocked else "ok"
    organ_html = []
    for o in ev["organs"]:
        down = o["status"] == "DOWN"
        organ_html.append(
            f'<div class="metric">'
            f'<div class="k">{_esc(o["name"])} · {_esc(o["quechua"])}</div>'
            f'<div class="v {"false" if down else "ok"}">{_esc(o["status"])}</div>'
            f'<div class="k" style="margin-top:6px">{_esc(o["honesty"])} · '
            f'{_esc("+".join(o["formulas"]))}</div>'
            f"</div>"
        )
    willay = "REFUSED" if ev["willay"]["refused"] else "inspectable"
    return (
        f'<div class="hero">'
        f'<span class="k">five-organ integrity · fail closed · not a 3D rehost</span>'
        f'<p class="statement">{live}/5 LIVE · {_esc(ev["reason"])}</p>'
        f'<span class="verdict {verdict_cls}">'
        f'{"BLOCKED" if blocked else "advisory body"} · WILLAY {willay} · '
        f"energy UNAVAILABLE · Conjecture 1 OPEN</span>"
        f"</div>"
        f'<div class="metrics">{"".join(organ_html)}</div>'
        + _lrow(
            kind,
            "HEART is advisory Λ. YAWAR is the chain. YACHAY is read-only. "
            "NERVOUS refuses fabricated joules. SKELETON is locked-8 CHECKED ≠ PROVEN.",
            f"chain depth {depth} · proven_trust=false · 3D atlas is SLSA L1 static viz "
            "at SZLHOLDINGS/anatomy · WILLAY is tamper-EVIDENT, not tamper-proof",
            "organ integrity",
        )
    )


def chain_status() -> str:
    ok, depth, brk = CHAIN.verify()
    rows = []
    receipts = CHAIN.receipts[-8:]
    if not receipts:
        rows.append(
            _lrow(
                "part",
                "chain empty",
                "Score Λ, run YARQA, train TinyKhipu, or train moons to mint a receipt.",
                "depth 0",
            )
        )
    else:
        for rec in receipts:
            short = rec.digest[:12]
            receipt = (
                f'<span class="receipt" data-state="{"verified" if ok else "failed"}">'
                f'<span class="receipt__dot" aria-hidden="true"></span>'
                f'<span class="receipt__label">{"chain ok" if ok else "chain break"}</span>'
                f'<span class="receipt__root">{_esc(short)}…</span></span>'
            )
            rows.append(
                _lrow(
                    "ok" if ok else "false",
                    f"{rec.kernel} · {rec.op}",
                    f"seq {rec.seq} · {rec.alg} · {receipt}",
                    f"prev {rec.prev[:8]}…",
                )
            )
    status = "ok" if ok else f"BREAK at {brk}"
    head = (
        f'<div class="hero">'
        f'<span class="k">unified receipt chain · integrity, not authorship</span>'
        f'<p class="statement">depth {depth} · {_esc(status)}</p>'
        f'<span class="verdict">energy UNAVAILABLE · proven_trust=false · SHA-256</span>'
        f"</div>"
    )
    return head + "".join(rows)


with gr.Blocks(
    title="SZL KHIPU",
    analytics_enabled=False,
    fill_width=True,
) as demo:
    gr.HTML(HEADER, elem_classes=["holo-html"])
    with gr.Tabs(elem_classes=["holo-tabs"]):
        with gr.Tab("Λ gate"):
            gr.HTML(
                '<p class="lab-lede">Λ = weighted geometric mean over 13 Yuyay axes. '
                "Any zero axis fail-closes to 0. Advisory always. Uniqueness is "
                "Conjecture 1 — OPEN.</p>",
                elem_classes=["holo-html"],
            )
            sliders: list[gr.Slider] = []
            with gr.Row():
                cols = [gr.Column(), gr.Column()]
                for i, axis in enumerate(AXES):
                    with cols[i % 2]:
                        sliders.append(
                            gr.Slider(
                                0,
                                1,
                                value=float(FLOORS[i]),
                                step=0.01,
                                label=_pretty(axis),
                                info=f"floor {FLOORS[i]:.2f}",
                            )
                        )
            lam_out = gr.HTML(elem_classes=["holo-html"])
            lam_btn = gr.Button("Score Λ", variant="primary")
            lam_btn.click(score_lambda, inputs=sliders, outputs=lam_out)
            for s in sliders:
                s.release(score_lambda, inputs=sliders, outputs=lam_out)

        with gr.Tab("YARQA"):
            gr.HTML(
                '<p class="lab-lede">Original canal / compartment attention. Not SageAttention. '
                "Attend only inside each canal. Cross-canal leak is a chain break. CUDA UNAVAILABLE.</p>",
                elem_classes=["holo-html"],
            )
            n_canals = gr.Slider(2, 6, value=3, step=1, label="n canals")
            yarqa_out = gr.HTML(elem_classes=["holo-html"])
            yarqa_btn = gr.Button("Run YARQA", variant="primary")
            yarqa_btn.click(run_yarqa, inputs=[n_canals], outputs=yarqa_out)
            n_canals.release(run_yarqa, inputs=[n_canals], outputs=yarqa_out)

        with gr.Tab("TileDigest"):
            gr.HTML(
                '<p class="lab-lede">Receipt the Br×Bc schedule. Residual-vs-naive can hold while '
                "the grid lies. Not a FlashAttention rehost. No tokens/s claim. "
                "Claim a coarser Br or drop a K-tile and the bound fail-closes.</p>",
                elem_classes=["holo-html"],
            )
            td_br = gr.Slider(2, 8, value=4, step=2, label="Br = Bc")
            td_tamper = gr.Radio(
                choices=["clean", "claim coarser Br", "drop last K-tile"],
                value="clean",
                label="schedule",
            )
            td_out = gr.HTML(elem_classes=["holo-html"])
            td_btn = gr.Button("Seal tile grid", variant="primary")
            td_btn.click(run_digest, inputs=[td_br, td_tamper], outputs=td_out)

        with gr.Tab("TinyKhipu"):
            gr.HTML(
                '<p class="lab-lede">NAVIGATE or ABSTAIN silhouette. Cited IDs are hard-filtered '
                "to the offered set. A few thousand floats. Not Qwen. Not 1.5B. Abstain is the thing to beat.</p>",
                elem_classes=["holo-html"],
            )
            train_out = gr.HTML(elem_classes=["holo-html"])
            train_btn = gr.Button("Train TinyKhipu", variant="primary")
            train_btn.click(train_tiny, inputs=None, outputs=train_out)

        with gr.Tab("Moons"):
            gr.HTML(
                '<p class="lab-lede">Two-moons 2→8→2 tanh-softmax SGD. A few hundred floats. '
                "Not 1.5B. Not Qwen. Acc is REPORTED on the training moons, not a published benchmark.</p>",
                elem_classes=["holo-html"],
            )
            moons_out = gr.HTML(elem_classes=["holo-html"])
            moons_btn = gr.Button("Train moons", variant="primary")
            moons_btn.click(train_moons, inputs=None, outputs=moons_out)

        with gr.Tab("MiniEmbed"):
            gr.HTML(
                '<p class="lab-lede">V=64 d=12 hash+table. Not neural. Not the 3290×128 MiniEmbed '
                "on szl-kernels. No analogy score. L2-normalized rows.</p>",
                elem_classes=["holo-html"],
            )
            embed_out = gr.HTML(elem_classes=["holo-html"])
            embed_btn = gr.Button("Build MiniEmbed-Nano", variant="primary")
            embed_btn.click(build_embed, inputs=None, outputs=embed_out)

        with gr.Tab("Anatomy"):
            gr.HTML(
                '<p class="lab-lede">Five-organ fail-closed kernel of '
                "<a href=\"https://github.com/szl-holdings/anatomy\" target=\"_blank\" rel=\"noopener\">szl-holdings/anatomy</a>. "
                "Not a Three.js rehost. The 3D atlas is SLSA L1 static viz. "
                "Any DOWN organ or a WILLAY veto blocks the body. "
                "Λ stays Conjecture 1 OPEN. Energy UNAVAILABLE. Never a fabricated joule.</p>",
                elem_classes=["holo-html"],
            )
            with gr.Row():
                z_heart = gr.Checkbox(label="Zero Yuyay axis", value=False)
                leak = gr.Checkbox(label="Leak a canal", value=False)
                tamper = gr.Checkbox(label="Tamper YAWAR", value=False)
            with gr.Row():
                joule = gr.Checkbox(label="Fabricate a joule", value=False)
                sorry = gr.Checkbox(label="Paint a sorry green", value=False)
                willay = gr.Checkbox(label="Governance bypass", value=False)
            anatomy_out = gr.HTML(elem_classes=["holo-html"])
            anatomy_btn = gr.Button("Run organ cycle", variant="primary")
            anatomy_btn.click(
                run_anatomy,
                inputs=[z_heart, leak, tamper, joule, sorry, willay],
                outputs=anatomy_out,
            )

        with gr.Tab("Receipts"):
            gr.HTML(
                '<p class="lab-lede">Hash-chained receipts. Depth is integrity, not authorship. '
                "Energy UNAVAILABLE. This Space hashes SHA-256 (Python package). "
                "Production SHA3-256 is a different surface.</p>",
                elem_classes=["holo-html"],
            )
            depth_out = gr.HTML(elem_classes=["holo-html"])
            depth_btn = gr.Button("Read chain", variant="primary")
            depth_btn.click(chain_status, inputs=None, outputs=depth_out)

    gr.HTML(FOOTER, elem_classes=["holo-html"])


def launch_demo(
    *,
    server_name: str = "0.0.0.0",
    server_port: int | None = None,
    prevent_thread_lock: bool = False,
):
    """Launch the same styled demo for local use and the loopback CI smoke test."""
    return demo.launch(
        theme=THEME,
        css=HOLO_CSS,
        js=HOLO_JS,
        head=HOLO_HEAD,
        allowed_paths=[str(SZL_DIR)],
        server_name=server_name,
        server_port=int(os.environ.get("PORT", 7860)) if server_port is None else server_port,
        prevent_thread_lock=prevent_thread_lock,
        share=False,
        ssr_mode=False,
        footer_links=[],
        show_error=True,
    )


if __name__ == "__main__":
    launch_demo()
