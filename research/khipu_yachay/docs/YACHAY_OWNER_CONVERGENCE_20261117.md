# Khipu Yachay owner-convergence note\n\n### Concurrent source-owner convergence

During this review, PR #121 advanced from `b16cc3e3...` to
`fb6e145b...`. The owner added the **correct independent**
`.gitattributes` protection (`-text` for JSON/JSONL) plus a separate
52-case developer-post-hoc stress fixture, score script and tests. This
follow-up **does not replace those files**, retrain the model or rewrite that
owner's tests. It tightens runtime/release asset admission, and the stager now
copies only the five explicitly reviewed public data files into the dataset
and Space, excluding `posthoc_ood_v0.jsonl`.

The owner-authored post-hoc fixture reported **24/40** in-domain routes and
**5/12** OOD abstentions; the separately pre-registered 100-case diagnostic
above reported **27/50** and **13/30** OOD abstentions. Both are
developer/post-hoc, not sealed; together they reinforce the HOLD without
supporting an independent quality estimate.
