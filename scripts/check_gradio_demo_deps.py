#!/usr/bin/env python3
"""Fail closed on any dependency inconsistency in the Gradio 6.32 locked demo.

Gradio 6.32.0 supports Pillow 13.0.0, so the previous one-line temporary
incompatibility exception is no longer necessary or permitted. This check
does not imply Hugging Face production deployment or browser admission.
"""
from __future__ import annotations
import subprocess
import sys

CLEAN = "No broken requirements found."

def unexpected(report: str, returncode: int) -> list[str]:
    lines = [line.strip() for line in report.splitlines() if line.strip()]
    if returncode == 0:
        return [line for line in lines if line != CLEAN]
    return lines or ["pip check returned a nonzero exit without a diagnostic"]

def main() -> int:
    proc = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        capture_output=True, text=True, check=False,
    )
    report = f"{proc.stdout}{proc.stderr}"
    problems = unexpected(report, proc.returncode)
    if problems:
        print("dependency consistency failed:", file=sys.stderr)
        if report.strip():
            print(report.strip(), file=sys.stderr)
        for message in problems:
            if message not in report:
                print(message, file=sys.stderr)
        return 1
    print("pip check: clean")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
