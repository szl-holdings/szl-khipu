#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
# Signed-off-by: Lutar, Stephen P. <stephenlutar2@gmail.com>
"""Energy probe. Channel is always LIVE. Joules MEASURED only from RAPL or NVML."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

POWERCAP = Path("/sys/class/powercap")
RAPL = Path("/sys/class/powercap/intel-rapl:0/energy_uj")


def _rapl_uj() -> int | None:
    candidates: list[Path] = [RAPL]
    try:
        if POWERCAP.is_dir():
            candidates.extend(sorted(POWERCAP.glob("intel-rapl:*/energy_uj")))
            candidates.extend(sorted(POWERCAP.glob("intel-rapl:*:*/energy_uj")))
    except OSError:
        pass
    seen: set[Path] = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        try:
            if path.is_file():
                return int(path.read_text().strip())
        except (OSError, ValueError):
            continue
    return None


def _pynvml_importable() -> bool:
    try:
        import pynvml  # noqa: F401

        return True
    except ImportError:
        return False


def _nvml_mj() -> float | None:
    try:
        import pynvml  # type: ignore
    except ImportError:
        return None
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        mj = float(pynvml.nvmlDeviceGetTotalEnergyConsumption(handle))
        pynvml.nvmlShutdown()
        return mj
    except Exception:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass
        return None


def hardware() -> dict[str, Any]:
    """Inventory only. Never a joule. RAPL/NVML readable ⇒ a later probe can MEASURE."""
    rapl = _rapl_uj()
    nv = _nvml_mj()
    return {
        "powercap_dir": POWERCAP.is_dir(),
        "rapl_readable": rapl is not None,
        "rapl_uj": rapl,
        "pynvml_import": _pynvml_importable(),
        "nvml_readable": nv is not None,
        "nvml_mj": nv,
    }


def _unavailable(note: str) -> dict[str, Any]:
    return {
        "channel": "LIVE",
        "honesty": "UNAVAILABLE",
        "source": None,
        "package_energy_j": None,
        "sample_delta_j": None,
        "inference_energy_j": None,
        "energy_j": None,
        "hardware": hardware(),
        "note": note,
    }


def probe(*, sample_s: float = 0.05) -> dict[str, Any]:
    """Return MEASURED package energy if hardware exists, else UNAVAILABLE.

    The probe channel is always LIVE. A RAPL counter is package energy, not
    tokens/joule. Inference joules are only MEASURED when a kernel run is
    wrapped in a RAPL/NVML delta. Never a fabricated joule.
    """
    a = _rapl_uj()
    if a is not None:
        time.sleep(max(0.0, sample_s))
        b = _rapl_uj()
        if b is None:
            b = a
        delta_j = max(0.0, (b - a) / 1_000_000.0)
        return {
            "channel": "LIVE",
            "honesty": "MEASURED",
            "source": "intel-rapl",
            "package_energy_j": b / 1_000_000.0,
            "sample_delta_j": delta_j,
            "inference_energy_j": None,
            "energy_j": None,
            "hardware": hardware(),
            "note": "RAPL package counter MEASURED. Inference joule still None until a kernel is wrapped.",
        }
    mj = _nvml_mj()
    if mj is not None:
        return {
            "channel": "LIVE",
            "honesty": "MEASURED",
            "source": "nvml",
            "package_energy_j": mj / 1000.0,
            "sample_delta_j": None,
            "inference_energy_j": None,
            "energy_j": None,
            "hardware": hardware(),
            "note": "NVML total energy MEASURED. Inference joule still None until a kernel is wrapped.",
        }
    return _unavailable("No RAPL, no NVML. Channel is live. Never a fabricated joule.")


def measure_run(fn):
    """Wrap a kernel. If RAPL/NVML exists, inference_energy_j is MEASURED."""
    a = _rapl_uj()
    nv_a = _nvml_mj()
    t0 = time.perf_counter()
    result = fn()
    dt = time.perf_counter() - t0
    b = _rapl_uj()
    nv_b = _nvml_mj()
    energy = probe(sample_s=0.0)
    energy["channel"] = "LIVE"
    energy["duration_s"] = dt
    if a is not None and b is not None:
        energy["honesty"] = "MEASURED"
        energy["source"] = "intel-rapl"
        energy["inference_energy_j"] = max(0.0, (b - a) / 1_000_000.0)
        energy["energy_j"] = energy["inference_energy_j"]
        energy["note"] = f"RAPL delta around kernel · {dt:.4f}s"
    elif nv_a is not None and nv_b is not None:
        energy["honesty"] = "MEASURED"
        energy["source"] = "nvml"
        energy["inference_energy_j"] = max(0.0, (nv_b - nv_a) / 1000.0)
        energy["energy_j"] = energy["inference_energy_j"]
        energy["note"] = f"NVML delta around kernel · {dt:.4f}s"
    return result, energy


if __name__ == "__main__":
    print(json.dumps({"probe": probe(), "hardware": hardware()}, indent=2))
