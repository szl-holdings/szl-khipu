# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""szl-provenance-native-v6 SFT (LoRA). STAGED - NOT LAUNCHED.

Corpus v0.5 plus the v6 conflict pack (provenance_conflict_pack_v6.jsonl), with the same
recipe as v5 (LoRA r16, 3 epochs, lr 1e-4). It refuses to start unless a results file
records that preregistered hypothesis H4 held (research/provenance_conflict_v3/README.md);
launching it also needs Stephen's approval by name. Evaluate v6 on a new held-out set,
never on held-out v2 or conflict v3.
"""
import argparse, hashlib, json, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--h4-result', required=True, help='JSON with {"H4": "HELD", "receipts_commit": "..."}')
ap.add_argument('--corpus', default='provenance_corpus_v05.jsonl')
ap.add_argument('--pack', default='provenance_conflict_pack_v6.jsonl')
ap.add_argument('--out-repo', default='SZLHOLDINGS/szl-provenance-native-v6-lora')
a = ap.parse_args()

PACK_SHA = '77a5963bf9fab9dab46dc3ac6ddfc9c1795896fe567cb1f92030fc4be8883029'
h4 = json.loads(Path(a.h4_result).read_text(encoding='utf-8'))
if h4.get('H4') != 'HELD' or not h4.get('receipts_commit'):
    print('ABORT_H4_NOT_HELD', h4, flush=True)
    sys.exit(3)
if hashlib.sha256(Path(a.pack).read_bytes()).hexdigest() != PACK_SHA:
    print('ABORT_PACK_CHANGED', flush=True)
    sys.exit(4)

import torch  # noqa: E402  imported after the gates so a refused run loads nothing
from datasets import concatenate_datasets, load_dataset  # noqa: E402
from peft import LoraConfig, get_peft_model  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402
from trl import SFTConfig, SFTTrainer  # noqa: E402

BASE = 'SZLHOLDINGS/szl-receiptagent-qwen35-0.8b-v2m-estate-sft-v1'
tok = AutoTokenizer.from_pretrained(BASE)
model = AutoModelForCausalLM.from_pretrained(BASE, dtype=torch.bfloat16, device_map='auto')
ds = concatenate_datasets([load_dataset('json', data_files=a.corpus, split='train'),
                           load_dataset('json', data_files=a.pack, split='train')]).shuffle(seed=20261119)
model = get_peft_model(model, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05,
                                         target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj'], task_type='CAUSAL_LM'))
ds = ds.map(lambda ex: {'text': tok.apply_chat_template(ex['messages'], tokenize=False)})
cfg = SFTConfig(output_dir='./pn-v6', per_device_train_batch_size=2, gradient_accumulation_steps=8,
                learning_rate=1e-4, num_train_epochs=3, bf16=True, logging_steps=5, save_strategy='epoch',
                report_to=[], seed=20261119)
SFTTrainer(model=model, train_dataset=ds, args=cfg, processing_class=tok).train()
model.save_pretrained('./pn-v6')
model.push_to_hub(a.out_repo, private=True)
print('DONE v6 - UNSIGNED; evaluate on a new held-out set before any claim.', flush=True)
