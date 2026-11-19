"""Strict relation overlap for pinned KFG v2.1.0 and SZL Proof Loom release.
Inputs: KFG_DB.SQL, khipu_summary.csv, sum_top_cords_relation.csv,
corpus.json.gz (=okr_corpus_v1.json.gz), okr.json (=okr_relations_v1.json).
Usage: python compare.py > result.json
Positive match exports only: not a sensitivity, precision, or replication analysis.
"""
import csv, gzip, hashlib, json, re
from collections import defaultdict
from pathlib import Path
HASHES = {'corpus.json.gz': '6ef204b641826b37c320509952ed4181e93865af20f1cdfefd7516a49cf8ad0d', 'okr.json': 'a9f38398359e88819514333c083bdfd9b5880fb2b428847c872630c8b317a038', 'KFG_DB.SQL': 'a0171bf18a3c6652a818b079050d72a6e0ecb535ec0923a680979072d491221b', 'khipu_summary.csv': '0545deea4246d117a3de1ea425fb14800970c202b772ceded65bc13a90b4c7af', 'sum_top_cords_relation.csv': 'e51a52330663f529285b71c4e55a5563571f5b4469749a91dd2ea1eec8173832'}
atom = "(?:'(?:[^'\\\\]|\\\\.|'')*'|[^,()]+)"
row_re = re.compile('\\((' + atom + '(?:,' + atom + ')*)\\)')
sep_re = re.compile(atom)

def rows(line, width):
    payload = line.split(' VALUES ', 1)[1].rstrip('\r\n;')
    prev = 0
    for m in row_re.finditer(payload):
        if not payload[prev:m.start()] in ('', ','):
            raise AssertionError(payload[prev:m.start()])
        prev = m.end()
        row = sep_re.findall(m.group(1))
        if not len(row) == width:
            raise AssertionError((width, row[:5], len(row)))
        yield row
    if not prev == len(payload):
        raise AssertionError((prev, len(payload)))

def load_analysis(input_dir=Path('.')):
    """Validate pinned local inputs and return the report and native positive set."""
    input_dir = Path(input_dir)
    for f, h in HASHES.items():
        path = input_dir / f
        if not path.is_file():
            raise FileNotFoundError(f'Required pinned input is missing or not a file: {path}')
        if hashlib.sha256(path.read_bytes()).hexdigest() != h:
            raise ValueError(f'SHA256 mismatch for pinned input: {path}')

    def read_csv(f):
        with open(f, newline='', encoding='utf-8') as rf:
            return list(csv.DictReader(rf))
    summary = {int(s['khipu_id']): s for s in read_csv(input_dir / 'khipu_summary.csv')}
    kfg = read_csv(input_dir / 'sum_top_cords_relation.csv')
    with gzip.open(input_dir / 'corpus.json.gz', 'rt') as f:
        c = json.load(f)
    with open(input_dir / 'okr.json') as f:
        o = json.load(f)
    objects = {row['id']: row for row in c['khipus']}
    if not len(objects) == len(c['khipus']):
        raise AssertionError()
    common = summary.keys() & objects.keys()
    shared = {i for i in common if summary[i]['okr_name'] == objects[i]['okr']}
    col = {k: v for v, k in enumerate(c['cord_fields'])}
    ok_pos = set()
    multi = 0
    for r in o['khipus']:
        cord = {q[0]: q for q in objects[r['id']]['cords']}
        for t, target, members, value in r['relations']:
            if t != 'R2':
                continue
            if not len({cord[j][col['parent']] for j in members}) == 1:
                raise AssertionError()
            clusters = {cord[j][col['cluster']] for j in members}
            if len(clusters) == 1:
                ok_pos.add((r['id'], target, tuple(sorted(members)), value))
            else:
                multi += 1
    target_objects = {int(r['khipu_id']) for r in kfg}
    clusters = {}
    by_primary = defaultdict(list)
    cord_ids = defaultdict(list)
    with open(input_dir / 'KFG_DB.SQL', encoding='utf-8') as sql:
        for line in sql:
            if line.startswith('INSERT INTO `cord_cluster` VALUES '):
                for r in rows(line, 16):
                    obj, parent, cluster, ordinal, n, level = map(int, (r[1], r[2], r[3], r[4], r[7], r[8]))
                    if obj in target_objects and level in (1, -1):
                        if not (obj, cluster) not in clusters:
                            raise AssertionError()
                        clusters[obj, cluster] = (parent, ordinal, n)
                        by_primary[obj, parent].append((ordinal, cluster))
            elif line.startswith('INSERT INTO `cord` VALUES '):
                for r in rows(line, 22):
                    obj = int(r[1])
                    if obj not in target_objects or r[10] == 'NULL':
                        continue
                    cord_ids[obj, int(r[10])].append(int(r[2]))
    positives = set()
    exceptions = []
    conflicts = []
    for r in kfg:
        obj, tc, tp, sp, n, value, sm = map(int, (r['khipu_id'], r['cluster_id'], r['cluster_position'], r['summand_cluster_position'], r['num_summand_cords'], r['top_cord_value'], r['summand_value']))
        flag = r['is_exact_sum'] == 'True'
        if flag != (value == sm):
            conflicts.append({'id': obj, 'kfg': r['name'], 'target': value, 'sum': sm, 'exact_flag': flag})
        if not (flag and value == sm and (value > 0) and (n >= 2) and (abs(tp - sp) == 1)):
            continue
        try:
            parent, ord_, _ = clusters[obj, tc]
            g = [g for _, g in sorted(by_primary[obj, parent])]
            if not g[tp] == tc:
                raise AssertionError((g[tp], tc))
            sc = g[sp]
            t = cord_ids[obj, tc]
            s = cord_ids[obj, sc]
            if not (len(t) == 1 and len(s) == n):
                raise AssertionError((len(t), len(s), n))
        except (AssertionError, KeyError, IndexError) as e:
            exceptions.append((obj, r['name'], tc, tp, sp, n, str(e)))
            continue
        positives.add((obj, t[0], tuple(sorted(s)), value))
    ok_shared = {r for r in ok_pos if r[0] in shared}
    kfg_shared = {r for r in positives if r[0] in shared}
    match = ok_shared & kfg_shared

    def display(rs):
        return [dict(okr=objects[i]['okr'], kfg=summary[i]['kfg_name'], object_id=i, top_cord_id=t, summand_ids=ss, value=v) for i, t, ss, v in sorted(rs)]
    result = dict(input_hashes=HASHES, kfg_artifacts=len(summary), okr_artifacts=len(objects), shared_internal_ids=len(common), concordant_id_and_okr_name=len(shared), identity_exclusions=[(i, summary[i]['okr_name'], objects[i]['okr']) for i in sorted(common - shared)], kfg_relation_rows=len(kfg), kfg_export_flag_arithmetic_conflicts=conflicts, positional_or_group_size_mapping_exceptions=exceptions, okr_single_group_rows=len(ok_pos), okr_multigroup_rows=multi, kfg_strict_mapped_rows=len(positives), okr_shared_positive_rows=len(ok_shared), kfg_shared_positive_rows=len(kfg_shared), strictly_matching_rows=len(match), strictly_matching_objects=len({r[0] for r in match}), rows_in_both=display(match), rows_okr_only=display(ok_shared - kfg_shared), rows_kfg_only=display(kfg_shared - ok_shared))
    return (result, ok_pos, multi)

def compare(input_dir=Path('.')):
    """Return the positive-overlap report without printing it."""
    return load_analysis(input_dir)[0]

def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, default=Path('.'))
    args = parser.parse_args()
    print(json.dumps(compare(args.input_dir), indent=2))
if __name__ == '__main__':
    main()
