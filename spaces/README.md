---
title: SZL KHIPU
emoji: 🪢
colorFrom: gray
colorTo: green
sdk: gradio
sdk_version: 6.31.0
python_version: "3.11"
app_file: app.py
pinned: true
license: apache-2.0
short_description: Knot the run. Hash the proof. Fail closed.
---

# SZL KHIPU

Knot the run. Hash the proof. Fail closed.

Holographic Gradio 6 demo for the `szl-khipu` package **on GitHub**. The separate Docker publisher uses `../space/` (stdlib HTTP, no Gradio); this demo is not a request to create or replace a Hub Space. Chrome is SZL KANCHAY (founder direction), vendored byte-for-byte in `szl_khipu/szl/`: space-navy ground `--bg`, one coral primary `--accent` per tab, status as worded chips, receipts as `.receipt`. Kernels are live NumPy. Not default Gradio orange. YAML `emoji` is Hub metadata, not product chrome. System fonts. No Google Fonts.

From the repository root, install and run the pinned demo in a virtual environment:

```sh
python -m pip install -e ".[test,gradio]" -r spaces/requirements.txt
python -m pip check
python -m unittest discover -s tests -p gradio_runtime.py -v
python spaces/app.py
```

The dedicated CI smoke test imports the real SDK, starts a loopback server, checks its configuration, and calls the live NumPy callbacks through the Gradio client. It never downloads models or enables a public sharing tunnel. This local demo test is not evidence of a deployed Hub runtime.

CI installs the same set from the hash-locked `requirements/ci/gradio-demo.txt` (`pip install --require-hashes`, then `pip install --no-deps -e .`). When the Gradio pin in `requirements.txt` changes, also update `sdk_version` above and the version assertion in `tests/gradio_runtime.py`, and regenerate the lock; `tests/test_ci_requirements.py` fails until the lock carries the pinned Gradio:

```sh
uv pip compile requirements/ci/gradio-demo.in --universal --python-version 3.11 --generate-hashes -o requirements/ci/gradio-demo.txt
```

**Conjecture 1 OPEN. energy UNAVAILABLE. proven_trust=false.** CPU numpy LIVE. CUDA UNAVAILABLE. Not Qwen. Not 1.5B. Not a FlashAttention rehost.

| Tab | What you get | What you do not get |
|---|---|---|
| Λ gate | score + blocked on 13 sliders | proven trust, a Λ uniqueness theorem (Conjecture 1 stays open) |
| YARQA | `n_canals` + leaked | SageAttention, CUDA cubins, tokens/s |
| TinyKhipu | plan-valid / abstain / hallucinated | 1.5B, Qwen, GGUF |
| Moons | acc / loss on 2→8→2 | 1.5B, published benchmark |
| MiniEmbed | V=64 d=12 L2 table | neural embed, 3290×128 table |
| Anatomy | 5 organs LIVE or fail-closed | 3D Three.js rehost, joules, proven trust |
| Receipts | last chain depth | joules, authorship |

Gold means OPEN. Proof teal means LIVE. Never green-as-proven. Never a fabricated joule.

Source: [szl-holdings/szl-khipu](https://github.com/szl-holdings/szl-khipu) · Hub: [SZLHOLDINGS/szl-khipu](https://huggingface.co/SZLHOLDINGS/szl-khipu) · hologram language from the retired `lambda-gate-holo` Space (deleted 2026-09-04; the Λ kernel lives in [szl-holdings/szl-lambda-gate](https://github.com/szl-holdings/szl-lambda-gate))

Apache-2.0. Copyright 2026 SZL Holdings. Doctrine v11 LOCKED · 749/14/163.
