# szl-khipu domain leader study r1 (propose-only)

Date: 2026-11-23. Method: web-verified leader landscape + governing-seat synthesis (Kimi nonce T3-SZL-KHIPU-BRIEF). This card is documentation only; it changes no code, CI, config, or existing PR status. All absorb actions are FUTURE PROPOSALS (non-authorizing); implementation and merges remain separately reviewed and gated.

## Domain: governed-AI trust-and-receipt kernels (advisory Lambda-gate, canal attention, hash-chained run receipts)

## Leaders studied (web-verified 2026-11-23)

1. FlashAttention (https://arxiv.org/abs/2205.14135) — IO-aware kernel tiling makes exact attention fast without approximation; moat is exactness preserved through memory-traffic engineering rather than relaxed math.
2. Sigstore Rekor (https://github.com/sigstore/rekor) — append-only software supply chain transparency log with signed tree heads and public verifiability; moat is independently checkable inclusion and consistency evidence.
3. RFC 6962 Certificate Transparency (https://datatracker.ietf.org/doc/html/rfc6962) — append-only Merkle log plus independent monitors and gossip so misbehavior is detectable between checkpoints; moat is distributed detection rather than trust in one log operator.

## Absorb actions (FUTURE PROPOSALS, non-authorizing)

1. (FlashAttention) Propose an IO-aware tiling study for YARQA canal attention that preserves the LIVE CPU NumPy 1e-9 leak bound and exact semantics, with CUDA remaining UNAVAILABLE. Any performance effect is unmeasured until a live run; no speedup is claimed.
2. (baseline) Propose receipt fixtures that keep the SHA-256 chain and `szl-khipu verify` exit-1-on-mismatch behavior authoritative while recording the advisory Lambda-gate outcome separately. Lambda remains Conjecture 1 OPEN and advisory, never a theorem; the deterministic `rule_check` remains authoritative over learned predictions, `proven_trust` remains false, and the Lean locked-proven formula count remains exactly 8.
3. (Sigstore Rekor) Propose an optional receipt-export design carrying signed tree heads and publicly verifiable inclusion/consistency evidence alongside existing hash-chained training receipts. This would not replace local digest verification or establish proven trust, and any third-party log dependency, availability cost, and verification failure mode must be measured before adoption.
4. (RFC 6962) Propose independent monitor and gossip checkpoints for published receipt logs so operator misbehavior could be detected between checkpoints. Third-party monitors remain required; local hash-chain verification alone does not provide this detection property.
5. (baseline) Propose byte-parity receipt coverage for Hub mirrors published by the publish-hf workflow, binding verification evidence to `MODEL_SOURCE_BINDING.json` without changing the stdlib HTTP server or NAVIGATE/ABSTAIN silhouette. Energy remains UNAVAILABLE and must never be fabricated; parity evidence would not imply model quality, speedup, or proven trust.

## Do not do (per governing seat)

Do not merge, bypass the signature wall, or claim implementation beyond this card.
