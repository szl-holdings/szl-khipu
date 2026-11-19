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
import threading
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


def canon_strict(obj: Any) -> str:
    """canon() for receipts: refuses NaN/inf, non-str keys and unsupported types.

    Lenient canon() maps those onto strings, so distinct payloads would share a digest.
    Supported inputs give the same bytes as canon().
    """
    return _canon(obj, strict=True)


def _canon(value: Any, strict: bool = False) -> str:
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
            if strict:
                raise ValueError("non-finite float refused in receipt")
            return json.dumps(str(f), ensure_ascii=True)
        return json.dumps(f)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=True)
    if isinstance(value, np.ndarray):
        return _canon(value.tolist(), strict)
    if isinstance(value, dict):
        if strict:
            for k in value:
                if not isinstance(k, str):
                    raise TypeError(
                        f"non-str key of type {type(k).__name__} refused in receipt"
                    )
        items = {str(k): v for k, v in value.items()}
        keys = sorted(items)
        inner = ",".join(
            f"{json.dumps(k, ensure_ascii=True)}:{_canon(items[k], strict)}" for k in keys
        )
        return "{" + inner + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_canon(v, strict) for v in value) + "]"
    if is_dataclass(value) and not isinstance(value, type):
        return _canon(asdict(value), strict)
    if isinstance(value, Mapping):
        return _canon(dict(value), strict)
    if strict:
        raise TypeError(f"unsupported type {type(value).__name__} refused in receipt")
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
    """Raises ValueError/TypeError on payloads canon_strict refuses."""
    return sha256_hex(canon_strict(_body(rec)))


class UnifiedReceiptChain:
    """Append-only receipt chain. Fail-closed on any break.

    emit() refuses NaN/inf, non-str dict keys and unsupported types before a
    receipt is appended (see canon_strict).
    """

    def __init__(self) -> None:
        self._receipts: list[Receipt] = []
        # One chain is shared by ThreadingHTTPServer handlers; unserialized appends fork prev/seq.
        self._lock = threading.Lock()

    @property
    def receipts(self) -> list[Receipt]:
        with self._lock:
            return list(self._receipts)

    @property
    def head(self) -> str:
        with self._lock:
            return self._receipts[-1].digest if self._receipts else ZERO

    def emit(self, kernel: str, op: str, attrs: Mapping[str, Any] | None = None) -> Receipt:
        payload = deepcopy(dict(attrs or {}))
        with self._lock:
            rec = Receipt(
                seq=len(self._receipts),
                op=str(op),
                kernel=str(kernel),
                payload=payload,
                digest="",
                prev=self._receipts[-1].digest if self._receipts else ZERO,
                alg="SHA-256",
                note=DIGEST_NOTE,
            )
            rec.digest = receipt_digest(rec)
            self._receipts.append(rec)
            return rec

    def verify(self) -> tuple[bool, int, int]:
        """Return (ok, depth, break_index). break_index is -1 when ok."""
        with self._lock:
            snap = list(self._receipts)
        prev = ZERO
        depth = len(snap)
        for i, rec in enumerate(snap):
            if rec.prev != prev:
                return False, depth, i
            if rec.alg != "SHA-256":
                return False, depth, i
            try:
                digest = receipt_digest(rec)
            except (ValueError, TypeError):
                return False, depth, i
            if digest != rec.digest:
                return False, depth, i
            prev = rec.digest
        return True, depth, -1

    def reset(self) -> None:
        with self._lock:
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
