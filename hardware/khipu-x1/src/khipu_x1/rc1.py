"""RC1 authorization-boundary emulator.

This module models the contract between a host and a future independent control
microcontroller. It performs no GPIO or physical actuation. HMAC is used only as
a deterministic test mechanism; production requires asymmetric keys held in a
secure element and a separately reviewed firmware implementation.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import time
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Mapping, Sequence

from .kids import Descriptor, KhipuValidationError, Opcode, canonical_json_bytes, validate_stream
from .receipt import ReceiptChain

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class RC1Mode(str, Enum):
    LOCK = "LOCK"
    OBSERVE = "OBSERVE"
    ACT = "ACT"


@dataclass(frozen=True)
class AuthorizationEnvelope:
    authorization_id: str
    device_id: str
    issued_at: int
    expires_at: int
    sequence: int
    nonce: int
    command_digest: str
    model_digest: str
    policy_digest: str
    allowed_opcodes: tuple[str, ...]
    mode: RC1Mode
    key_id: str
    signature: str = ""
    version: str = "0.1"
    algorithm: str = "HMAC-SHA256-EMULATOR"
    constraints: Mapping[str, Any] = field(default_factory=dict)

    def payload_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "algorithm": self.algorithm,
            "authorization_id": self.authorization_id,
            "device_id": self.device_id,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "sequence": self.sequence,
            "nonce": self.nonce,
            "command_digest": self.command_digest,
            "model_digest": self.model_digest,
            "policy_digest": self.policy_digest,
            "allowed_opcodes": list(self.allowed_opcodes),
            "mode": self.mode.value,
            "key_id": self.key_id,
            "constraints": dict(self.constraints),
            "production_eligible": False,
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self.payload_dict(), "signature": self.signature}


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason: str
    authorization_id: str
    envelope_digest: str
    receipt_digest: str
    mode: str
    production_eligible: bool = False
    authority: str = "RC1_EMULATOR"

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "authorization_id": self.authorization_id,
            "envelope_digest": self.envelope_digest,
            "receipt_digest": self.receipt_digest,
            "mode": self.mode,
            "production_eligible": self.production_eligible,
            "authority": self.authority,
        }


def descriptor_stream_digest(descriptors: Sequence[Descriptor]) -> str:
    if not descriptors:
        raise ValueError("descriptor stream is empty")
    validate_stream(descriptors)
    payload = {"kids_version": "0.1", "commands": [item.as_dict() for item in descriptors]}
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _sign(secret: bytes, envelope: AuthorizationEnvelope) -> str:
    if len(secret) < 16:
        raise ValueError("emulator secret must be at least 16 bytes")
    return hmac.new(secret, canonical_json_bytes(envelope.payload_dict()), hashlib.sha256).hexdigest()


def issue_hmac_authorization(
    *,
    secret: bytes,
    authorization_id: str,
    device_id: str,
    issued_at: int,
    expires_at: int,
    sequence: int,
    nonce: int,
    descriptors: Sequence[Descriptor],
    allowed_opcodes: Sequence[Opcode | str],
    mode: RC1Mode = RC1Mode.ACT,
    key_id: str = "test-key",
    constraints: Mapping[str, Any] | None = None,
) -> AuthorizationEnvelope:
    if not descriptors:
        raise ValueError("descriptors are required")
    ops = tuple(sorted({(op if isinstance(op, Opcode) else Opcode(str(op))).value for op in allowed_opcodes}))
    model_digests = {descriptor.model_digest for descriptor in descriptors}
    policy_digests = {descriptor.policy_digest for descriptor in descriptors}
    if len(model_digests) != 1 or len(policy_digests) != 1:
        raise ValueError("all descriptors must share one model and policy digest")
    envelope = AuthorizationEnvelope(
        authorization_id=authorization_id,
        device_id=device_id,
        issued_at=int(issued_at),
        expires_at=int(expires_at),
        sequence=int(sequence),
        nonce=int(nonce),
        command_digest=descriptor_stream_digest(descriptors),
        model_digest=next(iter(model_digests)),
        policy_digest=next(iter(policy_digests)),
        allowed_opcodes=ops,
        mode=mode,
        key_id=key_id,
        constraints=dict(constraints or {}),
    )
    return replace(envelope, signature=_sign(secret, envelope))


class RC1Emulator:
    """Fail-closed authorization verifier with stateful anti-replay."""

    def __init__(self, *, device_id: str, key_id: str, secret: bytes, max_lifetime_s: int = 3600) -> None:
        if not _ID.fullmatch(device_id) or not _ID.fullmatch(key_id):
            raise ValueError("device_id and key_id must be bounded identifiers")
        if len(secret) < 16:
            raise ValueError("emulator secret must be at least 16 bytes")
        if max_lifetime_s <= 0:
            raise ValueError("max_lifetime_s must be positive")
        self.device_id = device_id
        self.key_id = key_id
        self._secret = bytes(secret)
        self.max_lifetime_s = int(max_lifetime_s)
        self.last_sequence = -1
        self.last_nonce = -1
        self.chain = ReceiptChain()

    def _record(self, envelope: AuthorizationEnvelope, allowed: bool, reason: str) -> AuthorizationDecision:
        envelope_digest = hashlib.sha256(canonical_json_bytes(envelope.as_dict())).hexdigest()
        event = self.chain.append(
            "authorization_allowed" if allowed else "authorization_blocked",
            {
                "authorization_id": envelope.authorization_id,
                "device_id": envelope.device_id,
                "sequence": envelope.sequence,
                "nonce": envelope.nonce,
                "mode": envelope.mode.value,
                "algorithm": envelope.algorithm,
                "key_id": envelope.key_id,
                "envelope_digest": envelope_digest,
                "command_digest": envelope.command_digest,
                "allowed": allowed,
                "reason": reason,
                "authority": "RC1_EMULATOR",
                "production_eligible": False,
                "physical_actuation": "NOT_PERFORMED",
            },
        )
        self.chain.require_valid()
        return AuthorizationDecision(
            allowed=allowed,
            reason=reason,
            authorization_id=envelope.authorization_id,
            envelope_digest=envelope_digest,
            receipt_digest=event["digest"],
            mode=envelope.mode.value,
        )

    def authorize(
        self,
        envelope: AuthorizationEnvelope,
        descriptors: Sequence[Descriptor],
        *,
        now: int | None = None,
    ) -> AuthorizationDecision:
        now = int(time.time()) if now is None else int(now)

        # Syntactic and signature checks happen before any replay state is consumed.
        if envelope.version != "0.1" or envelope.algorithm != "HMAC-SHA256-EMULATOR":
            return self._record(envelope, False, "UNSUPPORTED_AUTHORIZATION_FORMAT")
        if not _ID.fullmatch(envelope.authorization_id):
            return self._record(envelope, False, "INVALID_AUTHORIZATION_ID")
        if envelope.key_id != self.key_id:
            return self._record(envelope, False, "UNKNOWN_KEY_ID")
        expected_signature = _sign(self._secret, replace(envelope, signature=""))
        if not hmac.compare_digest(envelope.signature, expected_signature):
            return self._record(envelope, False, "SIGNATURE_INVALID")
        if envelope.device_id != self.device_id:
            return self._record(envelope, False, "DEVICE_MISMATCH")
        if envelope.sequence <= self.last_sequence or envelope.nonce <= self.last_nonce:
            return self._record(envelope, False, "REPLAY_REJECTED")

        # A valid, correctly targeted envelope consumes its one-shot identity even
        # when later policy checks block it.
        self.last_sequence = envelope.sequence
        self.last_nonce = envelope.nonce

        if envelope.issued_at > now + 30:
            return self._record(envelope, False, "NOT_YET_VALID")
        if envelope.expires_at <= now:
            return self._record(envelope, False, "EXPIRED")
        if envelope.expires_at <= envelope.issued_at or envelope.expires_at - envelope.issued_at > self.max_lifetime_s:
            return self._record(envelope, False, "INVALID_LIFETIME")
        if envelope.mode is not RC1Mode.ACT:
            return self._record(envelope, False, "MODE_NOT_ACT")
        if not descriptors:
            return self._record(envelope, False, "EMPTY_COMMAND_STREAM")

        try:
            actual_command_digest = descriptor_stream_digest(descriptors)
        except (ValueError, KhipuValidationError) as exc:
            return self._record(envelope, False, f"DESCRIPTOR_INVALID:{type(exc).__name__}")
        if actual_command_digest != envelope.command_digest:
            return self._record(envelope, False, "COMMAND_DIGEST_MISMATCH")
        if not _HEX64.fullmatch(envelope.model_digest) or not _HEX64.fullmatch(envelope.policy_digest):
            return self._record(envelope, False, "DIGEST_FIELD_INVALID")
        if any(descriptor.model_digest != envelope.model_digest for descriptor in descriptors):
            return self._record(envelope, False, "MODEL_DIGEST_MISMATCH")
        if any(descriptor.policy_digest != envelope.policy_digest for descriptor in descriptors):
            return self._record(envelope, False, "POLICY_DIGEST_MISMATCH")
        try:
            normalized_allowed = tuple(Opcode(value).value for value in envelope.allowed_opcodes)
        except ValueError:
            return self._record(envelope, False, "INVALID_OPCODE_ALLOWLIST")
        if normalized_allowed != tuple(sorted(set(normalized_allowed))):
            return self._record(envelope, False, "NONCANONICAL_OPCODE_ALLOWLIST")
        allowed = set(normalized_allowed)
        if not allowed:
            return self._record(envelope, False, "NO_ALLOWED_OPCODES")
        if any(descriptor.opcode.value not in allowed for descriptor in descriptors):
            return self._record(envelope, False, "OPCODE_NOT_AUTHORIZED")
        if envelope.constraints.get("physical_actuation") is True:
            return self._record(envelope, False, "PHYSICAL_ACTUATION_UNAVAILABLE")

        return self._record(envelope, True, "AUTHORIZED_EMULATOR_ONLY")
