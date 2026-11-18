# Hugging Face model / dataset / interactive Space release handoff

**Not published by creating this source tree.** Current ChatGPT-connected Hugging Face OAuth (checked 2026-11-17) granted `read-repos`, `jobs`, `read-mcp`, etc., **not write-repos**. Do not evade this limitation through a secondary token, a compute job, another owner identity, or an unreviewed CI secret. An owner-approved write connection and exact source admission are prerequisites.

## Intended public Hub repositories

- Dataset: `SZLHOLDINGS/khipu-yachay-research-v0` (540/80 synthetic intent examples; 702 pinned OKR archival-ID references; 14 attributed source registry entries; rights and caveats).
- Model: `SZLHOLDINGS/SZL-Khipu-Yachay-Nano` (small actually trained Naive Bayes intent router; NOT the existing 1.5B Khipu model, NOT a historical decoder).
- Space: `SZLHOLDINGS/khipu-yachay` (Docker Python + JavaScript interactive synthetic cord demonstrations, local source search, source citations and JSON receipts).

## Source-gated release procedure

1. Normal GitHub owner DCO, CI and review; source under `szl-holdings/szl-khipu/research/khipu_yachay/`. Do not merge draft PRs #118 or #119 by surprise. If main changes, rebase or re-evaluate the exact expected parent under a new PR.
2. Verify source hash, model weight/config JSON, exact training/evaluation dataset byte SHA-256, and the published OKR source tag/blob. Explicitly separate the MIT repository source licence and other contributors' cultural rights.
3. `python research/khipu_yachay/scripts/stage_release.py --reviewed-source-sha <40hex> --out <new private directory>` on the reviewed GitHub tree. This tool ONLY stages three local directories; it does not contact the Hub or initiate jobs.
4. With an authorized Hub **write-repos** identity, inspect existing repo IDs before creating anything; don't overwrite sibling files or existing versions. Create repos only if unowned/absent. Upload at an expected parent revision and read back the immutable HF commit/file sizes/digests. The staging `SOURCE_BINDING.json` must be updated by the reviewed publisher to reflect a **completed** release; `STAGED_NOT_UPLOADED` must never be called deployed. Do not publish a one-off model as trained on historical objects.
5. Run the Space with a pinned, supported Docker image **digest** (the Space Dockerfile now pins `python:3.12.16-slim` by index digest and sets `HOST=0.0.0.0`, without which the loopback-bound server is unreachable through the Space router; the pin is necessary, not sufficient, for release admission), no secrets in the image, no external model downloads, no runtime access to GitHub or unreviewed source data. Read back `api/healthz` plus an actual synthetic `/api/analyze`, rendering, layout and accessibility via an authorized browser, then record runtime and model hashes.
6. Rollback/disable on an identity mismatch, rights error, unknown source, unverified asset or failed user-content boundary. Never auto-train new weights from incoming chats or newly discovered links.

**Main risks:** unrelated rights held by museum photographers and Indigenous communities; dataset leakage/archival confounders; unknown historic meanings; scoring of synthetic template questions versus genuine Q&A; runtime image reproducibility and provider permissions. None is resolved just by an HTTP 200.
