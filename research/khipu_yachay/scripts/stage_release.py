"""Stage three Hugging Face repositories from one reviewed, pinned GitHub source.

Never publishes. It creates byte-verifiable local staging artifacts only.
An independent source owner must then review DCO, rights, Hub write authority,
exact expected-parent commits, live Space output and rollbacks before upload.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys


# Only these previously reviewed source files belong in a published dataset
# or the hosted Space. The post-hoc evaluation set is intentionally absent
# from production images and remains a research-only source fixture.
RELEASE_DATA_FILES = (
    "synthetic_train.jsonl",
    "synthetic_eval.jsonl",
    "sources.jsonl",
    "okr_kh_index.jsonl",
    "okr_registry_provenance.json",
)


def stage(project: Path, output: Path, source_revision: str) -> dict:
    if len(source_revision) != 40 or any(c not in '0123456789abcdef' for c in source_revision):
        raise ValueError('REVIEWED_SOURCE_SHA_REQUIRED')
    if output.exists():
        raise ValueError('OUTPUT_EXISTS')
    # Reuse the same exact-byte admission contract as the hosted reader.
    # Changing a source file without reviewing its Git-bound pin is a HOLD.
    if str(project.resolve()) not in sys.path:
        sys.path.insert(0, str(project.resolve()))
    from src.asset_contract import verify_assets
    verify_assets(project)
    receipt = json.loads((project/'model/training_receipt.json').read_bytes())
    model = project/'model/yachay_nb_v0.json'
    if sha256(model.read_bytes()).hexdigest() != receipt['data']['model/yachay_nb_v0.json']['sha256']:
        raise ValueError('MODEL_DIGEST_MISMATCH')
    for name, item in receipt['data'].items():
        if sha256((project/name).read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('DATA_DIGEST_MISMATCH:'+name)
    output.mkdir(parents=True)
    dirs = {x: output/x for x in ('dataset','model','space')}
    for d in dirs.values():d.mkdir()
    # Dataset: original authored synthetic data and MIT-attributed public metadata pointers.
    for name in RELEASE_DATA_FILES:
        shutil.copyfile(project/'data'/name, dirs['dataset']/name)
    shutil.copyfile(project/'docs/DATASET_CARD.md',dirs['dataset']/'README.md')
    shutil.copyfile(project/'model/yachay_nb_v0.json',dirs['model']/'yachay_nb_v0.json')
    shutil.copyfile(project/'model/training_receipt.json',dirs['model']/'training_receipt.json')
    shutil.copyfile(project/'docs/MODEL_CARD.md',dirs['model']/'README.md')
    # HF Space repository root is /app. The runtime's ROOT calculation and
    # Docker CMD require app.py/assets under /app/space/, not /app/.
    for name in ('README.md', 'Dockerfile'):
        shutil.copyfile(project/'space'/name, dirs['space']/name)
    (dirs['space'] / 'space').mkdir()
    for name in ('app.py', 'app.js', 'style.css', 'index.html'):
        shutil.copyfile(project/'space'/name, dirs['space']/'space'/name)
    for subdir in ('src','model'):
        shutil.copytree(project/subdir,dirs['space']/subdir,
                        ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    (dirs['space'] / 'data').mkdir()
    for name in RELEASE_DATA_FILES:
        shutil.copyfile(project/'data'/name,dirs['space']/'data'/name)
    # Include the license in all three repo packages; the source rights status
    # remains mixed and described explicitly in the cards.
    for dest in dirs.values():
        (dest/'SOURCE_BINDING.json').write_text(json.dumps({
            'schema':'szl.khipu-yachay.github-source-binding/v0',
            'source_repo':'szl-holdings/szl-khipu',
            'expected_source_sha':source_revision,
            'publication_state':'STAGED_NOT_UPLOADED',
            'model_source_sha256':sha256(model.read_bytes()).hexdigest(),
        },sort_keys=True,indent=2)+'\n',encoding='utf-8')
    files={}
    for key,directory in dirs.items():
        files[key]={str(p.relative_to(directory)):sha256(p.read_bytes()).hexdigest()
                    for p in sorted(directory.rglob('*')) if p.is_file()}
    manifest={'schema':'szl.khipu-yachay.release-plan/v0',
              'source_sha':source_revision,'target_org':'SZLHOLDINGS',
              'intended_repos':{
                  'dataset':'SZLHOLDINGS/khipu-yachay-research-v0',
                  'model':'SZLHOLDINGS/SZL-Khipu-Yachay-Nano',
                  'space':'SZLHOLDINGS/khipu-yachay'},
              'files':files,'dry_run_only':True,'provider_commits':None,
              'released':False,'runtime_verified':False,
              'owner_review_required':True}
    (output/'STAGING_MANIFEST.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--reviewed-source-sha',required=True)
    args=p.parse_args()
    result=stage(args.root,args.out,args.reviewed_source_sha)
    print(json.dumps({'state':'STAGED_NOT_UPLOADED','files':{k:len(v) for k,v in result['files'].items()},'source_sha':result['source_sha']},indent=2))
