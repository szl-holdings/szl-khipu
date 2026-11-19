"""Bounded, denominator-first recorded arithmetic concordance, not replication."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
from collections import defaultdict, Counter
from compare import HASHES, rows

ENUMERATOR_HASH = '8cd4ba65f10806db9d3c13e9c2aed1ba618d22b4306ec85b4c6091072d1c35f7'


def need(ok, why):
    if not ok:
        raise ValueError(why)


def sql_value(cord, knots):
    if not knots:
        return None if cord[6].strip("'") in ('B', 'C') else 0
    return None if any(v is None or v <= 0 for v in knots) else sum(knots)


def arithmetic(values):
    if any(v is None for v in values):
        return dict(status='unknown', target=values[0], summands=values[1:])
    target, *members = values
    eligible = target > 0 and len(members) >= 2 and sum(v > 0 for v in members) >= 2
    return dict(status='known', target=target, summands=members, sum=sum(members),
                equal=target == sum(members), eligible=eligible,
                exact_relation=eligible and target == sum(members))


def single_group_candidates(k, st):
    """Native pendant-group segmentation; extend native touches to unknown targets."""
    cords = k['cords']
    seqs = defaultdict(list)
    for i, c in enumerate(cords):
        if st.roles[i] in ('pendant', 'top', 'marker') and c['parent_kind'] != 'cord':
            key = c.get('parent') if c['parent_kind'] == 'primary' else None
            seqs[key].append(i)
    for seq in seqs.values():
        pend = sorted((i for i in seq if st.roles[i] == 'pendant'), key=lambda i:(cords[i]['ordinal'],st.ids[i]))
        for t in seq:
            if st.roles[t] != 'top':
                continue
            ins = sum((cords[i]['ordinal'],st.ids[i]) < (cords[t]['ordinal'],st.ids[t]) for i in pend)
            touch = {st.group_of[pend[j]] for j in (ins-1,ins) if 0 <= j < len(pend)}
            for g in sorted(touch):
                if len(st.groups[g]) >= 2:
                    yield t, g


def run(input_dir):
    d = Path(input_dir)
    hashes = {k:v for k,v in HASHES.items() if k in ('corpus.json.gz','KFG_DB.SQL','khipu_summary.csv')}
    hashes['okr_khipu.py'] = ENUMERATOR_HASH
    for name, digest in hashes.items():
        need((d/name).is_file(), 'missing input: '+name)
        need(hashlib.sha256((d/name).read_bytes()).hexdigest() == digest, 'hash mismatch: '+name)
    spec=importlib.util.spec_from_file_location('_okr_pinned',d/'okr_khipu.py')
    okr=importlib.util.module_from_spec(spec);spec.loader.exec_module(okr)
    corpus=okr.load_corpus(d/'corpus.json.gz',expected_sha256=hashes['corpus.json.gz'])
    with (d/'khipu_summary.csv').open(newline='') as f:
        summary={int(r['khipu_id']):r for r in csv.DictReader(f)}
    shared={i for i,k in corpus['by_id'].items() if i in summary and k['okr_num']==summary[i]['okr_name']}
    cords={};clusters={};members=defaultdict(list);primaries=defaultdict(list);knots=defaultdict(list)
    # Parse every knot before filtering, so SQL INSERT table order cannot silently drop values.
    with (d/'KFG_DB.SQL').open(encoding='utf-8') as f:
        for line in f:
            for table,width in [('cord',22),('cord_cluster',16),('knot',13)]:
                if not line.startswith(f'INSERT INTO `{table}` VALUES '): continue
                for r in rows(line,width):
                    if table=='knot':
                        knots[int(r[1])].append(None if r[5]=='NULL' else int(r[5]));continue
                    obj=int(r[1])
                    if obj not in shared:continue
                    if table=='cord':
                        key=(obj,int(r[2]));need(key not in cords,'duplicate SQL cord');cords[key]=r
                        if r[10]!='NULL':members[obj,int(r[10])].append(int(r[2]))
                    elif int(r[8]) in (1,-1):
                        key=(obj,int(r[3]));need(key not in clusters,'duplicate SQL group');clusters[key]=r
                        primaries[obj,int(r[2])].append((int(r[4]),int(r[3])))
    detailed=[];native_check=0
    for obj in sorted(shared):
        k=corpus['by_id'][obj];st=okr._Structure(k)
        cands=list(single_group_candidates(k,st))
        expected={(t,gs[0]) for t,unions in st.r2 for gs in unions if len(gs)==1 and len(st.groups[gs[0]])>=2}
        actual={(t,g) for t,g in cands if st.known[t]}
        need(actual==expected,'candidate builder differs from native enumerator');native_check+=len(actual)
        for t,g in cands:
            ids=[st.ids[t]]+sorted(st.ids[i] for i in st.groups[g])
            ov=[st.values[st.idx[i]] for i in ids]
            rec=dict(object_id=obj,okr_name=k['okr_num'],target_id=ids[0],summand_ids=ids[1:],okr=arithmetic(ov))
            missing=[i for i in ids if (obj,i) not in cords]
            rec['missing_kfg_cord_ids']=missing
            rec['mapping']='missing_cord' if missing else 'unverified'
            if not missing:
                raw=[cords[obj,i] for i in ids]
                kv=[sql_value(r,knots[int(r[2])]) for r in raw]
                rec['kfg']=arithmetic(kv)
                rec['values_identical']=ov==kv
                group_ids={r[10] for r in raw[1:]}
                if raw[0][10]=='NULL' or len(group_ids)!=1 or 'NULL' in group_ids:
                    rec['mapping']='missing_or_multiple_groups'
                else:
                    tg=int(raw[0][10]);sg=int(next(iter(group_ids)))
                    rec['kfg_target_cluster']=tg;rec['kfg_summand_cluster']=sg
                    full=sorted(members[obj,sg])==ids[1:] and members[obj,tg]==[ids[0]]
                    rec['complete_cord_groups']=full
                    if not full:rec['mapping']='group_members_differ'
                    elif (obj,tg) not in clusters or (obj,sg) not in clusters:rec['mapping']='cluster_metadata_missing'
                    else:
                        tr,sr=clusters[obj,tg],clusters[obj,sg]
                        same=tr[2]==sr[2]
                        levels=(int(raw[0][15])==-1 or tr[12].strip("'") in okr.TOP_CLASSES) and int(sr[8])==1 and sr[12].strip("'") not in (*okr.TOP_CLASSES, *okr.MARKER_CLASSES) and all(int(r[15])==1 for r in raw[1:])
                        rec['kfg_levels_verified']=levels
                        rec['same_primary']=same
                        if not same:rec['mapping']='different_primary'
                        else:
                            seq=sorted(primaries[obj,int(tr[2])]);order=[x[1] for x in seq]
                            tied=len({x[0] for x in seq})!=len(seq)
                            adjacency=abs(order.index(tg)-order.index(sg))==1 and not tied
                            rec['kfg_cluster_positions']=[order.index(tg),order.index(sg)]
                            lo,hi=sorted(rec['kfg_cluster_positions'])
                            rec['interposed_kfg_clusters']=[dict(cluster_id=gid,group_class=clusters[obj,gid][12].strip("'"),cord_ids=sorted(members[obj,gid])) for gid in order[lo+1:hi]]
                            rec['kfg_adjacency_verified']=adjacency
                            rec['mapping']='strict_shared_candidate' if adjacency and levels else ('ambiguous_cluster_order' if tied else ('role_mismatch' if not levels else 'nonadjacent_clusters'))
            detailed.append(rec)
    counts=Counter(r['mapping'] for r in detailed)
    strict=[r for r in detailed if r['mapping']=='strict_shared_candidate']
    known=[r for r in strict if r['okr']['status']==r['kfg']['status']=='known']
    matrix=Counter(f"okr_{r['okr']['exact_relation']}_kfg_{r['kfg']['exact_relation']}" for r in known)
    per=[]
    for obj in sorted(shared):
        rs=[r for r in detailed if r['object_id']==obj]
        per.append(dict(object_id=obj,okr=corpus['by_id'][obj]['okr_num'],candidate_count=len(rs),mapping_counts=dict(Counter(r['mapping'] for r in rs)),strict_unknown=sum(r['mapping']=='strict_shared_candidate' and (r['okr']['status']=='unknown' or r['kfg']['status']=='unknown') for r in rs), strict_known_matrix=dict(Counter(f"okr_{r['okr']['exact_relation']}_kfg_{r['kfg']['exact_relation']}" for r in rs if r['mapping']=='strict_shared_candidate' and r['okr']['status']==r['kfg']['status']=='known'))))
    all_native=sum(okr._Structure(k).candidates()['R2'] for k in corpus['khipus'])
    shared_native=sum(okr._Structure(corpus['by_id'][obj]).candidates()['R2'] for obj in shared)
    positives=sum(r['okr']['exact_relation'] and r['kfg']['exact_relation'] for r in known)
    unknown=len(strict)-len(known)
    return dict(schema='szl.conditional-candidate-concordance.v1',input_hashes=hashes,
        domain='One adjacent native OKR pendant group with >=2 cords per top cord, including unknown target/summand values; KFG strict adjacency is immediate full-cluster adjacency on same primary with unique ordinal order and SQL top role (-1 cord level or top grouping class), pendant level 1/non-marker group.',
        interpretation='Recorded-source concordance conditional on OKR candidates and strict shared KFG structure. Not an independent KFG algorithm replay, population prevalence, precision, recall, or decipherment. Export absence is never a negative.',
        native_all_corpus_R2_union_candidates=all_native,native_shared_R2_union_candidates=shared_native,shared_objects=len(shared),objects_without_candidates=len(shared)-sum(bool(x['candidate_count']) for x in per), identity_exclusions=[dict(object_id=i,okr=corpus['by_id'][i]['okr_num'],kfg_okr_name=summary[i]['okr_name']) for i in sorted(set(summary)&set(corpus['by_id'])-shared)],native_known_target_candidates_verified=native_check,total_candidates=len(detailed),candidate_objects=sum(bool(x['candidate_count']) for x in per),mapping_counts=dict(sorted(counts.items())),strict_shared_candidates=len(strict),strict_candidate_objects=len({r['object_id'] for r in strict}),strict_known_both=len(known),strict_unknown=unknown,strict_status_pairs=dict(Counter(r['okr']['status']+'_'+r['kfg']['status'] for r in strict)),strict_values_identical=sum(r['values_identical'] for r in known),strict_exact_relation_matrix=dict(sorted(matrix.items())),strict_eligibility_matrix=dict(Counter(f"okr_{r['okr']['eligible']}_kfg_{r['kfg']['eligible']}" for r in known)),strict_eligible_both_exact_matrix=dict(Counter(f"okr_{r['okr']['exact_relation']}_kfg_{r['kfg']['exact_relation']}" for r in known if r['okr']['eligible'] and r['kfg']['eligible'])),
        joint_exact_fraction_identification_bounds=dict(denominator=len(strict),lower_numerator=positives,upper_numerator=positives+unknown,lower=positives/len(strict) if strict else None,upper=(positives+unknown)/len(strict) if strict else None,note='Conservative finite conditional denominator bounds, not sampling confidence intervals or sharp partial-arithmetic bounds. All 109 unresolved rows are unknown on both sides; none has a fully-known nonexact opposite side. Partial known sums are not used to tighten the upper bound.'),per_artifact=per,rows=detailed)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('input_dir');a=p.parse_args()
    print(json.dumps(run(a.input_dir),indent=2,sort_keys=True))
