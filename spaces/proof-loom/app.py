"""Gradio Space for the source-bound, pure-Python Khipu Proof Loom.

Gradio supplies the WebGL viewer; application logic, geometry and UI are Python.
No model loads, inference, external assets, unaudited data or JavaScript sources.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

import gradio as gr

# The protected publisher copies canonical szl_khipu/proof_loom.py beside this app.
from proof_loom import panel


def _source_identity() -> tuple[str, str]:
    """Refuse unpinned, incomplete or modified deployments at boot."""
    root = Path(__file__).resolve().parent
    manifest_path = root / "SOURCE.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise RuntimeError("SOURCE_MANIFEST_MISSING")
    raw = manifest_path.read_bytes()
    if len(raw) > 32_768:
        raise RuntimeError("SOURCE_MANIFEST_TOO_LARGE")
    manifest = json.loads(raw)
    if (
        manifest.get("schema") != "szl.khipu.proof-loom-publication/v1"
        or manifest.get("source_repository") != "szl-holdings/szl-khipu"
        or manifest.get("target_space") != "SZLHOLDINGS/khipu-proof-loom"
    ):
        raise RuntimeError("SOURCE_IDENTITY_MISMATCH")
    source = manifest.get("source_commit")
    if not isinstance(source, str) or re.fullmatch(r"[0-9a-f]{40}", source) is None:
        raise RuntimeError("SOURCE_COMMIT_NOT_IMMUTABLE")
    records = manifest.get("files")
    if not isinstance(records, list) or len(records) != 3:
        raise RuntimeError("SOURCE_FILE_SET_INVALID")
    observed = set()
    for item in records:
        if not isinstance(item, dict):
            raise RuntimeError("SOURCE_FILE_RECORD_INVALID")
        name = item.get("dest")
        if name not in {"app.py", "README.md", "proof_loom.py"} or name in observed:
            raise RuntimeError("SOURCE_FILE_IDENTITY_INVALID")
        observed.add(name)
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("SOURCE_FILE_UNAVAILABLE")
        body = path.read_bytes()
        if (
            type(item.get("size")) is not int
            or len(body) != item["size"]
            or hashlib.sha256(body).hexdigest() != item.get("sha256")
        ):
            raise RuntimeError("SOURCE_FILE_BYTES_MISMATCH")
    if observed != {"app.py", "README.md", "proof_loom.py"}:
        raise RuntimeError("SOURCE_FILE_SET_MISMATCH")
    return source, hashlib.sha256(raw).hexdigest()


SOURCE_SHA, SOURCE_MANIFEST_SHA = _source_identity()
PREVIEW, INTRO = panel(18, 'RR1', '2,3')
ARTIFACT_DIR = str(Path(PREVIEW).parent)

STYLE = """
:root { color-scheme: dark; }
body, .gradio-container { background: #090e1b !important; color: #e9efff !important; }
.gradio-container { max-width: 1320px !important; margin: auto; }
.proof-head { padding: clamp(20px, 5vw, 58px); border: 1px solid #31445f;
 background: radial-gradient(ellipse at 70% 10%, #173450, transparent 65%), #0d1526;
 border-radius: 24px; box-shadow: inset 0 0 60px #00d6ef09; }
.proof-kicker { font: 600 12px/1.6 ui-monospace, monospace; letter-spacing: .14em; color: #70dbeb; }
.proof-title { font: 700 clamp(30px, 5vw, 66px)/1.04 system-ui; letter-spacing: -.06em; margin: 18px 0; }
.proof-intro { color: #c5d4e5; max-width: 75ch; line-height: 1.65; }
.proof-chip { display: inline-block; border: 1px solid #3b5275; border-radius: 99px;
 padding: 7px 11px; margin: 10px 8px 0 0; font: 600 11px ui-monospace, monospace; }
.proof-pill { color:#ffd27b; border-color:#82642f; }
.proof-foot { color: #b6c8df; font-size: 13px; line-height: 1.6; }
.receipt { background:#0b2634; border-left: 3px solid #6ff0e5; padding: 15px;
 font-family: ui-monospace, monospace; overflow-wrap:anywhere; }
@media (prefers-reduced-motion: reduce) { *,*::before,*::after {scroll-behavior:auto!important;transition:none!important;} }
"""

HEADER = """
<section class="proof-head" aria-label="Khipu research proof loom">
<div class="proof-kicker">SZL HOLDINGS / KHATU / FINITE MATHEMATICS LAB</div>
<h1 class="proof-title">Khipu <span style="color:#70f2e6">Proof Loom</span></h1>
<p class="proof-intro">Explore an actual 3D mathematical torus knot alongside a separate,
modern decimal cord representation of exactly counted Rogers–Ramanujan partitions.
Orbit, pan and zoom the model; recompute the witness in Python. Two worlds of knots,
not a claim of a common historical origin.</p>
<span class="proof-chip">PYTHON-ONLY SOURCE</span>
<span class="proof-chip">EXACT FINITE CHECK</span>
<span class="proof-chip proof-pill">NOT INFINITE PROOF</span>
<span class="proof-chip proof-pill">NOT HISTORICAL DECIPHERMENT</span>
</section>
"""
HEADER = HEADER.replace(
    "</section>",
    '<span class="proof-chip" data-szl-source-sha="'
    + SOURCE_SHA
    + '" data-szl-manifest-sha256="'
    + SOURCE_MANIFEST_SHA
    + '">PINNED SOURCE '
    + SOURCE_SHA[:12]
    + '</span></section>',
)

with gr.Blocks(title='Khipu Proof Loom', analytics_enabled=False) as demo:
    gr.HTML(HEADER)
    with gr.Row():
        degree = gr.Slider(0, 128, step=1, value=18, label='Coefficient degree n')
        identity = gr.Radio(['RR1', 'RR2'], value='RR1', label='Classical partition identity')
        curve = gr.Dropdown(['2,3', '3,4', '3,5', '3,7'], value='2,3', label='Mathematical torus knot (a,b)')
    model = gr.Model3D(
        value=PREVIEW, interactive=False, display_mode='solid',
        clear_color=(.035,.05,.085,1), camera_position=(0,.4,12),
        height=580, label='3D mathematical torus knot | separate modern cord sketch',
    )
    receipt = gr.HTML(INTRO)
    go = gr.Button('Recompute exact witness and 3D diagram', variant='primary')
    go.click(panel, inputs=[degree, identity, curve], outputs=[model, receipt], api_name='recompute')
    gr.HTML('<p class="proof-foot">This model does not use SZL trained weights. The external '
            '<a href="https://github.com/AxiomMath/HJO">HJO formalization</a> has not '
            'been re-executed here. The <a href="https://github.com/khipulab/open-khipu-repository">'
            'Open Khipu Repository</a> supports a separate archaeological research program. '
            'Digest integrity is not a signature, and green finite checks are not infinite proof.</p>')

def launch():
    return demo.launch(server_name='0.0.0.0', server_port=int(os.getenv('PORT','7860')),
                       share=False, show_error=False, css=STYLE, allowed_paths=[ARTIFACT_DIR])

if __name__ == '__main__':
    launch()
