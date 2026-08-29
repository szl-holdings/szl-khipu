# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""SZL KHIPU holographic Gradio 5 space.

Chrome copies the estate holograms (lambda-gate-holo / governed-norm-holo):
void backdrop, lattice grid, gold = OPEN, proof teal = LIVE, never green-as-proven.
Kernels stay live NumPy. sdk remains gradio. YAML emoji is Hub metadata only.
"""

from __future__ import annotations

import html
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if not (ROOT / "szl_khipu").is_dir() and (ROOT.parent / "szl_khipu").is_dir():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

import gradio as gr  # noqa: E402
import numpy as np  # noqa: E402

from szl_khipu import (  # noqa: E402
    YUYAY_AXES,
    YUYAY_FLOORS,
    UnifiedReceiptChain,
    evaluate_lambda,
    yarqa_attn,
)
from szl_khipu.doctrine import DOCTRINE  # noqa: E402
from szl_khipu.train import tiny_khipu  # noqa: E402

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
      <span class="badge">status <b>CONJECTURE-1</b></span>
      <span class="badge">trust ceiling <b>0.97</b> · never 100%</span>
      <span class="badge">proven_trust <b>false</b></span>
      <span class="badge">energy <b>UNAVAILABLE</b></span>
      <span class="badge">CPU numpy <b>LIVE</b></span>
      <span class="badge">CUDA <b>UNAVAILABLE</b></span>
      <span class="badge">0 runtime CDN · system fonts</span>
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
      <p class="d">Λ WGM, YARQA canal leak, TinyKhipu NAVIGATE/ABSTAIN, SHA-256 receipt chain. CUDA UNAVAILABLE.</p>
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
:root{
  --bg:#05070d;--void:#080c14;--panel:#0b121b;--panel2:#0a121b;--line:#1b2734;
  --proof:#3af4c8;--lattice:#5b8dee;--gold:#e8c074;--cream:#eef3f6;--para:#9fb1bf;
  --warn:#e88a6a;--dim:#6c7d8c;--false:#d76a6a;
}
html, body, .gradio-container, .gradio-container.light, .gradio-container.dark,
.contain, .app, .main, .wrap, .body-background-fill {
  background: var(--bg) !important;
  color: var(--cream) !important;
  font-family: ui-sans-serif, system-ui, Segoe UI, Roboto, Arial, sans-serif !important;
}
html, body { min-height: 100%; margin: 0; }
.gradio-container {
  max-width: 1040px !important;
  margin: 0 auto !important;
  padding: 18px 16px 56px !important;
  position: relative;
}
.gradio-container::before{
  content:""; position:fixed; inset:0; z-index:-2; pointer-events:none;
  background:
    radial-gradient(120% 90% at 50% -10%, rgba(232,192,116,.09), transparent 60%),
    radial-gradient(90% 70% at 12% 110%, rgba(58,244,200,.07), transparent 60%),
    var(--bg);
}
.gradio-container::after{
  content:""; position:fixed; inset:0; z-index:-1; pointer-events:none;
  background:
    linear-gradient(rgba(58,244,200,.03) 1px, transparent 1px) 0 0 / 100% 34px,
    linear-gradient(90deg, rgba(91,141,238,.028) 1px, transparent 1px) 0 0 / 34px 100%;
  mask-image: radial-gradient(130% 100% at 50% 0%, #000 55%, transparent 100%);
  animation: drift 24s linear infinite;
}
@keyframes drift { to { background-position: 0 34px, 34px 0; } }
@media (prefers-reduced-motion: reduce) {
  .gradio-container::after { animation: none; }
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
  border-color: var(--line) !important;
  box-shadow: none !important;
}
.block {
  background: var(--panel) !important;
  border: 1px solid var(--line) !important;
  border-radius: 11px !important;
  padding: 4px !important;
}
label, .label-wrap, .block-label, span.label-text, .block-info {
  color: var(--dim) !important;
  font: 10.5px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace !important;
  letter-spacing: .6px !important;
  text-transform: uppercase !important;
}
input, textarea, select {
  background: var(--void) !important;
  color: var(--cream) !important;
  border: 1px solid var(--line) !important;
  border-radius: 8px !important;
}
input[type=range] { accent-color: var(--proof) !important; }

button.primary, button.primary.svelte-1ipelgc, .primary {
  background: var(--proof) !important;
  color: var(--bg) !important;
  border: 1px solid var(--proof) !important;
  border-radius: 8px !important;
  font: 600 12px ui-monospace, monospace !important;
  letter-spacing: .8px !important;
  text-transform: uppercase !important;
  min-height: 44px !important;
  box-shadow: 0 0 18px rgba(58,244,200,.18) !important;
}
button.primary:hover { filter: brightness(1.06); }
button.lg, button.sm, button { cursor: pointer; }

.tab-nav, .tabitem, .tabs > div:first-child {
  border-color: var(--line) !important;
  background: transparent !important;
}
.tab-nav button, .tabs button {
  color: var(--para) !important;
  background: transparent !important;
  font: 600 12px ui-monospace, monospace !important;
  letter-spacing: .5px !important;
  text-transform: uppercase !important;
  border-radius: 0 !important;
  min-height: 44px !important;
}
.tab-nav button.selected, .tabs button.selected, .tab-nav button[aria-selected="true"] {
  color: var(--gold) !important;
  border-bottom: 1px solid var(--gold) !important;
  background: rgba(232,192,116,.06) !important;
}

.prose, .prose * { color: var(--para) !important; }
.prose code, code {
  font: 12px ui-monospace, monospace !important;
  color: var(--lattice) !important;
  background: #0e1620 !important;
  padding: 1px 5px !important;
  border-radius: 4px !important;
}

/* Hologram chrome (injected HTML). */
.holo-wrap, .holo-html { color: var(--cream); }
.holo-wrap header { border-bottom: 1px solid var(--line); padding-bottom: 16px; margin-bottom: 18px; }
.eyebrow { font: 10.5px ui-monospace, monospace; letter-spacing: 1.4px; text-transform: uppercase; color: var(--gold); opacity: .9; }
.glyph { font-size: clamp(48px, 11vw, 86px); line-height: 1; color: var(--gold); text-shadow: 0 0 34px rgba(232,192,116,.4); margin: .15em 0 0; }
.holo-wrap h1 { font-size: clamp(20px, 3.6vw, 31px); margin: .15em 0 .1em; letter-spacing: .3px; color: var(--cream); font-weight: 600; }
.lede { color: var(--para); max-width: 72ch; margin: .35em 0 0; font-size: 14.5px; line-height: 1.55; }
.badges { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
.badge { font: 10.5px ui-monospace, monospace; padding: 3px 9px; border-radius: 6px; border: 1px solid var(--line); color: var(--para); background: #10171f; white-space: nowrap; }
.badge b { color: var(--gold); font-weight: 600; }
.identity { display: grid; grid-template-columns: 1.1fr .9fr; gap: 12px; margin: 18px 0 18px; }
.identity > div { border: 1px solid var(--line); border-radius: 11px; background: var(--panel); padding: 15px; }
.identity h2 { margin: 0 0 7px; font-size: 14px; color: var(--cream); }
.identity p { margin: 0; color: var(--para); font-size: 12.5px; }
.identity dl { display: grid; grid-template-columns: auto 1fr; gap: 5px 12px; margin: 0; font: 11px/1.5 ui-monospace, monospace; }
.identity dt { color: var(--dim); }
.identity dd { margin: 0; color: var(--cream); overflow-wrap: anywhere; }
.ledger { display: grid; grid-template-columns: 1fr; gap: 12px; }
.static-ledger { margin-bottom: 8px; }
.lrow { border: 1px solid var(--line); border-radius: 11px; background: var(--panel); padding: 13px 15px; display: grid; grid-template-columns: auto 1fr; gap: 14px; align-items: start; }
.mark { font-size: 20px; line-height: 1.2; width: 26px; text-align: center; }
.mark.ok { color: var(--proof); }
.mark.false { color: var(--false); }
.mark.part { color: var(--lattice); }
.mark.conj { color: var(--gold); }
.lrow .t { font-size: 14px; color: var(--cream); margin: 0 0 3px; font-weight: 600; }
.lrow .d { color: var(--para); font-size: 13px; margin: 0; }
.lrow .tag { font: 10px ui-monospace, monospace; letter-spacing: .6px; text-transform: uppercase; color: var(--dim); display: inline-block; margin-top: 5px; border: 1px solid var(--line); padding: 1px 7px; border-radius: 5px; }
.metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 12px; }
.metric { border: 1px solid var(--line); border-radius: 11px; background: var(--panel); padding: 12px 14px; }
.metric .k { font: 10px ui-monospace, monospace; letter-spacing: .8px; text-transform: uppercase; color: var(--dim); }
.metric .v { font: 28px/1.1 ui-monospace, monospace; color: var(--cream); margin-top: 4px; font-variant-numeric: tabular-nums; }
.metric .v.ok { color: var(--proof); }
.metric .v.conj { color: var(--gold); }
.metric .v.false { color: var(--false); }
.hero { border: 1px solid #34301f; border-radius: 14px; background: linear-gradient(180deg, rgba(232,192,116,.06), var(--void)); padding: 16px 18px; margin: 0 0 12px; position: relative; overflow: hidden; }
.hero::before { content: ""; position: absolute; inset: 0 0 auto 0; height: 1px; background: linear-gradient(90deg, transparent, var(--gold), transparent); opacity: .6; }
.hero .k { font: 10px ui-monospace, monospace; letter-spacing: .8px; text-transform: uppercase; color: var(--dim); }
.hero .statement { font-size: 15.5px; color: var(--cream); margin: .4em 0 0; line-height: 1.6; }
.verdict { display: inline-block; font: 11px ui-monospace, monospace; letter-spacing: .5px; padding: 3px 10px; border-radius: 6px; border: 1px solid var(--gold); color: var(--gold); background: rgba(232,192,116,.08); margin-top: 10px; }
.verdict.ok { border-color: var(--proof); color: var(--proof); background: rgba(58,244,200,.08); }
.verdict.false { border-color: var(--false); color: var(--false); background: rgba(215,106,106,.08); }
.holo-foot { margin-top: 28px; border-top: 1px solid var(--line); padding-top: 16px; color: var(--dim); font: 11px/1.7 ui-monospace, monospace; }
.holo-foot a { color: var(--proof); text-decoration: none; }
.holo-foot a:hover { text-decoration: underline; }
.lab-lede { color: var(--para); font-size: 13.5px; max-width: 72ch; margin: 4px 0 12px; }
@media (max-width: 640px) {
  .identity, .metrics { grid-template-columns: 1fr; }
  .lrow { grid-template-columns: 32px minmax(0, 1fr); }
  .badge { white-space: normal; }
  .gradio-container { padding: 12px 10px 40px !important; }
}

:root, .dark, .gradio-container {
  --body-background-fill: #05070d !important;
  --body-text-color: #eef3f6 !important;
  --background-fill-primary: #0b121b !important;
  --background-fill-secondary: #080c14 !important;
  --border-color-primary: #1b2734 !important;
  --block-background-fill: #0b121b !important;
  --block-border-color: #1b2734 !important;
  --block-label-text-color: #6c7d8c !important;
  --block-title-text-color: #eef3f6 !important;
  --button-primary-background-fill: #3af4c8 !important;
  --button-primary-text-color: #05070d !important;
  --button-primary-background-fill-hover: #6af8d6 !important;
  --color-accent: #3af4c8 !important;
  --color-accent-soft: rgba(58,244,200,.12) !important;
  --input-background-fill: #080c14 !important;
  --input-border-color: #1b2734 !important;
  --slider-color: #3af4c8 !important;
  --link-text-color: #3af4c8 !important;
  --neutral-950: #05070d !important;
  --neutral-900: #080c14 !important;
  --neutral-800: #0b121b !important;
  --neutral-700: #1b2734 !important;
}
"""

HOLO_JS = """
function() {
  document.documentElement.setAttribute('data-theme', 'dark');
  document.documentElement.classList.add('dark');
  if (document.body) document.body.classList.add('dark');
  document.documentElement.style.background = '#05070d';
}
"""

HOLO_HEAD = """
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#05070d">
<style>html,body{background:#05070d!important;color:#eef3f6!important}</style>
"""

THEME = gr.themes.Base(
    primary_hue="teal",
    secondary_hue="slate",
    neutral_hue="slate",
    font=["ui-sans-serif", "system-ui", "Segoe UI", "Roboto", "Arial", "sans-serif"],
    font_mono=["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
)
try:
    THEME = THEME.set(
        body_background_fill="#05070d",
        body_background_fill_dark="#05070d",
        body_text_color="#eef3f6",
        body_text_color_dark="#eef3f6",
        background_fill_primary="#0b121b",
        background_fill_primary_dark="#0b121b",
        background_fill_secondary="#080c14",
        background_fill_secondary_dark="#080c14",
        border_color_primary="#1b2734",
        border_color_primary_dark="#1b2734",
        block_background_fill="#0b121b",
        block_background_fill_dark="#0b121b",
        block_border_color="#1b2734",
        block_border_color_dark="#1b2734",
        button_primary_background_fill="#3af4c8",
        button_primary_background_fill_dark="#3af4c8",
        button_primary_text_color="#05070d",
        button_primary_text_color_dark="#05070d",
        button_primary_background_fill_hover="#6af8d6",
        button_primary_background_fill_hover_dark="#6af8d6",
        color_accent="#3af4c8",
        color_accent_soft="rgba(58,244,200,0.12)",
        input_background_fill="#080c14",
        input_background_fill_dark="#080c14",
        slider_color="#3af4c8",
        slider_color_dark="#3af4c8",
        link_text_color="#3af4c8",
        link_text_color_dark="#3af4c8",
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
        color = "var(--false)" if not a["ok"] else "var(--proof)"
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


def chain_status() -> str:
    ok, depth, brk = CHAIN.verify()
    rows = []
    receipts = CHAIN.receipts[-8:]
    if not receipts:
        rows.append(
            _lrow(
                "part",
                "chain empty",
                "Score Λ, run YARQA, or train TinyKhipu to mint a receipt.",
                "depth 0",
            )
        )
    else:
        for rec in receipts:
            short = rec.digest[:12]
            rows.append(
                _lrow(
                    "ok" if ok else "false",
                    f"{rec.kernel} · {rec.op}",
                    f"seq {rec.seq} · {rec.alg} · {short}…",
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
    theme=THEME,
    css=HOLO_CSS,
    js=HOLO_JS,
    head=HOLO_HEAD,
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

        with gr.Tab("TinyKhipu"):
            gr.HTML(
                '<p class="lab-lede">NAVIGATE or ABSTAIN silhouette. Cited IDs are hard-filtered '
                "to the offered set. A few thousand floats. Not Qwen. Not 1.5B. Abstain is the thing to beat.</p>",
                elem_classes=["holo-html"],
            )
            train_out = gr.HTML(elem_classes=["holo-html"])
            train_btn = gr.Button("Train TinyKhipu", variant="primary")
            train_btn.click(train_tiny, inputs=None, outputs=train_out)

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


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
        show_error=True,
    )
