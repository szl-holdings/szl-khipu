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

CI installs the same set from the hash-locked `requirements/ci/gradio-demo.txt` (`pip install --require-hashes -r requirements/ci/gradio-demo.txt --no-deps`, then `pip install --no-deps -e .`). That lock pins Pillow 13.0.0, the earliest release that fixes GHSA-8g5g-8vmr-9782. Gradio 6.31.0 still declares `pillow<13`, so a resolving install stops at 12.3.0; `--no-deps` installs the hashed pins, and `scripts/check_gradio_demo_deps.py` allows only that one `pip check` finding. The plain extra install above still resolves Pillow 12.3.0 until a Gradio release widens the bound. When the Gradio pin in `requirements.txt` changes, also update `sdk_version` above and the version assertion in `tests/gradio_runtime.py`, and regenerate the lock; `tests/test_ci_requirements.py` fails until the lock carries the pinned Gradio:

```sh
uv pip compile requirements/ci/gradio-demo.in --universal --python-version 3.11 --generate-hashes --overrides requirements/ci/pillow-security-override.txt -o requirements/ci/gradio-demo.txt
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
