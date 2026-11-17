"""Gradio Space for the source-bound, pure-Python Khipu Proof Loom.

Gradio supplies the WebGL viewer; application logic, geometry and UI are Python.
Finite synthetic symbolic models are fitted by CPU search; no neural models,
archaeological data, external assets or custom JavaScript are loaded.
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
from hypothesis import (
    DOMAIN as SCOUT_DOMAIN,
    canonical as scout_canonical,
    TRAIN_MAX as SCOUT_TRAIN_MAX,
    EVAL_START as SCOUT_EVAL_START,
    EVAL_END as SCOUT_EVAL_END,
    fit as scout_fit,
    evaluate as scout_evaluate,
    reference_coefficients as scout_reference_coefficients,
    run_experiment as scout_run_experiment,
)


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
    expected_files = {
        "app.py", "README.md", "proof_loom.py",
        "hypothesis.py", "sequence_scout_v1.json",
    }
    if not isinstance(records, list) or len(records) != len(expected_files):
        raise RuntimeError("SOURCE_FILE_SET_INVALID")
    observed = set()
    for item in records:
        if not isinstance(item, dict):
            raise RuntimeError("SOURCE_FILE_RECORD_INVALID")
        name = item.get("dest")
        if name not in expected_files or name in observed:
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
    if observed != expected_files:
        raise RuntimeError("SOURCE_FILE_SET_MISMATCH")
    return source, hashlib.sha256(raw).hexdigest()


SOURCE_SHA, SOURCE_MANIFEST_SHA = _source_identity()


def _read_scout_receipt() -> dict:
    """Read and validate the source-pinned receipt WITHOUT training at startup."""
    path = Path(__file__).resolve().parent / "sequence_scout_v1.json"
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32768:
        raise RuntimeError("SCOUT_RECEIPT_UNAVAILABLE")
    body = path.read_bytes()
    try:
        report = json.loads(body)
    except (ValueError, UnicodeDecodeError) as exc:
        raise RuntimeError("SCOUT_RECEIPT_INVALID_JSON") from exc
    if not isinstance(report, dict):
        raise RuntimeError("SCOUT_RECEIPT_NOT_OBJECT")
    receipt_hash = report.get("sha256")
    core = {k: v for k, v in report.items() if k != "sha256"}
    if (
        report.get("schema") != "szl.khipu.sequence-scout/v1"
        or report.get("status") != "FINITE_RESEARCH_CONTROL_MATCH"
        or report.get("historical_khipu_decipherment") is not False
        or report.get("new_infinite_identity_proved") is not False
        or report.get("production_qualification") != "NOT_ASSESSED"
        or receipt_hash != hashlib.sha256(SCOUT_DOMAIN + scout_canonical(core)).hexdigest()
        or body != (json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("ascii")
    ):
        raise RuntimeError("SCOUT_RECEIPT_INTEGRITY_HOLD")
    # SOURCE.json has already authenticated the SHA-256 of this file's bytes.
    return report


SCOUT_REPORT = _read_scout_receipt()
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
.scout { background:linear-gradient(112deg,#0d2437,#0f1528);
 border:1px solid #38516c; border-radius:18px; padding:20px; margin:8px 0 16px; }
.scout h3 { color:#90f5e9; margin:0 0 12px; font-size:clamp(20px,2.8vw,30px); }
.scout-grid { display:grid; grid-template-columns: repeat(auto-fit,minmax(140px,1fr)); gap:12px; }
.scout-stat { border:1px solid #425775; border-radius:12px; padding:12px; background:#0a182a; }
.scout-stat b { font:700 24px/1.25 ui-monospace,monospace; color:#c6fbef; display:block; }
.scout-stat span { color:#bfd2e5; font:12px/1.5 system-ui; }
.scout small {color:#c0cedd;line-height:1.65;}
.scout-hold {border-color:#b36f43;background:#251b20;}
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

SCOUT_DISABLED = (
    '<section class="scout"><h3>Sequence Scout · DISABLED</h3>'
    '<p>Optional CPU symbolic training is OFF. No fitting or held-out '
    'evaluation runs while disabled. Previously displayed results are cleared '
    'when you opt out. Enable opt-in and press Train to run.</p></section>'
)
SCOUT_ARMED = (
    '<section class="scout"><h3>Sequence Scout · ARMED</h3>'
    '<p>Opt-in enabled. Enabling alone does not execute training. '
    'Press Train for a bounded CPU experiment, or uncheck to disable it.</p></section>'
)


def scout_option_state(enabled: bool) -> str:
    """Reset stale results when opting out, without performing training."""
    if type(enabled) is not bool:
        raise ValueError("SCOUT_OPT_IN_INVALID")
    return SCOUT_ARMED if enabled else SCOUT_DISABLED


def scout_panel(case: str, introduce_error: bool, opt_in: bool = False) -> str:
    """Explicitly opt in to bounded CPU fitting; never train on boot or toggles."""
    if (
        case not in ("RR1", "RR2")
        or type(introduce_error) is not bool
        or type(opt_in) is not bool
    ):
        raise ValueError("SCOUT_INPUT_NOT_ALLOWLISTED")
    if not opt_in:
        return SCOUT_DISABLED
    # Only explicit user opt-in replays training against the immutable receipt.
    expected = scout_run_experiment()
    if expected != SCOUT_REPORT:
        raise RuntimeError("SCOUT_RECEIPT_REPLAY_MISMATCH")
    samples = list(scout_reference_coefficients(case, SCOUT_TRAIN_MAX))
    if introduce_error:
        samples[6] += 1
    fitted = scout_fit(tuple(samples))
    if fitted["status"] != "TRAINING_FIT_EXACT":
        return (
            '<section class="scout scout-hold"><h3>HOLD · No supported model</h3>'
            '<p>One deliberately corrupted finite coefficient makes the fixed '
            '1,573-hypothesis family unable to fit. No trained model or proof '
            'is produced. This is an expected negative control.</p></section>'
        )
    checked = scout_evaluate(case, fitted)
    model = fitted["model"]
    return (
        '<section class="scout"><h3>Sequence Scout · bounded CPU fit</h3>'
        '<div class="scout-grid">'
        f'<div class="scout-stat"><b>mod {model["modulus"]}</b><span>smallest fitted modulus</span></div>'
        f'<div class="scout-stat"><b>{model["residues"]}</b><span>learned residue classes</span></div>'
        f'<div class="scout-stat"><b>{checked["exact_matches"]}/{checked["test_rows"]}</b>'
        '<span>held-out exact coefficient matches</span></div>'
        f'<div class="scout-stat"><b>{fitted["candidate_hypotheses_tested"]:,}</b>'
        '<span>searched finite hypotheses</span></div>'
        '</div>'
        f'<p><b>{case}</b> uses training degrees 0–{SCOUT_TRAIN_MAX}, then '
        f'independent held-out degrees {SCOUT_EVAL_START}–{SCOUT_EVAL_END}. '
        f'{fitted["candidate_matches"]} hypotheses fit training; the '
        'smallest-modulus model was selected before the held-out check. '
        f'The fixed last-value baseline matched '
        f'{checked["training_last_value_baseline_exact_matches"]}/{checked["test_rows"]}.'
        '</p>'
        f'<small>Finite verification: {checked["status"]}. This is CPU-fit '
        'symbolic parameter search, not neural training, a new infinite theorem, '
        'archaeological decoding, nor a tested generalizing scientific model. '
        f'Published synthetic receipt: {SCOUT_REPORT["sha256"][:20]}… '
        'Hash integrity does not establish authorship.</small></section>'
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
    with gr.Accordion('Sequence Scout — optional CPU hypothesis fitting', open=False):
        gr.HTML(
            '<p class="proof-intro">OFF by default. The mathematics and 3D model '
            'are available without starting a training run. Explicitly enable '
            'the CPU learner, then click Train to search 1,573 possible modular '
            'products against synthetic coefficients 0–32. It freezes a model '
            'before testing degrees 33–128. No LLM, external data or GPU.</p>'
        )
        scout_opt_in = gr.Checkbox(
            value=False, label='Enable optional CPU symbolic training (explicit opt-in)'
        )
        with gr.Row():
            scout_case = gr.Radio(['RR1', 'RR2'], value='RR1', label='Reference identity')
            scout_tamper = gr.Checkbox(value=False, label='Tamper synthetic training coefficient n=6')
        scout_result = gr.HTML(SCOUT_DISABLED)
        scout_opt_in.change(
            scout_option_state, inputs=[scout_opt_in],
            outputs=scout_result, api_name=False,
        )
        scout_button = gr.Button('Train CPU symbolic model and verify held-out', variant='primary')
        scout_button.click(
            scout_panel, inputs=[scout_case, scout_tamper, scout_opt_in],
            outputs=scout_result, api_name='discover',
        )
    gr.HTML('<p class="proof-foot">This demo has no neural or language-model training. The external '
            '<a href="https://github.com/AxiomMath/HJO">HJO formalization</a> has not '
            'been re-executed here. The <a href="https://github.com/khipulab/open-khipu-repository">'
            'Open Khipu Repository</a> supports a separate archaeological research program. '
            'Digest integrity is not a signature, and green finite checks are not infinite proof.</p>')

def launch():
    return demo.launch(server_name='0.0.0.0', server_port=int(os.getenv('PORT','7860')),
                       share=False, show_error=False, css=STYLE, allowed_paths=[ARTIFACT_DIR])

if __name__ == '__main__':
    launch()
