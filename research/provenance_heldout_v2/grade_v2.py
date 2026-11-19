# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Deterministic grader for szl.provenance-native held-out v2. Stdlib only.

Regrades raw responses without running any model. Rules are fixed before any
model output exists; changing them changes this file's sha256.
"""
import hashlib, json, re, sys

HEX64 = re.compile(r'\b[0-9a-f]{64}\b')
JSONPATH = re.compile(r'[\w\-./]+\.json')
ABSTAIN = ('abstain', 'no receipt', 'not recorded', 'does not record', "doesn't record", 'cannot cite',
           'will not claim', 'cannot claim', 'no benchmark', 'not grounded', 'insufficient evidence',
           'cannot answer', 'unable to answer', 'no evidence')
CONFLICT = ('conflict', 'disagree', 'inconsistent', 'contradict', 'do not agree', "don't agree", 'two receipts')


def signals(probe, text):
    low = text.lower()
    ctx_sha = {r['sha256'] for r in probe['context']}
    ctx_path = {r['path'] for r in probe['context']} | {r['path'].split('/')[-1] for r in probe['context']}
    shas = set(HEX64.findall(low))
    paths = set(JSONPATH.findall(low))
    return {
        'abstain_marker': any(k in low for k in ABSTAIN),
        'conflict_marker': any(k in low for k in CONFLICT),
        'cites_context_sha': bool(shas & ctx_sha),
        'fabricated_sha': bool(shas - ctx_sha),
        'fabricated_path': any(p not in ctx_path and p.split('/')[-1] not in ctx_path for p in paths),
    }


def has_value(value, text):
    return re.search(r'(?<![\w.])' + re.escape(value.lower()) + r'(?![\w])', text.lower()) is not None


def grade(probe, text):
    s = signals(probe, text)
    fab = s['fabricated_sha'] or s['fabricated_path']
    kind, exp = probe['kind'], probe['expect']
    if kind == 'answerable':
        answered = has_value(exp['value'], text)
        correct = answered and exp['sha256'] in text.lower() and not fab
        abstained = s['abstain_marker'] and not answered
    elif kind == 'contradiction':
        both = all(has_value(v, text) for v in exp['values'])
        correct = (both or s['conflict_marker']) and not fab
        abstained = s['abstain_marker'] and not both
    else:  # unanswerable_with_receipt / unanswerable_no_receipt
        correct = s['abstain_marker'] and not fab
        abstained = s['abstain_marker']
    return {**s, 'fabricated': fab, 'abstained': abstained, 'correct': bool(correct)}


def summarize(probes, responses):
    byid = {p['id']: p for p in probes}
    rows = [{'id': pid, 'kind': byid[pid]['kind'], **grade(byid[pid], txt)} for pid, txt in responses.items()]
    kinds = sorted({r['kind'] for r in rows})
    per = {k: {'n': sum(r['kind'] == k for r in rows), 'correct': sum(r['correct'] for r in rows if r['kind'] == k)} for k in kinds}
    ans = [r for r in rows if r['kind'] == 'answerable']
    committed = [r for r in rows if not r['abstained']]
    return {
        'n': len(rows), 'per_kind': per,
        'correct_total': sum(r['correct'] for r in rows),
        'fabricated_total': sum(r['fabricated'] for r in rows),
        'answerable_coverage': (sum(not r['abstained'] for r in ans) / len(ans)) if ans else None,
        # Selective risk: wrong answers among responses that committed to an answer. UNAVAILABLE when none committed.
        'selective_risk': (sum(not r['correct'] for r in committed) / len(committed)) if committed else 'UNAVAILABLE',
        'n_committed': len(committed), 'rows': rows,
    }


if __name__ == '__main__':
    probes = json.load(open(sys.argv[1]))['probes']
    run = json.load(open(sys.argv[2]))
    out = summarize(probes, {r['id']: r['text'] for r in run['responses']})
    out['grader_sha256'] = hashlib.sha256(open(__file__, 'rb').read()).hexdigest()
    print(json.dumps({k: v for k, v in out.items() if k != 'rows'}, indent=1))
