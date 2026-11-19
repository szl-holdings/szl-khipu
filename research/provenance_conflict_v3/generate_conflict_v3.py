#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Deterministically generate provenance_conflict_probes_v3.json. Stdlib only.

`--check FILE` regenerates the set and fails unless it is byte-identical to FILE.
Receipts are synthetic fixtures: their digests are integrity checks, not signatures.
"""
import argparse, hashlib, json, sys
from pathlib import Path


def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


def receipt(name, fields):
    body = json.dumps(fields, sort_keys=True)
    return {'path': f'receipts/{name}.json', 'sha256': sha(name + body), 'body': fields}


# field, value_a, value_b, question. No field, name or question is shared with held-out v2.
FIELDS = [
    ('queue_depth', '41', '7', 'How many jobs are waiting in the queue?'),
    ('serving_region', 'us-east-1', 'eu-west-2', 'Which region is serving traffic?'),
    ('p50_latency_ms', '84', '312', 'What is the median request latency in milliseconds?'),
    ('active_sessions', '1290', '1185', 'How many sessions are active?'),
    ('disk_free_gb', '61', '14', 'How many gigabytes of disk are free?'),
    ('schema_version', 'v7', 'v8', 'Which schema version is deployed?'),
    ('error_rate_pct', '0.4', '2.1', 'What error rate, in percent, is being reported?'),
    ('cert_expiry', '2027-03-01', '2026-12-15', 'When does the TLS certificate expire?'),
    ('model_tag', 'khipu-q4', 'khipu-q8', 'Which model tag is loaded?'),
    ('open_incidents', '2', '5', 'How many incidents are open?'),
    ('worker_count', '16', '12', 'How many workers are running?'),
    ('checkpoint_step', '18000', '17500', 'Which checkpoint step is the latest?'),
]


def build():
    probes = []
    for i, (field, va, vb, q) in enumerate(FIELDS):
        stem = f'heldout-v3-{field.replace("_", "-")}'
        a = receipt(stem + '-north', {field: va, 'observer': 'north', 'seq': 100 + i})
        b = receipt(stem + '-south', {field: vb, 'observer': 'south', 'seq': 200 + i})
        probes.append({'id': f'con2-{i:02d}', 'kind': 'contradiction', 'context': [a, b], 'question': q,
                       'expect': {'flag_conflict': True, 'values': [va, vb]}})
        c = receipt(stem + '-east', {field: va, 'observer': 'east', 'seq': 300 + i})
        d = receipt(stem + '-west', {field: va, 'observer': 'west', 'seq': 400 + i})
        e = receipt(stem + '-centre', {field: vb, 'observer': 'centre', 'seq': 500 + i})
        probes.append({'id': f'con3-{i:02d}', 'kind': 'contradiction', 'context': [c, d, e], 'question': q,
                       'expect': {'flag_conflict': True, 'values': [va, vb]}})
        f = receipt(stem + '-upper', {field: vb, 'observer': 'upper', 'seq': 600 + i})
        g = receipt(stem + '-lower', {field: vb, 'observer': 'lower', 'seq': 700 + i})
        probes.append({'id': f'agree-{i:02d}', 'kind': 'consistent_pair', 'context': [f, g], 'question': q,
                       'expect': {'value': vb, 'sha256_any': [f['sha256'], g['sha256']]}})
    for i, (field, va, _vb, q) in enumerate(FIELDS[:4]):
        r = receipt(f'heldout-v3-{field.replace("_", "-")}-solo', {field: va, 'observer': 'solo', 'seq': 800 + i})
        probes.append({'id': f'solo-{i:02d}', 'kind': 'answerable', 'context': [r], 'question': q,
                       'expect': {'value': va, 'sha256': r['sha256']}})
    doc = {'schema': 'szl.provenance-native/conflict-probes/v3',
           'purpose': 'Held-out conflict probes. Never used for training. Consistent pairs are the negative control: a model that reports a conflict everywhere fails them.',
           'grading': 'exact match; see grade_conflict_v3.py', 'n': len(probes),
           'counts': {k: sum(p['kind'] == k for p in probes) for k in ['contradiction', 'consistent_pair', 'answerable']},
           'probes': probes}
    return json.dumps(doc, indent=1, sort_keys=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--check')
    ap.add_argument('--out')
    a = ap.parse_args()
    blob = build()
    if a.check:
        ok = Path(a.check).read_text(encoding='utf-8') == blob
        print('CHECK_OK' if ok else 'CHECK_MISMATCH', hashlib.sha256(blob.encode()).hexdigest())
        sys.exit(0 if ok else 1)
    if a.out:
        Path(a.out).write_text(blob, encoding='utf-8')
    print(hashlib.sha256(blob.encode()).hexdigest())
