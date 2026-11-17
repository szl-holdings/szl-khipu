"""Gradio Space for the source-bound, pure-Python Khipu Proof Loom.

Three labs share one CPU lane and one hash-chained session ledger:
  * Ancestral arithmetic — 619 real Inka-style khipus from the Open Khipu
    Repository (MIT), exact decimal sum relations against a permutation null.
  * HJO Loom — exact finite replays of the 2026 X^a = Y^b Rogers–Ramanujan
    theorems (Huang–Lau–Ono; Huang–Jiang–Oblomkov), incl. finite-field counts.
  * Classic Proof Loom — the original Rogers–Ramanujan witness and Sequence Scout.
Gradio supplies the WebGL viewer; application logic, geometry and UI are Python.
"""
from __future__ import annotations

import hashlib
import html
import inspect
import json
import math
import os
import re
import tempfile
import threading
from functools import lru_cache
from pathlib import Path

import gradio as gr

# The protected publisher copies canonical sources beside this app.
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
import hjo_loom as hjo
import holo_glb as holo
import okr_khipu as okr
from chain import UnifiedReceiptChain

ROOT = Path(__file__).resolve().parent
EXPECTED_FILES = {
    "app.py", "README.md", "proof_loom.py", "hypothesis.py", "falsifier.py", "cylindric.py", "sequence_scout_v1.json",
    "hjo_loom.py", "holo_glb.py", "okr_khipu.py", "chain.py", "hjo_certificate_v1.json",
    "okr_corpus_v1.json.gz", "okr_relations_v1.json", "LICENSE-OKR.txt",
}


def _source_identity() -> tuple[str, str]:
    """Refuse unpinned, incomplete or modified deployments at boot."""
    manifest_path = ROOT / "SOURCE.json"
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
    if not isinstance(records, list) or len(records) != len(EXPECTED_FILES):
        raise RuntimeError("SOURCE_FILE_SET_INVALID")
    observed = set()
    for item in records:
        if not isinstance(item, dict):
            raise RuntimeError("SOURCE_FILE_RECORD_INVALID")
        name = item.get("dest")
        if name not in EXPECTED_FILES or name in observed:
            raise RuntimeError("SOURCE_FILE_IDENTITY_INVALID")
        observed.add(name)
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("SOURCE_FILE_UNAVAILABLE")
        body = path.read_bytes()
        if (
            type(item.get("size")) is not int
            or len(body) != item["size"]
            or hashlib.sha256(body).hexdigest() != item.get("sha256")
        ):
            raise RuntimeError("SOURCE_FILE_BYTES_MISMATCH")
    if observed != EXPECTED_FILES:
        raise RuntimeError("SOURCE_FILE_SET_MISMATCH")
    return source, hashlib.sha256(raw).hexdigest()


SOURCE_SHA, SOURCE_MANIFEST_SHA = _source_identity()


def _read_scout_receipt() -> dict:
    """Read and validate the source-pinned receipt WITHOUT training at startup."""
    path = ROOT / "sequence_scout_v1.json"
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
    return report


def _read_certificate() -> dict:
    cert = json.loads((ROOT / "hjo_certificate_v1.json").read_text(encoding="ascii"))
    if (
        cert.get("schema") != "szl.khipu.hjo-certificate/v1"
        or hjo.seal(cert)["sha256"] != cert.get("sha256")
        or cert.get("new_theorem_proved") is not False
        or cert.get("lean_certificate_replayed") is not False
        or cert.get("historical_claim") != "NOT_ESTABLISHED"
    ):
        raise RuntimeError("HJO_CERTIFICATE_INTEGRITY_HOLD")
    return cert


SCOUT_REPORT = _read_scout_receipt()
CERT = _read_certificate()
CORPUS = okr.load_corpus(ROOT / "okr_corpus_v1.json.gz", expected_sha256=okr.CORPUS_SHA256)
RELATIONS = okr.load_relations_report(ROOT / "okr_relations_v1.json", corpus_sha256=CORPUS["sha256"])
KHIPU_ROWS = okr.list_khipus(CORPUS)
KHIPU_IDS = {r["okr_num"] for r in KHIPU_ROWS if r["okr_num"]}
KHIPU_CHOICES = [
    (f'{r["okr_num"]} · {r["investigator_num"] or "—"} · {r["n_relations"]} relations', r["okr_num"])
    for r in KHIPU_ROWS if r["okr_num"]
]
DEFAULT_KHIPU = KHIPU_CHOICES[0][1]
HJO_PAIRS = ["2,3", "2,5", "3,4", "3,5", "2,7", "4,5", "3,7", "2,9", "3,8", "4,7", "5,6"]
RELATION_NAMES = {
    "R1": "subsidiary sum", "R2": "top-cord sum", "R3": "sum of another group", "R4": "in-group sum cord",
}

_SCENES = tempfile.TemporaryDirectory(prefix="szl-proof-loom-scenes-")
SCENE_DIR = Path(_SCENES.name)
_SCENE_LOCK = threading.Lock()


def _store_glb(prefix: str, data: bytes) -> str:
    """Content-addressed GLB, written atomically and read back before serving."""
    holo.parse_glb(data)
    digest = hashlib.sha256(data).hexdigest()
    dest = SCENE_DIR / f"{prefix}-{digest[:24]}.glb"
    with _SCENE_LOCK:
        if not dest.exists():
            tmp = dest.with_suffix(".tmp")
            with tmp.open("xb") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, dest)
        if dest.is_symlink() or hashlib.sha256(dest.read_bytes()).hexdigest() != digest:
            raise RuntimeError("SCENE_READBACK_MISMATCH")
    return str(dest)


def _esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


# --------------------------------------------------------------------------
# Session ledger (hash-chained receipts; SHA-256, unsigned)
# --------------------------------------------------------------------------

def _ledger_html(chain: UnifiedReceiptChain) -> str:
    ok, depth, brk = chain.verify()
    rows = "".join(
        f"<tr><td>{r.seq}</td><td>{_esc(r.kernel)}</td><td>{_esc(r.op)}</td>"
        f"<td><code>{r.digest[:16]}…</code></td><td><code>{r.prev[:16]}…</code></td></tr>"
        for r in chain.receipts[-12:]
    )
    state = "CHAIN INTACT" if ok else f"CHAIN BROKEN at {brk}"
    return (
        f'<div class="ledger"><b>{state}</b> · depth {depth} · head '
        f'<code>{chain.head[:24]}…</code><br><small>Session-local SHA-256 hash chain '
        '(szl_khipu.chain). Unsigned: digest integrity is not a signature or identity.</small>'
        f'<table><tr><th>#</th><th>kernel</th><th>op</th><th>digest</th><th>prev</th></tr>{rows}</table></div>'
    )


def _emit(chain, kernel: str, op: str, payload: dict) -> UnifiedReceiptChain:
    if not isinstance(chain, UnifiedReceiptChain):
        chain = UnifiedReceiptChain()
    if len(chain.receipts) >= 256:
        chain = UnifiedReceiptChain()
    chain.emit(kernel, op, payload)
    return chain


# --------------------------------------------------------------------------
# Ancestral arithmetic (OKR)
# --------------------------------------------------------------------------

def _corpus_banner() -> str:
    stats = RELATIONS["statistics"]
    prim = stats["by_strata"]["role_depth"]
    strict = stats["by_strata"].get("role_depth_magnitude", {})
    cells = []
    for t in okr.RELATION_TYPES:
        row = prim[t]
        drop = row.get("drop_top_khipu") or {}
        robust = (
            row["pooled_p"] <= 0.001
            and drop.get("pooled_p", 1) <= 0.01
            and strict.get(t, {}).get("pooled_p", 1) <= 0.01
        )
        verdict = "ROBUST" if robust else ("NOT ABOVE CHANCE" if row["pooled_p"] > 0.05 else "CONCENTRATED")
        cells.append(
            f'<div class="stat {"stat-strong" if robust else ""}"><b>{row["observed"]}</b>'
            f'<span>{t} · {RELATION_NAMES[t]}</span>'
            f'<em>null mean {row["null_mean"]:.1f} · ×{row["ratio_observed_to_null"]:.1f} · '
            f'p {"≤" if row["pooled_p"] <= stats["min_attainable_p"] else "="} {row["pooled_p"]:.3f}</em>'
            f'<i>{verdict}</i></div>'
        )
    r2 = prim["R2"]
    return (
        '<section class="banner"><div class="kicker">MEASURED ON 619 PINNED OKR RECORDS · '
        f'{stats["trials"]:,} WITHIN-KHIPU PERMUTATIONS · SEED {stats["seed"]}</div>'
        f'<h2>Top cords record exact decimal sums of the pendants beneath them — '
        f'{r2["observed"]} times, against {r2["null_mean"]:.1f} expected by chance.</h2>'
        '<p>Every relation below is an exact equality between knot values read with the '
        'Locke decimal convention from the Open Khipu Repository transcriptions. The chance '
        'control shuffles values among cords of the same role and depth inside each khipu '
        'and reruns the identical search. Top-cord sums (R2) survive a stricter null, '
        'dropping the strongest khipu, and excluding Incahuasi. The other types do not all '
        'survive: R1 is carried by one khipu, R4 mostly by Incahuasi, R3 is at chance level. '
        'This is arithmetic structure in the record, consistent with Ascher &amp; Ascher (1981) '
        '— not a decipherment of khipu narrative.</p>'
        f'<div class="grid">{"".join(cells)}</div></section>'
    )


def _relation_rows(rels: list) -> str:
    rows = []
    for r in rels[:60]:
        vals = " + ".join(str(v) for v in r["summand_values"][:14])
        if len(r["summand_values"]) > 14:
            vals += f" + … ({len(r['summand_values'])} cords)"
        flag = ' <span class="flag">broken cord involved</span>' if r.get("involves_broken_cord") else ""
        rows.append(
            f'<tr><td>{_esc(r["type"])}</td><td>{_esc(RELATION_NAMES.get(r["type"], ""))}</td>'
            f'<td><b>{_esc(r["target_value"])}</b> = {_esc(vals)}{flag}</td>'
            f'<td><code>{_esc(r["target"])}</code></td></tr>'
        )
    more = f"<p><small>{len(rels) - 60} more not shown.</small></p>" if len(rels) > 60 else ""
    return (
        '<table class="rel"><tr><th>type</th><th>relation</th><th>exact equality (knot values)</th>'
        f'<th>OKR cord id</th></tr>{"".join(rows)}</table>{more}'
    )


@lru_cache(maxsize=48)
def _khipu_render(okr_num: str, types: tuple[str, ...]) -> tuple[str, str]:
    k = okr.get_khipu(CORPUS, okr_num)
    prims = okr.scene(k)
    prims = {**prims, "arcs": [a for a in prims.get("arcs", []) if a.get("relation") in types]}
    path = _store_glb("khipu", holo.khipu_scene(prims, show_relations=True))
    card = okr.khipu_card(k, report=RELATIONS)
    rels = okr.find_relations(k)          # evidence table always lists every type
    meta = prims.get("meta") or {}
    null = card["null"]
    pcells = "".join(
        f'<span class="chip">{t}: {card["relations"][t]} obs · null {null["null_mean"][t]:.2f} · '
        f'p {null["p"][t]:.3f}</span>'
        for t in okr.RELATION_TYPES
    )
    trunc = " · drawing truncated to the cord budget" if meta.get("truncated_cords") else ""
    body = (
        f'<div class="card"><h3>{_esc(card["okr_num"])} <small>{_esc(card["investigator_num"])}</small></h3>'
        f'<p>{_esc(card["museum"]) or "museum not recorded"} · {_esc(card["provenance"]) or "provenance not recorded"}'
        f' · {_esc(card["country"])}</p>'
        f'<p>{card["n_cords"]} cords ({card["n_pendants"]} pendant, {card["n_top"]} top, '
        f'{card["n_subsidiary"]} subsidiary) · {card["n_knots"]} knots · values known on '
        f'{card["n_value_known"]}, unknown on {card["n_value_unknown"]} (missing is never read as zero){trunc}</p>'
        f'<div>{pcells}</div>'
        f'<p class="note">{_esc(card["label"])}. Layout is schematic: {_esc(meta.get("layout", ""))}. '
        f'Colours: {_esc(meta.get("rgb_source", ""))}. Source: {_esc(card["source"])}.</p>'
        f'{_relation_rows(rels)}</div>'
    )
    return path, body


def khipu_panel(okr_num: str, include_r3: bool, chain=None):
    if okr_num not in KHIPU_IDS or type(include_r3) is not bool:
        raise gr.Error("Choose a khipu from the list.")
    types = ("R1", "R2", "R3", "R4") if include_r3 else ("R1", "R2", "R4")
    path, body = _khipu_render(okr_num, types)
    scene_sha = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    chain = _emit(chain, "okr-khipu", "render", {
        "okr_num": okr_num, "relation_types": list(types), "scene_sha256": scene_sha,
        "corpus_sha256": CORPUS["sha256"], "relations_sha256": RELATIONS["sha256"],
    })
    return path, body, chain, _ledger_html(chain)


# --------------------------------------------------------------------------
# HJO Loom
# --------------------------------------------------------------------------

def _poly(coeffs: list, limit: int = 18) -> str:
    terms = []
    for k, c in enumerate(coeffs[:limit]):
        if c:
            terms.append(f"{c}" if k == 0 else (f"{'' if c == 1 else c}q<sup>{k}</sup>" if k > 1 else f"{'' if c == 1 else c}q"))
    tail = " + …" if any(coeffs[limit:]) else ""
    return " + ".join(terms) + tail


@lru_cache(maxsize=64)
def _hjo_run(a: int, b: int, rank: int, field: int) -> tuple[str, dict]:
    record = hjo.verify(a, b, degree=24, rank=rank, field=field, quot_m=3,
                        nil_n=3 if field == 2 else 2, budget=120_000)
    profile = hjo.balanced_profile(a, b)
    rows = hjo.sample_cylindric(profile, 2, 16, seed=100 * a + b)
    data = holo.hjo_scene(a, b, hjo.gap_poset(a, b).gaps, hjo.cover_relations(a, b), rows, profile)
    return _store_glb("hjo", data), record


def hjo_panel(pair: str, rank: int, field: int, chain=None):
    if pair not in HJO_PAIRS or rank not in (1, 2) or field not in (2, 3):
        raise gr.Error("Choose a listed pair, rank 1–2 and field F2 or F3.")
    a, b = (int(x) for x in pair.split(","))
    try:
        path, rec = _hjo_run(a, b, rank, field)
    except hjo.HjoHold as exc:
        raise gr.Error(f"HOLD: {exc}") from None
    rho = [hjo.rho(a, b, m) for m in range(1, a + b + 1)]
    checks = "".join(
        f'<tr><td>{_esc(c["id"])}</td><td>{_esc(c["statement"])}</td>'
        f'<td class="s-{_esc(c["status"]).lower()}">{_esc(c["status"])}</td>'
        f'<td>{_esc(_check_detail(c))}</td></tr>'
        for c in rec["checks"]
    )
    body = (
        f'<div class="card"><h3>X<sup>{a}</sup> = Y<sup>{b}</sup> · torus knot T({a},{b})</h3>'
        f'<p>d = {rec["d"]}, δ = {rec["delta"]}, Frobenius number f = {rec["f"]}, gaps G = {rec["gaps"]}, '
        f'balanced profile c = {rec["profile"]}.</p>'
        f'<p><b>Z<sub>{a},{b}</sub>(q)</b> = {_poly(rec["z_coefficients"])}</p>'
        f'<p><b>P<sub>{a},{b}</sub>(q)</b> = ∏<sub>m≥1</sub>(1−q<sup>m</sup>)<sup>−ρ(m)</sup>, '
        f'ρ(1..{a + b}) = {rho} (period {a + b})</p>'
        f'<p><b>F<sub>{rank}</sub>(q)</b> = {_poly(rec["F_N"], 26)} · F<sub>{rank}</sub>(1) = '
        f'{sum(rec["F_N"]):,} = Cat({a},{b})<sup>{rank}</sup></p>'
        f'<table class="rel"><tr><th>check</th><th>statement</th><th>status</th><th>detail</th></tr>{checks}</table>'
        f'<p class="note">Record digest <code>{rec["sha256"][:24]}…</code>. Exact finite checks of '
        'published theorems by independent routes; nothing new is proved, the Lean certificate '
        'is not replayed here, and no historical claim is made. NOT_RUN_BUDGET means the bounded '
        'brute force was not attempted to completion — it is never reported as a match.</p></div>'
    )
    chain = _emit(chain, "hjo-loom", "verify", {
        "pair": [a, b], "rank": rank, "field": field, "record_sha256": rec["sha256"],
        "statuses": {c["id"]: c["status"] for c in rec["checks"]},
    })
    return path, body, chain, _ledger_html(chain)


def _check_detail(c: dict) -> str:
    if c["id"].startswith("V5"):
        return f'F{c["field"]}, colength 0..{c["colength_max"]}: brute force {c.get("bruteforce")} vs formula {c["formula"]}'
    if c["id"] == "V6":
        return f'F{c["field"]}, n ≤ {c["n_max"]}: partial {c["partial_sum"]} < limit {c["predicted_limit"]}'
    if c["id"] == "V2":
        return f'rank {c["rank"]}, deg F_N = {c["deg_F_N"]}, through q^{c["degree"]}'
    if c["id"] == "V4":
        return f'Cat = {c["catalan"]}, filters = {c["filters"]}, F_N(1) = {c["F_N(1)"]:,}'
    if c["id"] == "V1":
        return f'through q^{c["degree"]}'
    return ""


def _certificate_html() -> str:
    v5 = "".join(
        f'<tr><td>({r["pair"][0]},{r["pair"][1]})</td><td>{r["rank"]}</td><td>F{r["field"]}</td>'
        f'<td>{", ".join(f"{n:,}" for n in r["submodule_counts"])}</td></tr>'
        for r in CERT["V5"]
    )
    return (
        '<div class="card"><h3>Sealed finite certificate</h3>'
        f'<p>{len(CERT["pairs"])} coprime pairs with a + b ≤ 13: Z = P through q<sup>40</sup>; '
        f'{len(CERT["V2"])} finite-identity rows (ranks 1–3); published golden values reproduced. '
        'Brute-force census of R-submodules of F<sub>q</sub>[[T]]<sup>N</sup> by colength — every row '
        'equals HJO Theorem 1.2 at L = q:</p>'
        f'<table class="rel"><tr><th>(a,b)</th><th>rank N</th><th>field</th><th>colength 0, 1, 2, …</th></tr>{v5}</table>'
        f'<p class="note">Digest <code>{CERT["sha256"]}</code>. Replay: '
        '<code>python research/hjo_loom/build_certificate.py --check research/hjo_loom/hjo_certificate_v1.json</code></p></div>'
    )


# --------------------------------------------------------------------------
# Classic Proof Loom + Sequence Scout (unchanged behaviour)
# --------------------------------------------------------------------------

PREVIEW, INTRO = panel(18, 'RR1', '2,3')
ARTIFACT_DIR = str(Path(PREVIEW).parent)

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


# --------------------------------------------------------------------------
# Presentation
# --------------------------------------------------------------------------

STYLE = """
:root { color-scheme: dark; }
body, .gradio-container { background: #070b16 !important; color: #e9efff !important; }
.gradio-container { max-width: 1360px !important; margin: auto; }
.proof-head { padding: clamp(20px, 5vw, 56px); border: 1px solid #2c4262; border-radius: 24px;
 background: radial-gradient(ellipse at 78% 0%, #123a55, transparent 60%),
 radial-gradient(ellipse at 10% 100%, #2a1d44, transparent 55%), #0b1222;
 box-shadow: inset 0 0 80px #00e5ff10, 0 0 40px #00e5ff08; }
.proof-kicker, .kicker { font: 600 12px/1.6 ui-monospace, monospace; letter-spacing: .14em; color: #70dbeb; }
.proof-title { font: 700 clamp(30px, 5vw, 64px)/1.04 system-ui; letter-spacing: -.05em; margin: 16px 0; color: #f2f6ff !important; }
.gradio-container .prose b, .gradio-container .prose strong, .gradio-container .prose sub,
.gradio-container .prose sup, .gradio-container .prose small { color: inherit !important; }
.card p, .card li { color: #c9d6e8 !important; }
.card h3 small { color: #8fa6c2 !important; }
button[role="tab"] { color: #b9c9de !important; }
button[role="tab"][aria-selected="true"] { color: #4fe3f0 !important; }
.proof-intro { color: #c5d4e5; max-width: 80ch; line-height: 1.65; }
.proof-chip, .chip { display: inline-block; border: 1px solid #3b5275; border-radius: 99px;
 padding: 6px 11px; margin: 8px 8px 0 0; font: 600 11px ui-monospace, monospace; color: #d6e6ff; }
.proof-pill { color:#ffd27b; border-color:#82642f; }
.proof-foot, .note { color: #b6c8df; font-size: 13px; line-height: 1.6; }
.banner { border: 1px solid #2f5a6d; border-radius: 20px; padding: 22px; margin: 6px 0 14px;
 background: linear-gradient(120deg, #0c2333, #0f1530 70%); }
.banner h2 { font: 700 clamp(20px, 2.6vw, 30px)/1.25 system-ui; margin: 10px 0; color: #eafcff; }
.banner p { color: #c3d3e6; line-height: 1.65; max-width: 95ch; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; margin-top: 12px; }
.stat { border: 1px solid #39506f; border-radius: 14px; padding: 12px; background: #0a1729; }
.stat-strong { border-color: #4fe3f0; box-shadow: 0 0 22px #4fe3f022; }
.stat b { display:block; font: 700 28px/1.2 ui-monospace, monospace; color: #c9fbff; }
.stat span, .stat em, .stat i { display:block; font-size: 12px; color: #bcd0e4; font-style: normal; }
.stat i { margin-top: 6px; font-weight: 700; letter-spacing: .08em; color: #ffd27b; }
.card { border: 1px solid #31445f; border-radius: 16px; padding: 16px; background: #0b1426; }
.card h3 { margin: 0 0 8px; color: #9ff6ec; }
.rel { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 10px; }
.rel th, .rel td { border-bottom: 1px solid #22344d; padding: 6px 8px; text-align: left; vertical-align: top; }
.rel th { color: #8fd9e8; font-weight: 600; }
.s-match, .s-consistent { color: #7ff5c8; font-weight: 700; }
.s-not_run_budget { color: #ffd27b; font-weight: 700; }
.flag { color: #ffb38a; font-size: 11px; border: 1px solid #7a4a32; border-radius: 6px; padding: 1px 5px; }
.ledger { border-left: 3px solid #6ff0e5; padding: 12px; background: #0b2634; font-size: 13px; }
.ledger table { width: 100%; font: 12px ui-monospace, monospace; margin-top: 8px; }
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
.people { display:grid; grid-template-columns: repeat(auto-fit,minmax(300px,1fr)); gap: 14px; }
.people li { margin: 6px 0; line-height: 1.5; color: #cbd9ea; }
a { color: #7fe7f4; }
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

HEADER = f"""
<section class="proof-head" aria-label="Khipu Proof Loom">
<div class="proof-kicker">SZL HOLDINGS / KHIPU PROOF LOOM / PURE-PYTHON EXACT RESEARCH LAB</div>
<h1 class="proof-title">Khipu <span style="color:#70f2e6">Proof Loom</span></h1>
<p class="proof-intro">Two kinds of knots, kept honestly apart. On the left bank: <b>real Inka-style
khipus</b> — 619 records from the Open Khipu Repository rebuilt as 3D digital twins, with every
exact decimal sum the cords encode found and tested against chance. On the right bank: the
<b>2026 torus-knot Rogers–Ramanujan theorems</b> for X<sup>a</sup> = Y<sup>b</sup>, replayed
exactly in integer arithmetic, down to counting submodules over finite fields one by one.
Every run is sealed into a hash-chained ledger.</p>
<span class="proof-chip">REAL ARCHAEOLOGICAL RECORDS</span>
<span class="proof-chip">EXACT INTEGER ARITHMETIC</span>
<span class="proof-chip">PERMUTATION NULL</span>
<span class="proof-chip proof-pill">NOT DECIPHERMENT</span>
<span class="proof-chip proof-pill">NO NEW THEOREM CLAIMED</span>
<span class="proof-chip" data-szl-source-sha="{SOURCE_SHA}" data-szl-manifest-sha256="{SOURCE_MANIFEST_SHA}">PINNED SOURCE {SOURCE_SHA[:12]}</span>
</section>
"""

PEOPLE = """
<div class="people">
<div class="card"><h3>Andean records and their scholars</h3><ul>
<li>The <b>khipukamayuq</b> — the Andean cord-keepers whose knots these are.</li>
<li><b>Leland L. Locke</b> (1912, 1923) — the decimal place-value reading of khipu knots.</li>
<li><b>Marcia &amp; Robert Ascher</b>, <i>Code of the Quipu</i> (1981) — the databook and the sum-cord relations tested here.</li>
<li><b>Open Khipu Repository</b> (MIT; <a href="https://doi.org/10.5281/zenodo.18025748">doi:10.5281/zenodo.18025748</a>), directed by <b>Mackinley FitzPatrick</b>;
Advisory Board <b>Carrie Brezine, Mackinley FitzPatrick, Iván Ghezzi, Sabine Hyland, Manuel Medrano, Jeffrey Splitstoser</b>; data contributors include the Aschers, <b>Gary Urton</b>, <b>Ashok Khosla</b> and <b>Jon Clindaniel</b>.</li>
<li><b>M. FitzPatrick</b>, “Knot Tricks: What Mathematical Knot Theory Can Reveal about the Structure of Khipu Knot Encoding”, <i>Latin American Antiquity</i> (2026), <a href="https://doi.org/10.1017/laq.2026.10171">doi:10.1017/laq.2026.10171</a>.</li>
<li><b>M. Medrano &amp; A. Khosla</b>, “How Can Data Science Contribute to Understanding the Khipu Code?”, <i>Latin American Antiquity</i> (2024), <a href="https://doi.org/10.1017/laq.2024.5">doi:10.1017/laq.2024.5</a>.</li>
</ul></div>
<div class="card"><h3>Partitions, knots and proof</h3><ul>
<li><b>L. J. Rogers</b> (1894) and <b>S. Ramanujan</b> — the Rogers–Ramanujan identities.</li>
<li><b>Basil Gordon</b> (1961) and <b>George E. Andrews</b> (1974) — the odd-modulus generalisations.</li>
<li><b>Yifeng Huang</b> (Emory), <b>Ruofan Jiang</b> (UC Berkeley), <b>Alexei Oblomkov</b> (UMass Amherst) — Quot schemes of torus-knot singularities and the HJO conjecture, <a href="https://arxiv.org/abs/2608.16086">arXiv:2608.16086</a>.</li>
<li><b>Y. Huang, K. Lau, K. Ono, P. Paule</b> — <a href="https://arxiv.org/abs/2608.15219">arXiv:2608.15219</a>; <b>K. Lau &amp; K. Ono</b> — the a = 3 layer, <a href="https://arxiv.org/abs/2608.05480">arXiv:2608.05480</a>.</li>
<li><b>Yifeng Huang, Kenny Lau, Ken Ono</b> — proof of the HJO conjecture for all coprime 1 &lt; a &lt; b, <a href="https://arxiv.org/abs/2609.20567">arXiv:2609.20567</a>, Lean-formalized by AxiomProver (<a href="https://github.com/AxiomMath/HJO">AxiomMath/HJO</a>, not replayed here).</li>
<li><b>K. Lau, S. Lee, K. Ono</b> — formalized q-series in Lean, <a href="https://arxiv.org/abs/2607.01544">arXiv:2607.01544</a>.</li>
</ul></div></div>
<p class="note">The torus knots of the mathematics are algebraic objects; the knots on a khipu are
physical records. This lab studies both rigorously and asserts no historical link between them.</p>
"""

SYSTEM_FONTS = ["system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"]
MONO_FONTS = ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"]
_DARK = {
    "body_background_fill": "#070b16", "body_text_color": "#e9efff",
    "body_text_color_subdued": "#b6c8df", "background_fill_primary": "#0b1426",
    "background_fill_secondary": "#0a1220", "border_color_primary": "#2c4262",
    "block_background_fill": "#0b1426", "block_border_color": "#2c4262",
    "block_label_background_fill": "#0f1d33", "block_label_text_color": "#bcd0e4",
    "block_title_text_color": "#d6e6ff", "block_info_text_color": "#b6c8df",
    "input_background_fill": "#0a1729", "input_border_color": "#39506f",
    "input_placeholder_color": "#8ea3bd", "checkbox_background_color": "#0a1729",
    "checkbox_border_color": "#4a6488", "checkbox_label_text_color": "#d6e6ff",
    "button_primary_background_fill": "#1fb6c9", "button_primary_background_fill_hover": "#3ccfe0",
    "button_primary_text_color": "#03121b", "button_secondary_background_fill": "#13243a",
    "button_secondary_text_color": "#d6e6ff", "color_accent": "#4fe3f0",
    "color_accent_soft": "#123a55", "link_text_color": "#7fe7f4",
    "table_even_background_fill": "#0b1426", "table_odd_background_fill": "#0a1220",
}
_THEME_VARS = set(inspect.signature(gr.themes.Base.set).parameters)
THEME = gr.themes.Base(
    primary_hue=gr.themes.colors.cyan, neutral_hue=gr.themes.colors.slate,
    font=SYSTEM_FONTS, font_mono=MONO_FONTS,
).set(**{k: v for k, v in _DARK.items() if k in _THEME_VARS},
      **{k + "_dark": v for k, v in _DARK.items() if k + "_dark" in _THEME_VARS})

# Delete old Gradio-generated request files after two hours, checking hourly.
with gr.Blocks(
    title='Khipu Proof Loom', analytics_enabled=False,
    delete_cache=(3600, 7200),
) as demo:
    gr.HTML(HEADER)
    ledger_state = gr.State(UnifiedReceiptChain())
    with gr.Tabs():
        with gr.Tab("Ancestral arithmetic · real khipus"):
            gr.HTML(_corpus_banner())
            with gr.Row():
                khipu_pick = gr.Dropdown(KHIPU_CHOICES, value=DEFAULT_KHIPU,
                                         label="Khipu (ranked by sum relations above chance)")
                khipu_r3 = gr.Checkbox(value=False, label="Also draw R3 arcs (chance-level type)")
            khipu_go = gr.Button("Rebuild 3D twin and re-find exact sums", variant="primary")
            khipu_init_path, khipu_init_html = _khipu_render(DEFAULT_KHIPU, ("R1", "R2", "R4"))
            khipu_model = gr.Model3D(
                value=khipu_init_path, interactive=False, display_mode="solid",
                clear_color=(.02, .035, .07, 1), camera_position=(90, 75, 14),
                height=600, label="Digital twin from OKR measurements · glowing arcs = exact sums",
            )
            khipu_card = gr.HTML(khipu_init_html)
        with gr.Tab("HJO Loom · X^a = Y^b"):
            gr.HTML('<p class="proof-intro">Pick a torus-knot singularity. The engine rebuilds the '
                    'gap poset, the quadratic form and the cylindric-partition profile from the '
                    'paper\'s definitions, then checks Z = P, the finite identity F<sub>N</sub> = '
                    '(q;q)<sub>N</sub>C<sub>c,≤N</sub>, the rational-Catalan filter count, and '
                    'counts R-submodules of F<sub>q</sub>[[T]]<sup>N</sup> by brute force against '
                    'the HJO motive formula.</p>')
            with gr.Row():
                hjo_pair = gr.Dropdown(HJO_PAIRS, value="4,5", label="(a, b) coprime, a + b ≤ 11")
                hjo_rank = gr.Radio([1, 2], value=2, label="Rank N")
                hjo_field = gr.Radio([2, 3], value=2, label="Finite field F_q")
            hjo_go = gr.Button("Run exact checks and render 3D", variant="primary")
            hjo_model = gr.Model3D(
                interactive=False, display_mode="solid", clear_color=(.02, .035, .07, 1),
                camera_position=(90, 82, 17), height=560,
                label="Torus knot T(a,b) · gap-poset lattice · a cylindric partition",
            )
            hjo_out = gr.HTML('<p class="note">Press run. Larger pairs take several seconds on CPU.</p>')
            gr.HTML(_certificate_html())
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
                    cyl_a = gr.Slider(2, 4, value=3, step=1, label='Coprime torus parameter a')
                    cyl_b = gr.Slider(3, 9, value=5, step=1, label='Coprime torus parameter b')
                with gr.Row():
                    cyl_rank = gr.Slider(0, 3, value=2, step=1, label='Maximum entry N')
                    cyl_degree = gr.Slider(0, 8, value=6, step=1, label='Truncated volume degree')
                cyl_result = gr.HTML(
                    '<section class="scout"><h3>NOT EVALUATED</h3>'
                    '<p>Select a coprime pair with 1&lt;a&lt;b and click Run. '
                    'No enumeration starts on page load.</p></section>'
                )
                cyl_receipt = gr.JSON(
                    value={"status": "NOT_EVALUATED", "HJO_equality_verified_here": False},
                    label="Pinned definition-level finite evidence (unsigned)",
                )
                cyl_button = gr.Button('Run exact finite cylindric enumeration', variant='secondary')
                cyl_button.click(
                    hjo_profile_panel,
                    inputs=[cyl_a, cyl_b, cyl_rank, cyl_degree],
                    outputs=[cyl_result, cyl_receipt],
                    api_name='hjo_profile', concurrency_limit=1,
                    concurrency_id='proof-loom-cpu', trigger_mode='once',
                )
        with gr.Tab("Classic Proof Loom"):
            with gr.Row():
                degree = gr.Slider(0, 128, step=1, value=18, label='Coefficient degree n')
                identity = gr.Radio(['RR1', 'RR2'], value='RR1', label='Classical partition identity')
                curve = gr.Dropdown(['2,3', '3,4', '3,5', '3,7'], value='2,3', label='Mathematical torus knot (a,b)')
            model = gr.Model3D(
                value=PREVIEW, interactive=False, display_mode='solid',
                clear_color=(.035, .05, .085, 1), camera_position=(0, .4, 12),
                height=520, label='3D mathematical torus knot | separate modern cord sketch',
            )
            receipt = gr.HTML(INTRO)
            go = gr.Button('Recompute exact witness and 3D diagram', variant='primary')
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
        with gr.Tab("Ledger"):
            ledger_view = gr.HTML(_ledger_html(UnifiedReceiptChain()))
        with gr.Tab("Scholars & sources"):
            gr.HTML(PEOPLE)
    gr.HTML('<p class="proof-foot">Data: Open Khipu Repository @ 4039ca51f4de, MIT licence '
            '(LICENSE-OKR.txt). Mathematics: arXiv:2609.20567 and arXiv:2608.16086. No neural or '
            'language model is trained or queried. Green finite checks are not infinite proofs, '
            'statistical structure is not decipherment, and digests are not signatures.</p>')

    khipu_go.click(
        khipu_panel, inputs=[khipu_pick, khipu_r3, ledger_state],
        outputs=[khipu_model, khipu_card, ledger_state, ledger_view], api_name='khipu',
        concurrency_limit=1, concurrency_id='proof-loom-cpu', trigger_mode='once',
    )
    hjo_go.click(
        hjo_panel, inputs=[hjo_pair, hjo_rank, hjo_field, ledger_state],
        outputs=[hjo_model, hjo_out, ledger_state, ledger_view], api_name='hjo',
        concurrency_limit=1, concurrency_id='proof-loom-cpu', trigger_mode='once',
    )
    go.click(
        panel, inputs=[degree, identity, curve], outputs=[model, receipt],
        api_name='recompute', concurrency_limit=1, concurrency_id='proof-loom-cpu',
        trigger_mode='once',
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

# One shared CPU lane for every expensive callback; bounded public queue.
demo.queue(max_size=32, default_concurrency_limit=1)


LAUNCH_KWARGS = {
    "css": STYLE, "theme": THEME, "show_error": False, "share": False,
    "allowed_paths": [ARTIFACT_DIR, str(SCENE_DIR)],
}


def launch():
    return demo.launch(server_name='0.0.0.0', server_port=int(os.getenv('PORT', '7860')),
                       **LAUNCH_KWARGS)


if __name__ == '__main__':
    launch()
