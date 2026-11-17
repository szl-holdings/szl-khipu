# SPDX-License-Identifier: Apache-2.0
"""Bounded offline advisory comparison, never a production admission gate."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path

from .cord_witness import CordError, canonical, compare_committed, load_record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--expected-reference-sha256', required=True)
    parser.add_argument('--challenge', type=int, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        a = load_record(args.reference)
        b = load_record(args.candidate)
        result = compare_committed(a, b,
                    expected_reference_sha256=args.expected_reference_sha256,
                    challenge=args.challenge)
        receipt = {'schema': 'szl.khipu-offline-audit-receipt/v1',
                   'observed_utc': datetime.now(timezone.utc).isoformat(),
                   'reference_input_sha256': sha256(args.reference.read_bytes()).hexdigest(),
                   'candidate_input_sha256': sha256(args.candidate.read_bytes()).hexdigest(),
                   'comparison': result,
                   'publication': 'PRIVATE_RESEARCH_ONLY',
                   'source_rights_independently_checked': False,
                   'training_authority': 'NONE',
                   'deployment_qualified': False}
        data = canonical(receipt)
        if not args.out.parent.is_dir():
            raise CordError('output directory does not exist')
        with args.out.open('xb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        print(json.dumps({'state': result['state'], 'receipt_sha256': sha256(data).hexdigest(),
                          'authority': 'NONE'}, sort_keys=True))
        return 0 if result['state'] == 'RECONCILED_FIXED_REFERENCE' else 3
    except (CordError, OSError, UnicodeError, OverflowError):
        print(json.dumps({'state': 'UNAVAILABLE', 'reason': 'INPUT_OR_OUTPUT_CONTRACT_FAILED',
                          'authority': 'NONE'}, sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
