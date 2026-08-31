# artifacts/model/ — default model artifact dir (model-publish-gate)

The workflow's default `model_dir` input points here. Drop the export
(safetensors + config + tokenizer; NO .pkl/.pt/pytorch_model.bin — the scan
gate rejects unpickleable formats) in this tree, or pass a different
`model_dir` at workflow_dispatch.
