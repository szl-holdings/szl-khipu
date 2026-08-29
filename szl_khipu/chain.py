# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""UnifiedReceiptChain — SHA-256 silhouette of the metal SHA3-256 kernel.

Browser / this package uses SHA-256. Production metal kernels use SHA3-256.
Same receipt shape, different digest alg — labeled, not faked.
"""

from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Mapping

import numpy as np

ZERO: str = "0" * 64

DIGEST_NOTE: str = (
    "This package / browser silhouette uses SHA-256. "
    "Production metal kernels use SHA3-256. "
    "Same receipt shape, different digest alg — labeled, not faked."
)


def canon(obj: Any) -> str:
    """Sorted-key JSON with no spaces. Deterministic across nested dicts."""
    return _canon(obj)


def _canon(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (np.bool_,)):
        return "true" if bool(value) else "false"
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        return json.dumps(int(value))
    if isinstance(value, (float, np.floating)):
        f = float(value)
        if not math.isfinite(f):
            return json.dumps(str(f), ensure_ascii=True)
        return json.dumps(f)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=True)
    if isinstance(value, np.ndarray):
        return _canon(value.tolist())
    if isinstance(value, dict):
        items = {str(k): v for k, v in value.items()}
        keys = sorted(items)
        inner = ",".join(
            f"{json.dumps(k, ensure_ascii=True)}:{_canon(items[k])}" for k in keys
        )
        return "{" + inner + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_canon(v) for v in value) + "]"
    if is_dataclass(value) and not isinstance(value, type):
        return _canon(asdict(value))
    if isinstance(value, Mapping):
        return _canon(dict(value))
    return json.dumps(str(value), ensure_ascii=True)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class Receipt:
    seq: int
    op: str
    kernel: str
    payload: dict[str, Any]
    digest: str
    prev: str
    alg: str = "SHA-256"
    note: str = DIGEST_NOTE


def _body(rec: Receipt) -> dict[str, Any]:
    return {
        "seq": rec.seq,
        "op": rec.op,
        "kernel": rec.kernel,
        "payload": rec.payload,
        "prev": rec.prev,
        "alg": rec.alg,
        "note": rec.note,
    }


def receipt_digest(rec: Receipt) -> str:
    return sha256_hex(canon(_body(rec)))


class UnifiedReceiptChain:
    """Append-only receipt chain. Fail-closed on any break."""

    def __init__(self) -> None:
        self._receipts: list[Receipt] = []

    @property
    def receipts(self) -> list[Receipt]:
        return list(self._receipts)

    @property
    def head(self) -> str:
        return self._receipts[-1].digest if self._receipts else ZERO

    def emit(self, kernel: str, op: str, attrs: Mapping[str, Any] | None = None) -> Receipt:
        payload = deepcopy(dict(attrs or {}))
        rec = Receipt(
            seq=len(self._receipts),
            op=str(op),
            kernel=str(kernel),
            payload=payload,
            digest="",
            prev=self.head,
            alg="SHA-256",
            note=DIGEST_NOTE,
        )
        rec.digest = receipt_digest(rec)
        self._receipts.append(rec)
        return rec

    def verify(self) -> tuple[bool, int, int]:
        """Return (ok, depth, break_index). break_index is -1 when ok."""
        prev = ZERO
        depth = len(self._receipts)
        for i, rec in enumerate(self._receipts):
            if rec.prev != prev:
                return False, depth, i
            if rec.alg != "SHA-256":
                return False, depth, i
            if receipt_digest(rec) != rec.digest:
                return False, depth, i
            prev = rec.digest
        return True, depth, -1

    def reset(self) -> None:
        self._receipts.clear()


_GLOBAL = UnifiedReceiptChain()
ReceiptChain = UnifiedReceiptChain


def mint_receipt(
    subject: str = "khipu",
    metrics: Mapping[str, Any] | None = None,
    prev: Any = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Mint onto the process-global chain. prev is accepted and ignored (chain owns prev)."""
    del prev
    payload: dict[str, Any] = {"metrics": dict(metrics or {}), **kwargs}
    rec = _GLOBAL.emit(str(subject), "mint", payload)
    return {
        "subject": subject,
        "metrics": payload["metrics"],
        "digest": rec.digest,
        "sha256": rec.digest,
        "seq": rec.seq,
        "prev": rec.prev,
        "alg": rec.alg,
        "proven_trust": False,
        "energy_status": "UNAVAILABLE",
    }


def verify_receipt(chain: UnifiedReceiptChain | None = None) -> dict[str, Any]:
    c = chain if chain is not None else _GLOBAL
    ok, depth, break_index = c.verify()
    return {"ok": ok, "depth": depth, "break_index": break_index}


def chain_depth(chain: UnifiedReceiptChain | None = None) -> int:
    c = chain if chain is not None else _GLOBAL
    return len(c.receipts)


def write_training_receipt(path: str, payload: Mapping[str, Any]) -> str:
    import json
    from pathlib import Path

    body = dict(payload)
    body.setdefault("proven_trust", False)
    body.setdefault("energy_j", None)
    body.setdefault("energy_status", "UNAVAILABLE")
    body.setdefault("honesty", "REPORTED")
    if body.get("proven_trust") is True:
        raise ValueError("refusing proven_trust true")
    if body.get("energy_j") not in (None,):
        raise ValueError("refusing to fabricate joules")
    text = json.dumps(body, indent=2, sort_keys=True) + "\n"
    Path(path).write_text(text)
    return sha256_hex(text)
