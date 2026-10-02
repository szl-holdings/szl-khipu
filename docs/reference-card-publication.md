# Publish one reviewed fixture card

`scripts/publish_reference_card.py` is the explicit consumer for the paired
chakana, qantu, tinku and waman authoring cards. It manages one `README.md` per
invocation. It is separate from the existing main-push `publish-hf` bundle and
does not introduce an automatic writer, model admission, inference or training.

Validate source offline from a checkout of the reviewed exact source commit:

```sh
python scripts/publish_reference_card.py --model chakana --source-sha "$SOURCE_SHA"
```

For publication, first complete the repository's source PR, required CI and
normal merge. Refresh canonical GitHub main and the target's exact Hub main SHA,
immutable README digest and non-README file metadata. Review the whole README
diff, including limitations and intended-organ disambiguation. Check that no
other active writer owns the target. The CLI metadata guard additionally rejects
removed fields, tags, license changes and promotion of publication eligibility.
Only the documented receipt-binding field may advance to the dated observed
fixture check; that update is not training or model qualification.

Use an isolated environment with `huggingface_hub==1.29.0` and `PyYAML==6.0.3`.
Use the existing authorized Hub cache or environment credential. Credentials
are never command-line arguments, receipts or source files.

```sh
python scripts/publish_reference_card.py --model chakana --source-sha "$SOURCE_SHA" \
  --expected-hf-parent "$REVIEWED_HF_PARENT" \
  --expected-readme-sha256 "$REVIEWED_README_SHA256" \
  --receipt "$NEW_RECEIPT_PATH" --apply
```

The receipt directory must exist and the receipt path must be new. The local
lock prevents this checkout from invoking a second writer; exact provider parent
binding is the protection against other checkouts and remote writers. Source
and publisher bytes must still match canonical main before credential acquisition
and each mutation. Observations across GitHub and Hugging Face are separate;
these checks do not create an atomic transaction across providers.

The pinned SDK can optimize away a file addition and return another writer's
head without sending a parent-conditional commit. An initial-false / final-true
`CommitOperationAdd._is_committed` marker confirms the reviewed pinned SDK
actually submitted the mutation. An unavailable marker, unsupported version,
HTTP conflict, ambiguous response or changed head fails closed. The offline
regression calls the pinned SDK with transport mocked and verifies both real
control-flow paths. SDK upgrades require reviewing and replacing this contract.
The public parent-binding API is documented by
[Hugging Face](https://huggingface.co/docs/huggingface_hub/package_reference/hf_api#huggingface_hub.HfApi.create_commit).

Every accepted write requires exact README byte readback at its returned immutable
SHA, identical non-README blob/LFS manifests and a current-head check. A matching
README creates no commit and requires a second head check. That observation is
not a branch lock. An error may follow an accepted commit: the checkpoint then
retains the returned revision or `MUTATION_ATTEMPTED` state. Never blindly retry;
refresh and reconcile the target and receipt first. This CLI never retries writes.

The 2026-10-02 UTC fixture report records actual digest and finite-array checks
of four small NumPy archives at their declared exact Hub revisions. It is byte
and array evidence, not a reproduced training run, signer validation, qualified
held-out evaluation, rights clearance, runtime deployment or production release.
