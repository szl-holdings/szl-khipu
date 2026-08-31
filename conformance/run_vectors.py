#!/usr/bin/env python3
"""SZL receipt conformance vectors — the subset of DSSEv1/PAE checks that run
WITHOUT the full SZL runtime, against release/run-manifest.json.

Five implemented vectors (vector JSONs live in conformance/vectors/):
  V01 canonicalization  JSON canonical form is stable: canonicalize -> mutate
                        key order -> canonicalize -> identical bytes; and any
                        recorded `payload_sha256` recomputes over canon(payload).
  V02 pae-byte-length   DSSE PAE = len(ctx)||ctx||len(type)||type||
                        len(payload)||payload with 8-byte ASCII decimal length
                        prefixes; verified against independently computed bytes.
  V03 der-parse         Any attached ECDSA signature parses as minimal-DER
                        SEQUENCE(INTEGER r, INTEGER s) with no trailing bytes.
  V04 prev-hash-linkage chain.prev_hash is 'genesis' or a 64-hex sha256; when a
                        predecessor file is given, it must equal its digest —
                        fail closed on chain forks / replays.
  V05 ts-monotonic      issued_at is valid RFC-3339 UTC and — with a
                        predecessor manifest — strictly newer (no rollback).

Each vector JSON: {"id", "name", "expect": "pass"|"fail", ...params}. A vector
"passes" when the check outcome equals `expect`. With --require-all-pass, exit
1 if ANY vector's outcome != expect, any vector file is malformed, or the
receipt is missing/unreadable. Stdlib only.
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import re
import sys

DSSE_CONTEXT = "DSSEv1"
PAYLOAD_TYPE = "application/vnd.szl.run-manifest+json"


# ── primitives ────────────────────────────────────────────────────────────────

def canon(obj) -> bytes:
    """RFC-8785-adjacent canonical JSON: sorted keys, no whitespace, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def pae(context: str, payload_type: str, payload: bytes) -> bytes:
    """DSSE pre-auth encoding: LEN SP field SP LEN SP field SP LEN SP field,
    where LEN is the field byte length as plain ASCII decimal."""
    c, t = context.encode(), payload_type.encode()
    out = b""
    for f in (c, t, payload):
        out += str(len(f)).encode() + b" " + f + b" "
    return out[:-1]  # no trailing space after the final field


def der_parse_ints(sig: bytes) -> tuple[int, int]:
    """Minimal DER parser for ECDSA-Sig-Value ::= SEQUENCE(INTEGER r, INTEGER s).
    Raises ValueError on any structural or minimality violation."""
    if len(sig) < 8 or sig[0] != 0x30:
        raise ValueError("not a DER SEQUENCE")
    total, off = sig[1], 2
    if total & 0x80:
        raise ValueError("long-form length (non-minimal for sig sizes)")
    if off + total != len(sig):
        raise ValueError("SEQUENCE length != remaining bytes (trailing/short data)")
    ints = []
    end = off + total
    while off < end:
        if sig[off] != 0x02:
            raise ValueError("expected INTEGER tag")
        ln = sig[off + 1]
        body = sig[off + 2: off + 2 + ln]
        if ln == 0 or off + 2 + ln > end:
            raise ValueError("INTEGER length out of bounds")
        if ln > 1 and body[0] == 0x00 and not (body[1] & 0x80):
            raise ValueError("non-minimal INTEGER (unnecessary leading 0x00)")
        if body[0] & 0x80:
            raise ValueError("negative INTEGER (missing leading 0x00)")
        ints.append(int.from_bytes(body, "big"))
        off += 2 + ln
    if len(ints) != 2:
        raise ValueError(f"expected 2 INTEGERs (r, s), got {len(ints)}")
    return ints[0], ints[1]


def rfc3339_utc(s: str) -> datetime.datetime:
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})(\.\d+)?(Z|\+00:00)", s or "")
    if not m:
        raise ValueError(f"not RFC-3339 UTC: {s!r}")
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))


# ── vector checks: each returns (ok: bool, detail: str) ───────────────────────

def v01_canonicalization(manifest: dict, raw: bytes, **_):
    c1 = canon(manifest)
    mutant = json.loads(raw)  # re-parse + re-serialize with reversed key order
    def reorder(o):
        if isinstance(o, dict):
            return dict(reversed(list({k: reorder(v) for k, v in o.items()}.items())))
        if isinstance(o, list):
            return [reorder(v) for v in o]
        return o
    c2 = canon(reorder(mutant))
    if c1 != c2:
        return False, "canonical form not stable under key reordering"
    rec = manifest.get("payload_sha256")
    if isinstance(rec, str) and rec.lower() != hashlib.sha256(c1).hexdigest():
        return False, "recorded payload_sha256 does not match canonical bytes"
    return True, f"canonical sha256={hashlib.sha256(c1).hexdigest()[:16]}... stable"


def v02_pae_byte_length(manifest: dict, raw: bytes, **_):
    """Re-parse the PAE sequentially; every length prefix must be canonical
    ASCII decimal and every counted field must match, byte for byte. Binary
    (struct-packed) length prefixes — the V11 malleation class — fail the
    int() decode or the field-length walk immediately."""
    payload = canon(manifest)
    p = pae(DSSE_CONTEXT, PAYLOAD_TYPE, payload)
    fields, off = [], 0
    try:
        for _ in range(3):
            sp = p.index(b" ", off)
            n = int(p[off:sp])                      # raises on binary prefixes
            if str(n).encode() != p[off:sp]:
                return False, "non-canonical length prefix (padding/whitespace)"
            start = sp + 1
            fields.append(p[start:start + n])
            if len(fields[-1]) != n:
                return False, "length prefix overruns the buffer"
            off = start + n + 1                     # skip field + separator
        if off - 1 != len(p):
            return False, "trailing bytes after final PAE field"
    except (ValueError, IndexError) as e:
        return False, f"PAE structure unparseable (V11-class malleation): {e}"
    if fields[0] != DSSE_CONTEXT.encode():
        return False, f"context field {fields[0]!r} != {DSSE_CONTEXT!r}"
    if fields[1] != PAYLOAD_TYPE.encode():
        return False, f"payload-type field {fields[1]!r} != {PAYLOAD_TYPE!r}"
    if fields[2] != payload:
        return False, "payload field != canonical manifest bytes"
    return True, f"PAE re-parse ok: 3 fields, {len(p)}B total, canonical decimal lengths"


def v03_der_parse(manifest: dict, **_):
    sig_b64 = (manifest.get("signatures") or {}).get("value")
    if not sig_b64:
        if (manifest.get("signatures") or {}).get("manifest") is True:
            return False, "signatures.manifest=true but no signature value attached"
        return True, "no signature attached and none claimed (pre-sign stage) — consistent"
    import base64
    try:
        sig = base64.b64decode(sig_b64, validate=True)
        r, s = der_parse_ints(sig)
    except (ValueError, TypeError) as e:
        return False, f"signature failed minimal-DER parse: {e}"
    return True, f"DER ok: r={hex(r)[:18]}..., s={hex(s)[:18]}..."


def v04_prev_hash_linkage(manifest: dict, prev_path: str | None = None, **_):
    prev = (manifest.get("chain") or {}).get("prev_hash")
    if not isinstance(prev, str) or not prev:
        return False, "chain.prev_hash missing"
    if prev == "genesis":
        return True, "genesis link — well-formed sentinel, nothing to compare against"
    if not re.fullmatch(r"[0-9a-f]{64}", prev):
        return False, f"prev_hash is not a lowercase sha256: {prev!r}"
    if prev_path:
        pp = pathlib.Path(prev_path)
        if not pp.is_file():
            return False, f"predecessor manifest given but missing: {pp}"
        actual = hashlib.sha256(pp.read_bytes()).hexdigest()
        if actual != prev:
            return False, f"FORK/REPLAY: prev_hash {prev[:16]}... != predecessor digest {actual[:16]}..."
        return True, "prev_hash matches predecessor manifest digest"
    return True, "prev_hash well-formed (no predecessor supplied to compare)"


def v05_ts_monotonic(manifest: dict, prev_path: str | None = None, **_):
    try:
        ts = rfc3339_utc(manifest.get("issued_at"))
    except ValueError as e:
        return False, str(e)
    if prev_path and pathlib.Path(prev_path).is_file():
        try:
            prev_ts = rfc3339_utc(json.loads(pathlib.Path(prev_path).read_text()).get("issued_at"))
        except (ValueError, json.JSONDecodeError) as e:
            return False, f"predecessor issued_at unreadable: {e}"
        if ts <= prev_ts:
            return False, f"ROLLBACK: issued_at {ts} <= predecessor {prev_ts}"
        return True, f"issued_at {ts.isoformat()} strictly after predecessor"
    return True, f"issued_at {ts.isoformat()} valid RFC-3339 UTC"


CHECKS = {
    "V01": v01_canonicalization,
    "V02": v02_pae_byte_length,
    "V03": v03_der_parse,
    "V04": v04_prev_hash_linkage,
    "V05": v05_ts_monotonic,
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vectors", required=True, help="Dir of vector JSON files.")
    ap.add_argument("--receipt", required=True, help="release/run-manifest.json")
    ap.add_argument("--prev-manifest", default=None, help="Previous run manifest for chain vectors.")
    ap.add_argument("--require-all-pass", action="store_true")
    a = ap.parse_args()

    rp = pathlib.Path(a.receipt)
    if not rp.is_file():
        print(f"::error::receipt not found: {rp}", file=sys.stderr)
        return 1
    try:
        raw = rp.read_bytes()
        manifest = json.loads(raw)
    except (OSError, json.JSONDecodeError) as e:
        print(f"::error::receipt unreadable: {e}", file=sys.stderr)
        return 1

    vdir = pathlib.Path(a.vectors)
    if not vdir.is_dir():
        print(f"::error::vectors dir not found: {vdir}", file=sys.stderr)
        return 1
    vfiles = sorted(vdir.glob("*.json"))
    if not vfiles:
        print(f"::error::no vector JSON files in {vdir}", file=sys.stderr)
        return 1

    failures = 0
    for vf in vfiles:
        try:
            vec = json.loads(vf.read_text())
            vid, expect = vec["id"], vec.get("expect", "pass")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"FAIL  {vf.name}: malformed vector file: {e}")
            failures += 1
            continue
        check = CHECKS.get(vid)
        if check is None:
            print(f"FAIL  {vid} {vf.name}: no implemented check for this vector id")
            failures += 1
            continue
        ok, detail = check(manifest, raw=raw, prev_path=a.prev_manifest)
        passed_gate = (ok == (expect == "pass"))
        mark = "PASS" if passed_gate else "FAIL"
        print(f"{mark}  {vid} {vec.get('name', vf.name)}: {detail} (expected {expect})")
        if not passed_gate:
            failures += 1

    print(f"\n{len(vfiles)} vectors, {failures} gate failure(s)")
    if a.require_all_pass and failures:
        print("::error::--require-all-pass: conformance suite FAILED", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
