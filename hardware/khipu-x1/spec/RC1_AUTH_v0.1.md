# RC1 Authorization Contract v0.1

Status: **EMULATOR CONTRACT — NO PHYSICAL ACTUATION**

The RC1 boundary separates host reasoning from future privileged physical or
hardware execution. A host submits a one-shot authorization envelope binding:

- target device;
- issuance and expiry;
- strictly increasing sequence and nonce;
- exact KIDS command-stream digest;
- model and policy digests;
- opcode allowlist;
- physical mode (`LOCK`, `OBSERVE`, `ACT`);
- key identity and explicit constraints.

The reference emulator uses `HMAC-SHA256-EMULATOR` only for deterministic tests.
It is not production signing. A production RC1 must use a separately reviewed
MCU implementation, asymmetric device/authority keys protected by a secure
element, secure boot, anti-rollback storage, constant-time cryptography,
watchdog/reset handling and electrical control over privileged outputs.

A valid correctly targeted envelope consumes its sequence/nonce even if a later
policy check blocks it. Invalid signatures and wrong-device envelopes do not
consume state. Every decision emits a tamper-evident receipt; an ALLOW receipt in
the emulator does **not** mean electrical actuation occurred.
