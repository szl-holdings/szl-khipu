"""Offline sensitivity replay; does not modify sources or admit training/evaluation."""
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

PIN = '9d62dec25f6ff6fd69a73bc74a7b714f8dcb2187'
ALIASES = [('KH0121', 'KH0473'), ('KH0140', 'KH0483')]
SIMILARITY = [('KH0192', 'KH0470'), ('KH0303', 'KH0304')]

def digest(b): return hashlib.sha256(b).hexdigest()
def original(k): return int(digest(str(k['id']).encode()), 16) % 10 == 0

def grouped_assignments(khipus, pairs):
    by = {k['okr_num']: k for k in khipus}
    if len(by) != len(khipus): raise ValueError('duplicate OKR identity')
    parent = {key:key for key in by}
    def root(x):
        while parent[x] != x: x = parent[x]
        return x
    for a,b in pairs:
        if a not in by or b not in by: raise ValueError('missing pair member')
        parent[root(a)] = root(b)
    groups = collections.defaultdict(list)
    for k in by: groups[root(k)].append(k)
    # Stable component key: minimum numeric corpus ID, not minimum OKR label.
    assignment = {}
    for members in groups.values():
        representative = min((by[m] for m in members), key=lambda k:int(k['id']))
        for m in members: assignment[m] = original(representative)
    return assignment

def summary(rows):
    return {'rows':len(rows), 'khipus':len({r['khipu'] for r in rows}),
            'tiers':dict(sorted(collections.Counter(r['tier'] for r in rows).items()))}

def content_id(r):
    # Exclude only split; retained rows can be attributed across partitions.
    return digest(json.dumps({k:v for k,v in r.items() if k != 'split'},sort_keys=True).encode())

def replay(source):
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()!=PIN:
        raise ValueError('source revision mismatch')
    tracked = subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=source,text=True)
    if tracked: raise ValueError('source modified')
    path = source/'research/okr_structure_sft/build_structure_sft.py'
    sys.path.insert(0,str(source))
    spec=importlib.util.spec_from_file_location('pinned_builder',path)
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    corpus,train,evals=builder.build()
    sealed=json.loads((path.parent/'structure_v3_manifest.json').read_text())
    if builder.manifest_for(corpus,train,evals)!=sealed: raise ValueError('baseline manifest mismatch')
    active=[k for k in corpus['khipus'] if builder.pendants(k)]
    old={k['okr_num']:original(k) for k in active}
    base_sets=[set(map(content_id,r)) for r in (train,evals)]
    report={'schema':'szl.grouped-split-sensitivity/v1','source_commit':PIN,
      'builder_sha256':digest(path.read_bytes()),'corpus_sha256':corpus['sha256'],
      'relations_archive_sha256':digest((source/'research/okr_corpus/okr_relations_v1.json').read_bytes()),
      'upstream':corpus['source'],'aliases':ALIASES,'similarity_sensitivity_not_duplicate_assertions':SIMILARITY,
      'policy':'Union declared pair edges; assign whole component using sha256(minimum numeric corpus id)%10==0; preserve singleton assignments.',
      'baseline':{'train':summary(train),'eval':summary(evals)},'scenarios':{},
      'training_run':False,'archive_modified':False,'heldout_qualification':False,
      'limitations':['Alias classifications are documentary, not independent physical-object verification; historical accession conflicts retained. KH0121/KH0473 documented in Khipu Field Guide sketchbook footnote 8; KH0140/KH0483 documented in OKR/KFG. These provenance assertions were supplied by coordinating research, not scraped by this replay.',
        'Only the four named pairs covered; no claim all aliases or similarity relations found.',
        'Regrouping does not erase prior training exposure; new split not independently held-out.',
        'Rows regenerate per original builder: train sequences disappear in eval and cipher limit changes 3 to 5.']}
    for name,pairs in [('aliases_only',ALIASES),('aliases_plus_similarity_sensitivity',ALIASES+SIMILARITY)]:
        assignment=grouped_assignments(corpus['khipus'],pairs)
        saved=builder.held_out
        try:
            builder.held_out=lambda k:assignment[k['okr_num']]
            _,new_train,new_eval=builder.build(corpus)
        finally: builder.held_out=saved
        new_sets=[set(map(content_id,r)) for r in (new_train,new_eval)]
        moved=[{'khipu':k,'from':'eval' if old[k] else 'train','to':'eval' if assignment[k] else 'train',
          'before_rows':sum(r['khipu']==k for r in train+evals),
          'after_rows':sum(r['khipu']==k for r in new_train+new_eval)} for k in sorted(old) if old[k]!=assignment[k]]
        pair_checks=[]
        for kind,edges in [('alias',ALIASES),('similarity_not_duplicate',SIMILARITY)]:
            for a,b in edges:
                pair_checks.append({'kind':kind,'pair':[a,b],'active_members':[x for x in (a,b) if x in old],
                    'baseline_splits':['eval' if old[x] else 'train' for x in (a,b)],
                    'candidate_splits':['eval' if assignment[x] else 'train' for x in (a,b)],
                    'cross_split_before':old[a]!=old[b], 'cross_split_after':assignment[a]!=assignment[b]})
        report['scenarios'][name]={'train':summary(new_train),'eval':summary(new_eval),'moved_khipus':moved,
          'rows_train_to_eval':len(base_sets[0]&new_sets[1]),'rows_eval_to_train':len(base_sets[1]&new_sets[0]),
          'removed_content_rows':len((base_sets[0]|base_sets[1])-(new_sets[0]|new_sets[1])),
          'added_content_rows':len((new_sets[0]|new_sets[1])-(base_sets[0]|base_sets[1])),
          'okr_id_overlap_before':len({r['khipu'] for r in train}&{r['khipu'] for r in evals}),
          'okr_id_overlap_after':len({r['khipu'] for r in new_train}&{r['khipu'] for r in new_eval}),
          'pair_checks':pair_checks,
          'train_sha256':digest(builder._jsonl(new_train)),'eval_sha256':digest(builder._jsonl(new_eval))}
    return report

if __name__=='__main__':
    # Keep the published evidence byte-identical on Windows and POSIX.
    encoded = json.dumps(replay(Path(sys.argv[1]).resolve()), indent=2, sort_keys=True)
    sys.stdout.buffer.write((encoded + "\n").encode("utf-8"))
