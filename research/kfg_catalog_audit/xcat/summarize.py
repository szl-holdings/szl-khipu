"""Summarize a generated ledger and separately cross-check frozen positive rows."""
import hashlib
import json
from pathlib import Path


def summarize(ledger_path, frozen_path):
    data=Path(ledger_path).read_bytes();r=json.loads(data)
    frozen=Path(frozen_path).read_bytes()
    if hashlib.sha256(frozen).hexdigest()!='476980099680971bc2580708b719c3b0b16007488b99cfb82cf134d5a8580378':
        raise ValueError('unexpected frozen positives')
    p=json.loads(frozen)
    key=lambda x:(x['object_id'],x.get('target_id',x.get('top_cord_id')),tuple(x['summand_ids']))
    allr={key(x):x for x in r['rows']}
    strict={key(x):x for x in r['rows'] if x['mapping']=='strict_shared_candidate'}
    out={k:v for k,v in r.items() if k not in ('rows','per_artifact')}
    out['full_ledger_sha256']=hashlib.sha256(data).hexdigest()
    out['full_ledger_bytes']=len(data)
    out['per_artifact_with_candidates']=[x for x in r['per_artifact'] if x['candidate_count']]
    out['excluded_rows']=[x for x in r['rows'] if x['mapping']!='strict_shared_candidate']
    out['known_value_disagreements']=[x for x in strict.values() if x['okr']['status']==x['kfg']['status']=='known' and not x['values_identical']]
    out['posthoc_frozen_positive_crosscheck']=dict(source_sha256=hashlib.sha256(frozen).hexdigest(),
        rows_in_both_mapped=sum(key(x) in strict for x in p['rows_in_both']),
        rows_okr_only_mapped=sum(key(x) in strict for x in p['rows_okr_only']),
        excluded_positive_rows=[allr[key(x)] for x in p['rows_in_both']+p['rows_okr_only'] if key(x) not in strict])
    return out


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('ledger');p.add_argument('frozen');a=p.parse_args()
    print(json.dumps(summarize(a.ledger,a.frozen),indent=2,sort_keys=True))
