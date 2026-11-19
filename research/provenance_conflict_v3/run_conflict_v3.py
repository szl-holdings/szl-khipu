# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Conflict v3 generation for szl-provenance-native adapters. Records raw responses only.

Grading is done afterwards by grade_conflict_v3.py, from the raw responses, so the grade can be
recomputed by anyone without a GPU. Results are UNSIGNED and stay local until reviewed.
"""
import argparse, hashlib, json, os, platform, sys, time
from pathlib import Path
import torch, transformers, peft
from huggingface_hub import HfApi, hf_hub_download
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grade_conflict_v3 as grader

ap = argparse.ArgumentParser()
ap.add_argument('--base', default='SZLHOLDINGS/szl-receiptagent-qwen35-0.8b-v2m-estate-sft-v1')
ap.add_argument('--adapters', default='SZLHOLDINGS/szl-provenance-native-v2-lora,SZLHOLDINGS/szl-provenance-native-v3-lora,'
                'SZLHOLDINGS/szl-provenance-native-v4-lora,SZLHOLDINGS/szl-provenance-native-v5-lora')
ap.add_argument('--probes', default='provenance_conflict_probes_v3.json')
ap.add_argument('--outdir', default='out')
ap.add_argument('--max-new-tokens', type=int, default=256)
a = ap.parse_args()
os.makedirs(a.outdir, exist_ok=True)

# Same system prompt as held-out v1 and v2, so results stay comparable across sets.
SYS = ('You are a provenance-native assistant of the SZL governed-AI estate. Cite the exact receipt '
       '(path + sha256) that grounds every factual claim about measured estate state; end grounded answers '
       'with a <provenance> block. If no receipt grounds a claim, say so and abstain. A receipt proves only '
       'what it records. State "no benchmark recorded" unless a receipt records one.')

def sha_file(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
probe_doc = json.loads(Path(a.probes).read_text(encoding='utf-8'))
probes = probe_doc['probes']

# Fail closed on leakage: no probe question may appear (exact or 40-char prefix) in any training corpus string.
def strings(x):
    if isinstance(x, str): yield x.lower()
    elif isinstance(x, dict):
        for v in x.values(): yield from strings(v)
    elif isinstance(x, list):
        for v in x: yield from strings(v)
corpus_text, corpus_sha = [], {}
for f in ['provenance_corpus_v02.jsonl', 'provenance_corpus_v03.jsonl', 'provenance_corpus_v04.jsonl', 'provenance_corpus_v05.jsonl']:
    path = hf_hub_download('SZLHOLDINGS/provenance-native-corpus-v1', f, repo_type='dataset')
    corpus_sha[f] = sha_file(path)
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if line:
                corpus_text.extend(strings(json.loads(line)))
blob = '\n'.join(corpus_text)
leaks = [p['id'] for p in probes if p['question'].lower() in blob or p['question'].lower()[:40] in blob]
if leaks:
    print('ABORT_LEAKAGE', leaks, flush=True); sys.exit(3)
print('LEAK_CHECK_OK', len(corpus_text), 'corpus strings', flush=True)

def user_turn(p):
    if not p['context']:
        ctx = 'Receipts in front of you: none.'
    else:
        ctx = 'Receipts in front of you:\n' + '\n'.join(
            f"- path: {r['path']}\n  sha256: {r['sha256']}\n  body: {json.dumps(r['body'], sort_keys=True)}" for r in p['context'])
    return ctx + '\n\nQuestion: ' + p['question']

# Preregistration gate: every model must predate this probe set, so no weights can be tuned to it.
PREREG_UTC = '2026-11-19T08:00:00+00:00'
# Amendment A1 (README): load the exact revisions held-out v2 evaluated, and require each pinned
# commit to predate PREREG_UTC. A later commit that only edits a model card no longer blocks the run;
# a model without a pinned revision does.
PINNED = {
    'SZLHOLDINGS/szl-receiptagent-qwen35-0.8b-v2m-estate-sft-v1': 'aa3e937e991af2513f9f77f28aeab4f220622785',
    'SZLHOLDINGS/szl-provenance-native-v2-lora': '4e3b48f077c1c060b4a3d3eb7e1523c14f9d4209',
    'SZLHOLDINGS/szl-provenance-native-v3-lora': '97c2b8e29d019def82b95b3f1f8f7f14ee951aba',
    'SZLHOLDINGS/szl-provenance-native-v4-lora': '7631759bfaf719944ebc6c6843261320ef0f0802',
    'SZLHOLDINGS/szl-provenance-native-v5-lora': '1dc8e0203ae64c61157e8b98947ef1f4af49fe49',
}
api = HfApi()
models = [a.base] + a.adapters.split(',')
unpinned = [m for m in models if m not in PINNED]
if unpinned:
    print('ABORT_UNPINNED_MODEL', unpinned, flush=True); sys.exit(4)
revs = {m: PINNED[m] for m in models}
pinned_utc, late = {}, []
for m in models:
    c = api.list_repo_commits(m, revision=revs[m])[0]
    pinned_utc[m] = c.created_at.isoformat()
    if c.commit_id != revs[m] or c.created_at.isoformat() >= PREREG_UTC:
        late.append(m)
if late:
    print('ABORT_MODEL_AFTER_PREREGISTRATION', late, flush=True); sys.exit(4)
infos = {m: api.model_info(m) for m in models}
print('PIN_GATE_OK', json.dumps({m.split('/')[-1]: [revs[m][:12], pinned_utc[m]] for m in models}), flush=True)
tok = AutoTokenizer.from_pretrained(a.base, revision=revs[a.base])
model = AutoModelForCausalLM.from_pretrained(a.base, revision=revs[a.base], dtype=torch.bfloat16, device_map='cuda')
env = {'python': platform.python_version(), 'torch': torch.__version__, 'transformers': transformers.__version__,
       'peft': peft.__version__, 'gpu': torch.cuda.get_device_name(0), 'os': platform.platform()}

def generate(m, user):
    msgs = [{'role': 'system', 'content': SYS}, {'role': 'user', 'content': user}]
    prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    ids = tok(prompt, return_tensors='pt').to(m.device)
    with torch.no_grad():
        out = m.generate(**ids, max_new_tokens=a.max_new_tokens, do_sample=False)
    return tok.decode(out[0][ids['input_ids'].shape[1]:], skip_special_tokens=True)

def run(name, m):
    t0 = time.time(); resp = []
    for i, p in enumerate(probes):
        txt = generate(m, user_turn(p)); resp.append({'id': p['id'], 'text': txt, 'sha256': hashlib.sha256(txt.encode()).hexdigest()})
        print(f'  {name} v3 {i+1}/{len(probes)} {time.time()-t0:.0f}s', flush=True)
    slug = 'base' if name == a.base else name.split('/')[-1].replace('szl-provenance-native-', '').replace('-lora', '')
    run_doc = {'kind': 'szl.provenance-native/conflict-v3-run', 'model': name, 'model_revision': revs[name],
               'base': a.base, 'base_revision': revs[a.base], 'probe_set_sha256': sha_file(a.probes),
               'grader_sha256': sha_file(grader.__file__), 'corpus_sha256': corpus_sha, 'env': env,
               'decode': f'greedy, max_new_tokens={a.max_new_tokens}', 'preregistered_utc': PREREG_UTC,
               'model_revision_commit_utc': pinned_utc[name], 'repo_head_at_run': infos[name].sha,
               'repo_last_modified_at_run': infos[name].last_modified.isoformat(), 'amendment': 'A1', 'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               'responses': resp, 'signature': 'UNSIGNED'}
    Path(f'{a.outdir}/run-{slug}.json').write_text(json.dumps(run_doc, indent=1), encoding='utf-8')
    s = grader.summarize(probes, {r['id']: r['text'] for r in resp})
    print('RESULT', slug, json.dumps({'per_kind': s['per_kind'], 'fabricated': s['fabricated_total'],
          'false_conflict_on_consistent': s['false_conflict_on_consistent']}), flush=True)

run(a.base, model)
names = a.adapters.split(',')
pm = PeftModel.from_pretrained(model, names[0], revision=revs[names[0]], adapter_name='a0')
for i, n in enumerate(names):
    if i: pm.load_adapter(n, revision=revs[n], adapter_name=f'a{i}')
    pm.set_adapter(f'a{i}')
    run(n, pm)
print('CONFLICT_V3_DONE', flush=True)
