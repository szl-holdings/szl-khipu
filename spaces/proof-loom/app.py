"""Gradio Space for the source-bound, pure-Python Khipu Proof Loom.

Gradio supplies the WebGL viewer; application logic, geometry and UI are Python.
Finite synthetic symbolic models are fitted by CPU search; no neural models,
archaeological data, external assets or custom JavaScript are loaded.
"""
from __future__ import annotations

import hashlib
import html
import json
import math
import os
import re
from pathlib import Path

import gradio as gr

# The protected publisher copies canonical szl_khipu/proof_loom.py beside this app.
from proof_loom import panel
from cylindric import (
    Hold as CylindricHold,
    witness as cylindric_witness,
)
from falsifier import (
    Hold as CrucibleHold,
    falsify as check_finite_conjecture,
    parse_residues as parse_conjecture_residues,
)
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
        "hypothesis.py", "falsifier.py", "cylindric.py",
        "sequence_scout_v1.json",
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
.hjo-profile { display:flex; flex-wrap:wrap; gap:10px; margin:14px 0; }
.hjo-cell { display:flex; flex-direction:column; gap:8px; min-width:110px;
  background:linear-gradient(148deg,#154354,#13213a); border:1px solid #387f91;
  border-radius:14px; padding:16px; }
.hjo-cell span { color:#bedce9; font:600 11px ui-monospace,monospace; }
.hjo-cell strong { color:#8ef6e6; font:700 22px ui-monospace,monospace; }
.hjo-bars {display:grid;gap:7px;margin:14px 0; }
.hjo-bar-row {display:grid;grid-template-columns:46px minmax(90px,1fr) 52px;
  gap:8px;align-items:center;font:600 12px ui-monospace,monospace; }
.hjo-bar-track {height:13px;border-radius:6px;background:#12263b;overflow:hidden; }
.hjo-bar-fill {height:100%;background:linear-gradient(90deg,#418eb1,#79e6cb);
  border-radius:6px;min-width:2px; }
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


def scout_toggle(enabled: bool) -> tuple[str, dict]:
    """Reset stale output and synchronize the actual Train button availability."""
    return scout_option_state(enabled), gr.update(interactive=enabled)


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


def conjecture_panel(
    case: str, modulus: float, residues_raw: str, degree: float,
) -> tuple[str, dict]:
    """Execute an explicitly requested, finite, three-oracle falsification."""
    try:
        if type(modulus) is float and math.isfinite(modulus) and modulus.is_integer():
            modulus = int(modulus)
        if type(degree) is float and math.isfinite(degree) and degree.is_integer():
            degree = int(degree)
        result = check_finite_conjecture(
            case, modulus, parse_conjecture_residues(residues_raw), degree
        )
    except CrucibleHold as error:
        reason = html.escape(str(error))
        return (
            '<section class="scout scout-hold"><h3>HOLD · Invalid finite proposal</h3>'
            f'<p>Input rejected: {reason}. Nothing was evaluated.</p></section>',
            {"status": "HOLD", "reason": str(error), "evaluation_performed": False},
        )
    checked = result["coefficients_checked"]
    digest = html.escape(result["sha256"][:20])
    if result["first_counterexample"] is not None:
        item = result["first_counterexample"]
        examples = html.escape(json.dumps(
            {
                "gap": item.get("gap_partition_examples_ascending"),
                "proposed": item.get("proposed_modular_partition_examples_ascending"),
                "examples_are_exhaustive": item.get("examples_are_exhaustive"),
            }, sort_keys=True,
        ))
        panel_html = (
            '<section class="scout scout-hold"><h3>REFUTED by finite counterexample</h3>'
            '<div class="scout-grid">'
            f'<div class="scout-stat"><b>n={item["degree"]}</b>'
            '<span>first mismatching degree</span></div>'
            f'<div class="scout-stat"><b>{item["expected_gap_and_qseries_count"]}</b>'
            '<span>independent reference count</span></div>'
            f'<div class="scout-stat"><b>{item["proposed_product_count"]}</b>'
            '<span>proposed modular-product count</span></div></div>'
            f'<p>Exact finite counterexample. Checked {checked} coefficients. '
            f'Displayed partition samples: <code>{examples}</code>.</p>'
            f'<small>Unsigned SHA-256 digest {digest}… . This refutes only the '
            'specified all-n partition equality, not a result about archaeology or '
            'the HJO torus-knot theorem.</small></section>'
        )
    else:
        panel_html = (
            '<section class="scout"><h3>NOT REFUTED · finite limit only</h3>'
            '<div class="scout-grid">'
            f'<div class="scout-stat"><b>{checked}/{checked}</b>'
            '<span>matching finite coefficients</span></div>'
            f'<div class="scout-stat"><b>n≤{degree}</b>'
            '<span>maximum degree tested</span></div></div>'
            f'<p>Two independent reference methods agree, and the proposed '
            f'product agrees at all tested degrees. This is <b>NOT an infinite '
            f'proof</b>. Digest {digest}…</p></section>'
        )
    return panel_html, result


def hjo_profile_panel(
    a: float, b: float, rank: float, degree: float,
) -> tuple[str, dict]:
    """On-demand finite cylindric definitions, not HJO polynomial or Lean proof."""
    numbers = []
    for item in (a, b, rank, degree):
        if type(item) is float and math.isfinite(item) and item.is_integer():
            item = int(item)
        numbers.append(item)
    try:
        report = cylindric_witness(*numbers)
    except CylindricHold as error:
        reason = html.escape(str(error))
        return (
            '<section class="scout scout-hold"><h3>HOLD · HJO profile not admitted</h3>'
            f'<p>{reason}. No finite enumeration was qualified.</p></section>',
            {"status": "HOLD", "reason": str(error), "enumeration_performed": False},
        )
    profile = "".join(
        '<div class="hjo-cell">'
        f'<span>row {i}</span><strong>c<sub>{i}</sub>={offset}</strong>'
        '</div>'
        for i, offset in enumerate(report["profile"])
    )
    values = report["cylindric_coefficients_by_volume"]
    ceiling = max(1, max(values))
    rows = "".join(
        '<div class="hjo-bar-row">'
        f'<span>q<sup>{volume}</sup></span>'
        '<div class="hjo-bar-track">'
        f'<div class="hjo-bar-fill" style="width:{max(1, 100 * value // ceiling)}%"></div>'
        '</div>'
        f'<b>{value}</b></div>'
        for volume, value in enumerate(values)
    )
    sample = html.escape(json.dumps(
        report["example_cylindric_rows"], sort_keys=True, ensure_ascii=True,
    ))
    return (
        '<section class="scout"><h3>HJO profile · exact finite definition check</h3>'
        f'<p>Source-pinned HJO balanced profile for (a,b)=({report["a"]},{report["b"]}), '
        f'maximum entry N={report["bounded_entry_max_N"]}, '
        f'volume ≤{report["finite_volume_limit"]}.</p>'
        '<div class="hjo-profile">' + profile + '</div>'
        '<p>Outgoing cylinder constraints were checked with two distinct '
        'finite enumerators. Their truncated coefficients agree:</p>'
        '<div class="hjo-bars">' + rows + '</div>'
        f'<p>One illustrative finite cylindric array: <code>{sample}</code>.</p>'
        '<small>Definition-level combinatorics only. The HJO rank-N polynomial '
        'was <b>not</b> computed; no equality to it is certified; no Lean '
        'kernel or comparator was run. The actual external challenge statement '
        '<a href="https://github.com/AxiomMath/HJO/blob/'
        '6a58dfa6ab98bd35d841cb2cf8fd9081f62fad03/Challenge/Basic.lean" '
        'target="_blank" rel="noopener">is pinned here</a>. It includes '
        'challenge-template <code>sorry</code> declarations, which are NOT '
        'proofs. Geometry is separate from archaeological khipu decoding.</small>'
        '</section>',
        report,
    )


# Delete old Gradio-generated request files after two hours, checking hourly.
# Geometry source files are owned by a process-lifetime TemporaryDirectory.
with gr.Blocks(
    title='Khipu Proof Loom', analytics_enabled=False,
    delete_cache=(3600, 7200),
) as demo:
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
    go.click(
        panel, inputs=[degree, identity, curve], outputs=[model, receipt],
        api_name='recompute', concurrency_limit=1, concurrency_id='proof-loom-cpu',
        trigger_mode='once',
    )
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
        scout_button = gr.Button(
            'Train CPU symbolic model and verify held-out',
            variant='primary', interactive=False,
        )
        scout_event = scout_button.click(
            scout_panel, inputs=[scout_case, scout_tamper, scout_opt_in],
            outputs=scout_result, api_name='discover',
            concurrency_limit=1, concurrency_id='proof-loom-cpu',
            trigger_mode='once',
        )
        # Reject queued training when the user opts out. Gradio cannot cancel
        # an already-running synchronous function, so the CPU work is bounded.
        scout_opt_in.change(
            scout_toggle, inputs=[scout_opt_in],
            outputs=[scout_result, scout_button], api_name=False,
            cancels=[scout_event], trigger_mode='always_last',
        )
    with gr.Accordion('Conjecture Crucible — exact finite falsification', open=False):
        gr.HTML(
            '<p class="proof-intro">Propose a modular-product identity and look '
            'for the first exact counterexample. Separate q-series and gap-partition '
            'calculations must agree before comparison. All inputs are bounded; '
            'finite agreement is never a proof of an infinite identity. '
            'This tests only the two classical Rogers–Ramanujan cases, '
            '<b>not</b> the new HJO torus-knot family.</p>'
        )
        with gr.Row():
            falsify_case = gr.Radio(["RR1", "RR2"], value="RR1", label="Classical reference")
            falsify_modulus = gr.Slider(2, 12, step=1, value=5, label="Proposed modulus")
            falsify_degree = gr.Slider(1, 256, step=1, value=128, label="Finite degree ceiling")
        falsify_residues = gr.Textbox(
            value="1,4", lines=1, label="Positive residue classes (sorted, e.g., 1,4)",
            max_lines=1, max_length=16,
        )
        falsify_result = gr.HTML(
            '<section class="scout"><h3>NOT EVALUATED</h3>'
            '<p>Specify your proposed residues, then click the finite checker. '
            'No test is run on page load.</p></section>'
        )
        falsify_receipt = gr.JSON(
            value={"status": "NOT_EVALUATED", "infinite_identity_proved_here": False},
            label="Unsigned reproducible finite-evidence receipt",
        )
        falsify_button = gr.Button("Find the first finite counterexample", variant="secondary")
        falsify_button.click(
            conjecture_panel,
            inputs=[falsify_case, falsify_modulus, falsify_residues, falsify_degree],
            outputs=[falsify_result, falsify_receipt],
            api_name="falsify", concurrency_limit=1, concurrency_id="proof-loom-cpu",
            trigger_mode="once",
        )
    with gr.Accordion('HJO Cylindric Lab — source-pinned finite profile', open=False):
        gr.HTML(
            '<p class="proof-intro">Explore one real combinatorial definition '
            'used by the HJO torus-knot theorem: the balanced profile and '
            'bounded cylindric partitions. All counts are exact integers '
            'from TWO different finite algorithms. This <b>does not compute</b> '
            'the HJO rank-N polynomial or verify the main equality in Lean. '
            'The original human-authored challenge is source-pinned. '
            'No training, GPU or external data are accessed.</p>'
        )
        with gr.Row():
            hjo_a = gr.Slider(2, 4, value=3, step=1, label='Coprime torus parameter a')
            hjo_b = gr.Slider(3, 9, value=5, step=1, label='Coprime torus parameter b')
        with gr.Row():
            hjo_rank = gr.Slider(0, 3, value=2, step=1, label='Maximum entry N')
            hjo_degree = gr.Slider(0, 8, value=6, step=1, label='Truncated volume degree')
        hjo_result = gr.HTML(
            '<section class="scout"><h3>NOT EVALUATED</h3>'
            '<p>Select a coprime pair with 1&lt;a&lt;b and click Run. '
            'No enumeration starts on page load.</p></section>'
        )
        hjo_receipt = gr.JSON(
            value={"status": "NOT_EVALUATED", "HJO_equality_verified_here": False},
            label="Pinned definition-level finite evidence (unsigned)",
        )
        hjo_button = gr.Button('Run exact finite cylindric enumeration', variant='secondary')
        hjo_button.click(
            hjo_profile_panel,
            inputs=[hjo_a, hjo_b, hjo_rank, hjo_degree],
            outputs=[hjo_result, hjo_receipt],
            api_name='hjo_profile', concurrency_limit=1,
            concurrency_id='proof-loom-cpu', trigger_mode='once',
        )
    gr.HTML('<p class="proof-foot">This demo has no neural or language-model training. The external '
            '<a href="https://github.com/AxiomMath/HJO">HJO formalization</a> has not '
            'been re-executed here. The <a href="https://github.com/khipulab/open-khipu-repository">'
            'Open Khipu Repository</a> supports a separate archaeological research program. '
            'Digest integrity is not a signature, and green finite checks are not infinite proof.</p>')

# One shared CPU lane for the expensive geometry and symbolic callbacks;
# keep public pending submissions bounded instead of unlimited queue growth.
demo.queue(max_size=32, default_concurrency_limit=1)


def launch():
    return demo.launch(server_name='0.0.0.0', server_port=int(os.getenv('PORT','7860')),
                       share=False, show_error=False, css=STYLE, allowed_paths=[ARTIFACT_DIR])

if __name__ == '__main__':
    launch()
