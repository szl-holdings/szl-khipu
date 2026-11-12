#!/usr/bin/env python3
"""Dependency consistency for the Gradio CI lock.

``pip check`` is the gate. Gradio 6.31.0 still declares ``pillow<13.0,>=8.0``,
and Pillow 13.0.0 is the earliest release that fixes GHSA-8g5g-8vmr-9782
(CVE-2026-112403; affected versions ``<= 12.3.0``) along with the other Pillow
advisories that still include 12.3.0. gradio-app/gradio#14034 widens that bound
to ``pillow<14`` and is not in a PyPI release yet. This demo does not encode
32-bit integer PNGs, which is the behavior that patch also preserves.

A clean ``pip check`` passes. The single finding below also passes. Anything
else fails.
"""

from __future__ import annotations

import subprocess
import sys

ALLOWED = (
    "gradio 6.31.0 has requirement pillow<13.0,>=8.0, but you have pillow 13.0.0."
)


def unexpected(report: str, returncode: int) -> list[str]:
    """Lines from ``pip check`` that are not the known Gradio metadata bound."""
    lines = [line.strip() for line in report.splitlines() if line.strip()]
    if returncode == 0:
        return lines
    extra = [line for line in lines if line != ALLOWED]
    if extra:
        return extra
    if lines == [ALLOWED]:
        return []
    return ["pip check failed without a recognized dependency report"]


def main() -> int:
    proc = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        check=False,
        capture_output=True,
        text=True,
    )
    report = f"{proc.stdout}{proc.stderr}"
    problems = unexpected(report, proc.returncode)
    if problems:
        print("dependency consistency failed:", file=sys.stderr)
        if report.strip():
            print(report.strip(), file=sys.stderr)
        for problem in problems:
            if problem not in report:
                print(problem, file=sys.stderr)
        return 1
    if proc.returncode == 0:
        print("pip check: ok")
    else:
        print(f"pip check: allowed the known Gradio 6.31.0 bound ({ALLOWED})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
