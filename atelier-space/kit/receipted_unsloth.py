#!/usr/bin/env python3
# receipted_unsloth.py
# Silhouette: Unsloth FastLanguageModel QLoRA.
# Cut: dataset SHA, LoRA knobs, seed, and final loss go into a training receipt
# BEFORE merge. GGUF is derived — never the signed object.

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--data", default="doctrine.jsonl")
    ap.add_argument("--out", default="out/adapter")
    ap.add_argument("--r", type=int, default=16)
    ap.add_argument("--seed", type=int, default=20260721)
    ap.add_argument("--max-seq", type=int, default=2048)
    args = ap.parse_args()

    data_sha = sha256_file(Path(args.data))
    from unsloth import FastLanguageModel
    from datasets import load_dataset
    from trl import SFTConfig, SFTTrainer

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.base,
        max_seq_length=args.max_seq,
        load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=args.r,
        lora_alpha=args.r,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=args.seed,
    )
    ds = load_dataset("json", data_files=args.data, split="train")
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=ds,
        args=SFTConfig(
            output_dir=args.out,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            max_steps=120,
            learning_rate=2e-4,
            logging_steps=10,
            seed=args.seed,
        ),
    )
    t0 = time.time()
    trainer.train()
    model.save_pretrained(args.out)
    loss = None
    if trainer.state.log_history:
        last = trainer.state.log_history[-1]
        loss = last.get("train_loss") or last.get("loss")
    receipt = {
        "schema": "szl.training_receipt.v1",
        "base": args.base,
        "dataset_sha256": data_sha,
        "lora": {"r": args.r, "alpha": args.r, "targets": "q,k,v,o,gate,up,down"},
        "seed": args.seed,
        "final_loss": loss,
        "seconds": round(time.time() - t0, 3),
        "note": "Sign this envelope (DSSE/Ed25519) BEFORE merge. GGUF is derived.",
    }
    Path(args.out).mkdir(parents=True, exist_ok=True)
    Path(args.out, "training_receipt.json").write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
