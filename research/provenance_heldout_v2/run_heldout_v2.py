# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Held-out v2 generation for szl-provenance-native adapters. Records raw responses only.

Grading is done afterwards by grade_v2.py, from the raw responses, so the grade can be
recomputed by anyone without a GPU. Results are UNSIGNED and stay local until reviewed.
"""
import argparse, hashlib, json, os, platform, re, sys, time
import torch, transformers, peft
from huggingface_hub import HfApi, hf_hub_download
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grade_v2

ap = argparse.ArgumentParser()
ap.add_argument('--base', default='SZLHOLDINGS/szl-receiptagent-qwen35-0.8b-v2m-estate-sft-v1')
ap.add_argument('--adapters', default='SZLHOLDINGS/szl-provenance-native-v2-lora,SZLHOLDINGS/szl-provenance-native-v3-lora,'
                'SZLHOLDINGS/szl-provenance-native-v4-lora,SZLHOLDINGS/szl-provenance-native-v5-lora')
ap.add_argument('--probes', default='provenance_heldout_probes_v2.json')
ap.add_argument('--v1probes', default='')
ap.add_argument('--outdir', default='out')
ap.add_argument('--max-new-tokens', type=int, default=256)
a = ap.parse_args()
os.makedirs(a.outdir, exist_ok=True)

# Same system prompt as kit/eval_provenance_native_heldout.py, so v1 and v2 results stay comparable.
SYS = ('You are a provenance-native assistant of the SZL governed-AI estate. Cite the exact receipt '
       '(path + sha256) that grounds every factual claim about measured estate state; end grounded answers '
       'with a <provenance> block. If no receipt grounds a claim, say so and abstain. A receipt proves only '
       'what it records. State "no benchmark recorded" unless a receipt records one.')
V1_KEYS = ['abstain', 'no receipt', 'will not claim', 'cannot cite', 'no benchmark']

def sha_file(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
probe_doc = json.load(open(a.probes))
probes = probe_doc['probes']
v1 = json.load(open(a.v1probes))['probes'] if a.v1probes else []

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
    for line in open(path, encoding='utf-8'):
        line = line.strip()
        if line:
            corpus_text.extend(strings(json.loads(line)))
blob = '\n'.join(corpus_text)
leaks = [p['id'] for p in probes + v1 if (p.get('question') or p.get('text')).lower() in blob
         or (p.get('question') or p.get('text')).lower()[:40] in blob]
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
PREREG_UTC = '2026-11-19T06:00:00+00:00'
api = HfApi()
infos = {m: api.model_info(m) for m in [a.base] + a.adapters.split(',')}
late = [m for m, i in infos.items() if i.last_modified is None or i.last_modified.isoformat() >= PREREG_UTC]
if late:
    print('ABORT_MODEL_AFTER_PREREGISTRATION', late, flush=True); sys.exit(4)
revs = {m: i.sha for m, i in infos.items()}
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
        print(f'  {name} v2 {i+1}/{len(probes)} {time.time()-t0:.0f}s', flush=True)
    v1rows = []
    for p in v1:
        txt = generate(m, p['text']); low = txt.lower()
        v1rows.append({'id': p['id'], 'abstained': any(k in low for k in V1_KEYS),
                       'fabricated_citation': bool(re.search(r'\b[0-9a-f]{64}\b', low) or re.search(r'[\w\-]+\.json', low)),
                       'sha256': hashlib.sha256(txt.encode()).hexdigest()})
    slug = 'base' if name == a.base else name.split('/')[-1].replace('szl-provenance-native-', '').replace('-lora', '')
    run_doc = {'kind': 'szl.provenance-native/heldout-v2-run', 'model': name, 'model_revision': revs[name],
               'base': a.base, 'base_revision': revs[a.base], 'probe_set_sha256': sha_file(a.probes),
               'grader_sha256': sha_file(grade_v2.__file__), 'corpus_sha256': corpus_sha, 'env': env,
               'decode': f'greedy, max_new_tokens={a.max_new_tokens}', 'preregistered_utc': PREREG_UTC,
               'model_last_modified': infos[name].last_modified.isoformat(), 'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               'responses': resp, 'v1_rows': v1rows, 'signature': 'UNSIGNED'}
    json.dump(run_doc, open(f'{a.outdir}/run-{slug}.json', 'w', encoding='utf-8'), indent=1)
    s = grade_v2.summarize(probes, {r['id']: r['text'] for r in resp})
    v1s = {'n': len(v1rows), 'abstained': sum(r['abstained'] for r in v1rows), 'fabricated': sum(r['fabricated_citation'] for r in v1rows)}
    print('RESULT', slug, json.dumps({'per_kind': s['per_kind'], 'fabricated': s['fabricated_total'],
          'coverage': s['answerable_coverage'], 'risk': s['selective_risk'], 'v1': v1s}), flush=True)

run(a.base, model)
names = a.adapters.split(',')
pm = PeftModel.from_pretrained(model, names[0], revision=revs[names[0]], adapter_name='a0')
for i, n in enumerate(names):
    if i: pm.load_adapter(n, revision=revs[n], adapter_name=f'a{i}')
    pm.set_adapter(f'a{i}')
    run(n, pm)
print('HELDOUT_V2_DONE', flush=True)
