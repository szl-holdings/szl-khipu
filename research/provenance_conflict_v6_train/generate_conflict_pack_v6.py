#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Deterministically generate the v6 conflict-handling SFT pack. Stdlib only.

Training data only. It shares no field, receipt path, observer label or question text
with the held-out v2 or conflict v3 probe sets; `--check-disjoint` verifies that against
the frozen probe files and fails otherwise. `--check FILE` must reproduce FILE byte for byte.
Receipts are synthetic fixtures: digests are integrity checks, not signatures.
"""
import argparse, hashlib, json, sys
from pathlib import Path

SYSTEM = ('You are a provenance-native assistant of the SZL governed-AI estate. Rules: (1) Cite the exact receipt '
          '(path + sha256) that grounds every factual claim about measured estate state; end grounded answers with a '
          '<provenance> block. (2) If no receipt grounds a claim, say so plainly and abstain from the claim - never '
          'invent evidence. (3) A receipt proves only what it records; never inflate its scope. (4) Benchmarks: state '
          '"no benchmark recorded" unless a receipt records one.')
LABELS = ['alpha', 'bravo', 'charlie', 'delta', 'echo']
# field, value_x, value_y, three question phrasings
FIELDS = [
    ('cache_hit_pct', '93', '71', ['What cache hit rate is recorded?', 'Report the cache hit percentage.', 'How often does the cache hit, in percent?']),
    ('gpu_temp_c', '64', '81', ['What GPU temperature is recorded?', 'How hot is the GPU, in Celsius?', 'Report the GPU temperature reading.']),
    ('build_minutes', '22', '37', ['How long did the build take, in minutes?', 'Report the build duration.', 'What build time is recorded?']),
    ('pending_reviews', '3', '9', ['How many reviews are pending?', 'Report the pending review count.', 'What number of reviews await action?']),
    ('shard_count', '8', '6', ['How many shards are configured?', 'Report the shard count.', 'What shard total is recorded?']),
    ('retry_budget', '5', '2', ['What retry budget is set?', 'Report the retry budget.', 'How many retries are allowed?']),
    ('index_version', 'idx-14', 'idx-15', ['Which index version is live?', 'Report the index version.', 'What index build is in use?']),
    ('backup_age_h', '6', '30', ['How old is the latest backup, in hours?', 'Report the backup age.', 'What backup age is recorded?']),
    ('license_tier', 'team', 'enterprise', ['Which license tier applies?', 'Report the license tier.', 'What licence level is recorded?']),
    ('replication_lag_s', '4', '19', ['What replication lag is recorded, in seconds?', 'Report the replication lag.', 'How far behind is the replica?']),
    ('node_pool', 'pool-a', 'pool-c', ['Which node pool is serving?', 'Report the active node pool.', 'What node pool is recorded?']),
    ('dns_ttl_s', '300', '60', ['What DNS TTL is set, in seconds?', 'Report the DNS TTL.', 'How long do DNS answers live?']),
    ('alert_level', 'amber', 'red', ['What alert level is raised?', 'Report the alert level.', 'Which alert colour is recorded?']),
    ('api_version', '2026-09', '2026-11', ['Which API version is served?', 'Report the API version.', 'What API release is recorded?']),
    ('pool_size', '32', '24', ['What connection pool size is set?', 'Report the pool size.', 'How many pooled connections are recorded?']),
    ('artifact_mb', '412', '388', ['How large is the artifact, in megabytes?', 'Report the artifact size.', 'What artifact size is recorded?']),
    ('cron_window', '02:00', '03:30', ['When does the maintenance window start?', 'Report the cron window.', 'What start time is recorded for maintenance?']),
    ('feature_flag', 'on', 'off', ['Is the feature flag on or off?', 'Report the feature flag state.', 'What flag state is recorded?']),
    ('rotation_days', '30', '90', ['How often are keys rotated, in days?', 'Report the rotation interval.', 'What rotation period is recorded?']),
    ('quota_used_pct', '58', '97', ['How much quota is used, in percent?', 'Report the quota usage.', 'What quota consumption is recorded?']),
]


def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


def receipt(name, fields):
    body = json.dumps(fields, sort_keys=True)
    return {'path': f'receipts/{name}.json', 'sha256': sha(name + body), 'body': fields}


def context(rs):
    return 'Receipts in front of you:\n' + '\n'.join(
        f"- path: {r['path']}\n  sha256: {r['sha256']}\n  body: {json.dumps(r['body'], sort_keys=True)}" for r in rs)


def prov(rs):
    return '<provenance>\n' + '\n'.join(f"- {r['path']} sha256 {r['sha256']}" for r in rs) + '\n</provenance>'


def ex(user, assistant):
    return {'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': user},
                         {'role': 'assistant', 'content': assistant}]}


def build():
    rows = []
    for fi, (field, x, y, questions) in enumerate(FIELDS):
        stem = 'train-v6-' + field.replace('_', '-')
        for qi, q in enumerate(questions):
            la, lb, lc = LABELS[qi % 5], LABELS[(qi + 1) % 5], LABELS[(qi + 2) % 5]
            a = receipt(f'{stem}-{la}-{qi}', {field: x, 'observer': la, 'seq': 1000 + 10 * fi + qi})
            b = receipt(f'{stem}-{lb}-{qi}', {field: y, 'observer': lb, 'seq': 2000 + 10 * fi + qi})
            rows.append(ex(context([a, b]) + '\n\nQuestion: ' + q,
                           f"The receipts conflict. {a['path']} (sha256 {a['sha256']}) records {field} = {x}; "
                           f"{b['path']} (sha256 {b['sha256']}) records {field} = {y}. Neither receipt overrides the other, "
                           f"so I will not pick one value; the conflict is unresolved.\n{prov([a, b])}"))
            c = receipt(f'{stem}-{lc}-{qi}', {field: x, 'observer': lc, 'seq': 3000 + 10 * fi + qi})
            rows.append(ex(context([a, c, b]) + '\n\nQuestion: ' + q,
                           f"The receipts disagree. {a['path']} and {c['path']} record {field} = {x}; "
                           f"{b['path']} records {field} = {y}. Agreement between two receipts does not settle it, "
                           f"so I report the conflict rather than a single value.\n{prov([a, c, b])}"))
            d = receipt(f'{stem}-{la}-agree-{qi}', {field: y, 'observer': la, 'seq': 4000 + 10 * fi + qi})
            e = receipt(f'{stem}-{lb}-agree-{qi}', {field: y, 'observer': lb, 'seq': 5000 + 10 * fi + qi})
            rows.append(ex(context([d, e]) + '\n\nQuestion: ' + q,
                           f"Both receipts record {field} = {y}, and they agree. "
                           f"Per {d['path']} (sha256 {d['sha256']}), {field} is {y}.\n{prov([d, e])}"))
            if qi == 0:
                s = receipt(f'{stem}-solo', {field: x, 'observer': 'solo', 'seq': 6000 + fi})
                rows.append(ex(context([s]) + '\n\nQuestion: ' + q,
                               f"Per {s['path']} (sha256 {s['sha256']}), {field} is {x}.\n{prov([s])}"))
    return '\n'.join(json.dumps(r, sort_keys=True) for r in rows) + '\n'


def check_disjoint(research):
    v2 = json.loads((research / 'provenance_heldout_v2' / 'provenance_heldout_probes_v2.json').read_text(encoding='utf-8'))['probes']
    v3 = json.loads((research / 'provenance_conflict_v3' / 'provenance_conflict_probes_v3.json').read_text(encoding='utf-8'))['probes']
    held = v2 + v3
    held_q = {p['question'].lower() for p in held}
    held_paths = {r['path'] for p in held for r in p['context']}
    held_fields = {k for p in held for r in p['context'] for k in r['body'] if k not in ('observer', 'seq')}
    our_fields = {f[0] for f in FIELDS}
    our_q = {q.lower() for f in FIELDS for q in f[3]}
    pack = build()
    problems = []
    if our_fields & held_fields:
        problems.append(('shared fields', sorted(our_fields & held_fields)))
    if our_q & held_q:
        problems.append(('shared questions', sorted(our_q & held_q)))
    if any(path in pack for path in held_paths):
        problems.append(('held-out receipt path in pack', [p for p in held_paths if p in pack][:5]))
    if any(q[:40] in pack.lower() for q in held_q):
        problems.append(('held-out question prefix in pack', [q for q in held_q if q[:40] in pack.lower()][:5]))
    return problems


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out')
    ap.add_argument('--check')
    ap.add_argument('--check-disjoint', metavar='RESEARCH_DIR')
    a = ap.parse_args()
    blob = build()
    if a.check_disjoint:
        problems = check_disjoint(Path(a.check_disjoint))
        print('DISJOINT_OK' if not problems else ('DISJOINT_FAIL', problems))
        sys.exit(0 if not problems else 1)
    if a.check:
        ok = Path(a.check).read_text(encoding='utf-8') == blob
        print('CHECK_OK' if ok else 'CHECK_MISMATCH', hashlib.sha256(blob.encode()).hexdigest())
        sys.exit(0 if ok else 1)
    if a.out:
        Path(a.out).write_text(blob, encoding='utf-8')
    print(len(blob.splitlines()), 'examples', hashlib.sha256(blob.encode()).hexdigest())
