# data/ — dataset provenance (model-publish-gate, Gate 1)

Place `dataset-manifest.json` here before the gate's dataset-provenance job
can pass. Format:

```json
{"files": [{"path": "train/part-000.jsonl", "sha256": "<64 hex>", "...": "..."}]}
```

Paths are relative to this directory. `scripts/dataset_digest.py` recomputes
every sha256 and fails closed on a missing manifest, missing file, or digest
mismatch; `scripts/assert_digest.py` then compares the aggregate digest
against `receipts/dataset-admission.json`. The manifest lists exactly the
files admitted into training — held-out eval prompts (`eval/heldout_generate.yaml`)
must NOT appear in any training file listed here.
