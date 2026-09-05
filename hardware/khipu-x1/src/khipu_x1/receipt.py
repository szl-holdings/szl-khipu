"""Ordered SHA3-256 receipt chain for the KHIPU software reference."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping

from .kids import canonical_json_bytes

GENESIS = "0" * 64


class ReceiptVerificationError(ValueError):
    pass


def sha3_hex(data: bytes) -> str:
    return hashlib.sha3_256(data).hexdigest()


class ReceiptChain:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    @property
    def head(self) -> str:
        return self.events[-1]["digest"] if self.events else GENESIS

    def append(self, kind: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        parent = self.head
        body = {
            "index": len(self.events),
            "kind": str(kind),
            "parent": parent,
            "payload": copy.deepcopy(dict(payload)),
        }
        digest = sha3_hex(bytes.fromhex(parent) + canonical_json_bytes(body))
        event = {**body, "digest": digest}
        self.events.append(event)
        return copy.deepcopy(event)

    def verify(self) -> tuple[bool, int | None, str | None]:
        parent = GENESIS
        for index, event in enumerate(self.events):
            if event.get("index") != index:
                return False, index, "INDEX_MISMATCH"
            if event.get("parent") != parent:
                return False, index, "PARENT_MISMATCH"
            body = {
                "index": event.get("index"),
                "kind": event.get("kind"),
                "parent": event.get("parent"),
                "payload": event.get("payload"),
            }
            expected = sha3_hex(bytes.fromhex(parent) + canonical_json_bytes(body))
            if event.get("digest") != expected:
                return False, index, "DIGEST_MISMATCH"
            parent = expected
        return True, None, None

    def require_valid(self) -> None:
        ok, index, reason = self.verify()
        if not ok:
            raise ReceiptVerificationError(f"receipt chain invalid at {index}: {reason}")

    def as_dict(self) -> dict[str, Any]:
        ok, index, reason = self.verify()
        return {
            "algorithm": "SHA3-256",
            "genesis": GENESIS,
            "head": self.head,
            "depth": len(self.events),
            "verified": ok,
            "first_break": index,
            "reason": reason,
            "events": copy.deepcopy(self.events),
        }
