# SZL Khipu Yachay · Living Cord Lab v0

**A modern, evidence-first research lab inspired by Andean khipu recordkeeping.** The source lives in `szl-holdings/szl-khipu` under this additive folder; no existing Khipu kernel, receipt signer, Lambda conjecture, trained checkpoint or protected main changes are implied by this staged copy.

The runnable components are: a 540-row synthetic training set, 80-row developer-influenced synthetic evaluation set; a genuinely trained tiny Naive Bayes intent model; an attributed index of 702 published KH IDs; 14 reviewed-link records with rights states; a deterministic arithmetic and evidence receipt checker; and a responsive stdlib Python + JS frontend/backend suitable for a reviewed Docker Hugging Face Space. The HTML string-knot rendering is deliberately a **modern symbolic sketch**, never an archaeological transcription. No downloaded source text was used to train the model.

## Run offline

```sh
cd research/khipu_yachay
python -m unittest discover -s tests -v
HOST=127.0.0.1 PORT=7860 python space/app.py
# http://127.0.0.1:7860
```

No external Python dependencies. On a computer without `python` use `python3`. The web server reads the exact model hash from the training receipt at startup and refuses an altered model. The app accepts no model uploads, training requests, model downloads, credentials or network calls to outside services.

## Training and research

Train fresh *only in an empty new experiment directory*; `src.train.write_outputs` refuses overwriting existing weights/receipts. Do not silently replace the bound model in source. This project's existing trained weights were produced with the author-controlled `src.train` generator and evaluated on separate template families, but the curriculum was revised after earlier evaluation feedback, so 95% is **not prospective** independent performance. The first 37.5% experiment is preserved under `internal/baseline_v0` in the private download bundle, not intended for an unreviewed public model release.

The licensed/public archaeological data are **indexed, not bulk-scraped or learned**. The `scripts/discover_metadata.py` command is an opt-in bounded Crossref bibliographic API probe (not executed in this offline build); output stays metadata-only pending review. To fine-tune any larger model, qualify dataset rights, source pins, budget and holdout first.

## What remains

GitHub PR admission, owner DCO; independent source and cultural review; verified HF write permission; live model/dataset/Space publication; artifact checksum, released Docker image digest, hosted runtime identity and independent evaluation. **None is implied by this README.**

See `docs/DATASET_CARD.md`, `docs/MODEL_CARD.md`, `docs/RESEARCH_REVIEW.md`, `data/okr_registry_provenance.json`, `model/training_receipt.json`.
