# SZL-Khipu-Yachay-Nano — model card (training artifact, research only)

**Artifact class:** trained **Multinomial Naive Bayes** intent router, **not a generative language model** or a fine-tuned historical Khipu decoder. It is distinct from `SZLHOLDINGS/SZL-Khipu-1.5B`, `KHIPU-R2` and the separate `szl-khipu` NumPy kernel software.

**Name:** *Yachay* is a Quechua word for “knowledge” (see Rosaleen Howard's lexical scholarship). The title acknowledges linguistic inspiration; it is not an Indigenous-authorship, translation, endorsement or decipherment claim. Research with Andean communities is a required next step.

## Architecture and training

- Multinomial Naive Bayes over Unicode-aware tokenized English/Spanish-character word strings; additive Laplace smoothing (`α=1.0`). The training script contains no network or GPU call and emits a deterministic `model/yachay_nb_v0.json` with trained log-likelihoods and priors.
- 540 **synthetic authored** training prompts; 80 synthetic held-out-template evaluation prompts; **zero archaeological samples and zero copyrighted article text in training**. Five intent labels: `NUMERACY`, `RECORDS`, `RESEARCH_LIMITS`, `DATA_RIGHTS`, `METHODS`.
- A modern deterministic arithmetic checker is an independent component. The trained model only selects a curated source summary; its probability is **not calibrated factual confidence**, authorization, or a substitute for independent historical verification.
- A first curriculum scored 30/80 (37.5%); after author revisions the final curriculum scored 76/80 (95.0%). Since the same developer saw evaluation feedback and edited the data generator, this **is not a clean prospective held-out quality estimate**. Preserve both run receipts for transparency.

## Measured result (synthetic-only, developer influenced)

- Final evaluation: **76 / 80 = 95.0%**, macro F1 **0.9597**, evaluated on five 16-example synthetic intent groups.
- Historical khipu decoding: **NOT TESTED**. Quechua fluency: **NOT TESTED**. Generalization to actual user requests: **NOT QUALIFIED**. Calibration: **NOT TESTED**. Hallucination or bias robustness: **NOT QUALIFIED**.
- The confidence-like routing score can be overconfident; an OOD low-coverage abstention gate exists but is not a safety guarantee.

## Limitations and releases

No large-language-model training, no new 1.5B weights, no verified Hugging Face model commit or live Space, no deployed production runtime. Historical KH identifiers are a separately attributed index and are **never used as supervised labels**. The model must not be promoted based on this short template test. Publish only after source owner DCO/required checks, rights review, model/dataset hashes and independent online readback. If training is extended to LoRA, pin a compatible base, exact dataset revisions, rights, held-out data, and a separate GPU budget; prior Khipu abstention weaknesses must remain blockers until genuinely measured improvements.

## Additional post-hoc stress evidence (November 17, 2026)

An **assistant-authored, non-blind** challenge of 52 novel questions was created **after inspecting the training and development templates**. It is not an independently sealed evaluation or a scientifically validated study of Andean archival sources. The challenge is retained in `data/posthoc_ood_v0.jsonl` and can be reproduced without retraining using `python -B scripts/score_posthoc.py`.

At the unchanged trained-weight SHA-256 `bf346facd30fa7abdabdb2dc8f5aa67058c122f98a7cf2b2d626f5cd03470646`, the candidate routed **24 of 40** hand-labeled in-domain questions correctly (**60.0%**) and abstained on **5 of 12** unrelated out-of-domain questions (**41.7%**); the other seven out-of-domain prompts received an unsupported in-domain label. This contrasts with the developer-influenced template result of 76/80 (95.0%). The fixed challenge bytes are `41ef4eeabfb1ed12e42e659aff39fa32f405474e59e973c7ff6f0090751b9838` (SHA-256).

**Disposition: HOLD for generalization and safety claims.** The post-hoc set is evaluation-only, not admissible for training, curriculum tuning, preference learning or a claim of prospective blinded model accuracy. The router score is **not a calibrated factual probability**. A new separately authored, protected, rights-reviewed prospective holdout with explicit abstention criteria and independent adjudication must qualify any future model revision. The application and corpus remain a research demonstration, not a deployable archaeological interpretation system.
