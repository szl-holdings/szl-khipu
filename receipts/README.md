# receipts/ — admission & publication receipts

`dataset-admission.json` records the sha256 dataset digest that was admitted
into training (see `scripts/dataset_digest.py`); Gate 1 asserts the recomputed
digest matches it. Publication receipts anchored by `scripts/anchor_receipt.py`
(SZL ledger, dry-run until the ledger client lands) belong here too.
