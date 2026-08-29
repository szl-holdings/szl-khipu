#!/usr/bin/env python3
# The model never sees node content. Handles only.
# Output is a typed plan: NAVIGATE | ABSTAIN.

from __future__ import annotations

import json

from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = "SZLHOLDINGS/SZL-Khipu-1.5B"

tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype="auto", device_map="auto")

payload = {
    "query": "Where is the lambda-gate defined?",
    "candidates": [
        {"id": "n-formulas", "kind": "kernel", "label": "szl-formulas"},
        {"id": "n-gate", "kind": "kernel", "label": "szl-lambda-gate"},
    ],
}
messages = [
    {
        "role": "system",
        "content": "Emit khipu.schema.json. HANDLES_ONLY. If no handle supports the query, ABSTAIN.",
    },
    {"role": "user", "content": json.dumps(payload)},
]
text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
ids = tok(text, return_tensors="pt").to(model.device)
out = model.generate(**ids, max_new_tokens=256, do_sample=False)
print(tok.decode(out[0][ids["input_ids"].shape[-1] :], skip_special_tokens=True))
