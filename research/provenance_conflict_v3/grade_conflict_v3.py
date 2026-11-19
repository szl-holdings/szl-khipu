# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Deterministic grader for szl.provenance-native conflict probes v3. Stdlib only.

Reuses held-out v2's citation, fabrication and value rules (grade_v2.py) unchanged.
What differs: a conflict counts only when it is asserted. "There is no conflict" or
"the receipts do not disagree" is not a conflict report, and the v2 phrase
"two receipts" no longer counts on its own.
"""
import hashlib, importlib.util, json, re, sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    'grade_v2', Path(__file__).resolve().parents[1] / 'provenance_heldout_v2' / 'grade_v2.py')
v2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v2)

# A conflict word counts unless it is directly negated ("no conflict", "not inconsistent").
_CONFLICT = re.compile(r"(?<!\bno )(?<!\bnot )(?<!n't )\b(conflict\w*|disagree\w*|inconsisten\w*|contradict\w*)\b")
_DISAGREE = re.compile(r"\b(do|does) not agree\b|\b(don't|doesn't) agree\b|\bdiffer(s|ent)? (from each other|between)\b")


def asserts_conflict(text):
    low = ' '.join(text.lower().split())
    return bool(_CONFLICT.search(low) or _DISAGREE.search(low))


def grade(probe, text):
    s = v2.signals(probe, text)
    fab = s['fabricated_sha'] or s['fabricated_path']
    conflict = asserts_conflict(text)
    kind, exp = probe['kind'], probe['expect']
    if kind == 'contradiction':
        all_values = all(v2.has_value(v, text) for v in exp['values'])
        correct = (all_values or conflict) and not fab
        abstained = s['abstain_marker'] and not all_values
    elif kind == 'consistent_pair':
        answered = v2.has_value(exp['value'], text)
        cites = any(h in text.lower() for h in exp['sha256_any'])
        correct = answered and cites and not conflict and not fab
        abstained = s['abstain_marker'] and not answered
    elif kind == 'answerable':
        answered = v2.has_value(exp['value'], text)
        correct = answered and exp['sha256'] in text.lower() and not fab
        abstained = s['abstain_marker'] and not answered
    else:
        raise ValueError(kind)
    return {**s, 'asserts_conflict': conflict, 'fabricated': fab, 'abstained': abstained, 'correct': bool(correct)}


def summarize(probes, responses):
    byid = {p['id']: p for p in probes}
    rows = [{'id': pid, 'kind': byid[pid]['kind'], **grade(byid[pid], txt)} for pid, txt in responses.items()]
    kinds = sorted({r['kind'] for r in rows})
    per = {k: {'n': sum(r['kind'] == k for r in rows), 'correct': sum(r['correct'] for r in rows if r['kind'] == k)} for k in kinds}
    return {'n': len(rows), 'per_kind': per, 'correct_total': sum(r['correct'] for r in rows),
            'fabricated_total': sum(r['fabricated'] for r in rows),
            'false_conflict_on_consistent': sum(r['asserts_conflict'] for r in rows if r['kind'] == 'consistent_pair'),
            'rows': rows}


if __name__ == '__main__':
    probes = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))['probes']
    run = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
    out = summarize(probes, {r['id']: r['text'] for r in run['responses']})
    out['grader_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    print(json.dumps({k: v for k, v in out.items() if k != 'rows'}, indent=1))
