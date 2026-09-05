# KHIPU-X1

**FPGA-first governed LLM accelerator reference.**

This directory is a software reference and future hardware workspace. It is not a fabricated chip and does not claim performance superiority.

Wave 1 implements:

- KIDS v0.1 logical descriptor draft;
- deterministic NumPy simulator;
- INT8 GEMM, RMSNorm and SHA3 commitments;
- ordered execution-receipt chains;
- explicit fail-closed handling for replay, reserved operations and abort;
- conformance tests.

Current hardware status: **UNAVAILABLE — target FPGA not selected**.

## Quick start

```bash
cd hardware/khipu-x1
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest -q
```

## Truth labels

- `SCAFFOLDED`: interface or design document exists.
- `SOFTWARE_EMULATED`: reference code executed on CPU.
- `FPGA_MEASURED`: allowed only after an exact device and bitstream are tested.
- `BLOCKED`: attempted path was refused with evidence.
- `UNAVAILABLE`: capability does not exist or was not measured.

## Program boundary

This is for one owner prototype. No production tooling, mass-production order or ASIC tapeout is authorized by this directory.

## Next waves

1. compiler/reference graph lowering;
2. safe `.khipu` package format;
3. RC1 authorization emulator and firmware contract;
4. FPGA target selection and binary KIDS ABI;
5. RTL, driver and measured-device conformance.
