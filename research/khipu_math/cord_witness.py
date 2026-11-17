# SPDX-License-Identifier: Apache-2.0
"""Khipu-inspired cord reconciliation and independent modular challenge.

CULTURAL AND MATHEMATICAL LIMITS
Khipu are real Andean knotted-cord recordkeeping instruments. Decimal place
notation and some additive top-cord relationships have been documented; this
program's JSON schema and modular polynomial challenge are ORIGINAL MODERN
ENGINEERING, not a claimed decipherment, an ancestral algorithm or an Inka
cryptographic protocol. The historic recordkeeping practice deserves its own
citation and Indigenous community scholarship.

For ordered values x_0,...,x_(n-1), independently declared top T, and a
challenge r in F_p, define
    C(x,T) := [T = sum(x_i)]
    W_r(x) := sum(x_i * r**i) mod p.

For two DIFFERENT sequences x and y of length n <= 64, with every element in
[0,p), if r is uniform and chosen AFTER the reference was committed, then
    Pr_r[W_r(x) = W_r(y)] <= (n-1)/p.
This is the standard polynomial identity/root bound. It is NOT a standalone
provenance signature. An adaptive adversary choosing y after observing r, a
modified reference, non-independent witnesses or unverified source rights can
invalidate its security interpretation. Even a matching fingerprint does not
establish factual truth; exact committed-byte readback is still required.

All operations are pure and non-executing; no model or dataset is fetched.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = 'szl.khipu-cord-research/v1'
PRIME = 2**61 - 1  # mathematically prime (Mersenne prime)
TEST_PRIME = 101  # for exhaustive small-field controls only
MAX_CHILDREN = 64
MAX_VALUE = 10**12 - 1  # capped to 12 decimal register positions
MAX_BYTES = 24_576
_ALLOWED_RIGHTS = {'SYNTHETIC', 'PUBLIC_RIGHTS_DECLARED'}
_ID = re.compile(r'[A-Za-z][A-Za-z0-9._-]{0,63}\Z')
_HEX40 = re.compile(r'[0-9a-f]{40}\Z')
_HEX64 = re.compile(r'[0-9a-f]{64}\Z')
_DOMAIN = b'SZL-KHIPU-CORD-RESEARCH/V1\x00'


class CordError(ValueError):
    """A malformed, unsupported or unauthoritative research input."""


def _object(value: Any, fields: set[str], name: str) -> dict:
    if type(value) is not dict or set(value) != fields:
        raise CordError(f'{name}: exact fields required')
    return value


def _bounded_int(value: Any, minimum: int, maximum: int, field: str) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise CordError(f'{field}: bounded integer required')
    return value


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def validate(record: Any) -> dict:
    """Validate a bounded aggregate as reported, without endorsing its meaning."""
    obj = _object(record, {'schema', 'scope', 'source_revision', 'rights_class',
                           'units', 'top_total', 'children'}, 'record')
    if obj['schema'] != SCHEMA:
        raise CordError('schema: unsupported')
    for field in ('scope', 'units'):
        if type(obj[field]) is not str or not _ID.fullmatch(obj[field]):
            raise CordError(f'{field}: identifier required')
    if type(obj['source_revision']) is not str or not _HEX40.fullmatch(obj['source_revision']):
        raise CordError('source_revision: immutable 40-hex declaration required')
    if type(obj['rights_class']) is not str or obj['rights_class'] not in _ALLOWED_RIGHTS:
        raise CordError('rights_class: unreviewed or unsupported')
    _bounded_int(obj['top_total'], 0, MAX_CHILDREN * MAX_VALUE, 'top_total')
    children = obj['children']
    if type(children) is not list or not 1 <= len(children) <= MAX_CHILDREN:
        raise CordError('children: bounded, nonempty ordered list required')
    seen = set()
    for child in children:
        row = _object(child, {'cord', 'value'}, 'child')
        name = row['cord']
        if type(name) is not str or not _ID.fullmatch(name) or name in seen:
            raise CordError('child: invalid or repeated cord identifier')
        seen.add(name)
        _bounded_int(row['value'], 0, MAX_VALUE, 'child.value')
    return json.loads(canonical(obj))  # detached; stable field ordering


def _no_duplicate_fields(pairs: list[tuple[str, Any]]) -> dict:
    o = {}
    for key, value in pairs:
        if key in o:
            raise CordError('duplicate JSON key')
        o[key] = value
    return o


def _reject_nonfinite(_: str) -> None:
    raise CordError('nonfinite JSON constant')


def load_record_bytes(path: str | Path) -> tuple[dict, bytes]:
    """Read once: the returned digest input is exactly what was validated.

    The caller must not reopen the path to calculate a receipt hash: a
    concurrent writer could replace its bytes after validation.
    """
    try:
        with Path(path).open('rb') as file:
            raw = file.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise CordError('record exceeds byte limit')
        record = validate(json.loads(raw.decode('utf-8'),
                                     object_pairs_hook=_no_duplicate_fields,
                                     parse_constant=_reject_nonfinite))
        return record, raw
    except CordError:
        raise
    except (UnicodeError, OSError, ValueError, RecursionError, OverflowError):
        raise CordError('record unavailable or invalid JSON') from None


def load_record(path: str | Path) -> dict:
    """Keep the original validation API for existing consumers."""
    return load_record_bytes(path)[0]


def commitment(record: dict) -> str:
    """SHA-256 of exact typed canonical bytes, domain separated; not a signature."""
    return hashlib.sha256(_DOMAIN + canonical(validate(record))).hexdigest()


def encode_decimal(value: int) -> list[dict[str, Any]]:
    """Synthetic positional knot notation, NOT physical knot reconstruction.

    Units: figure-eight for digit 1; long for digits 2-9. Tens and above:
    groups of single overhand knots. A zero place is absent from this symbolic
    sequence; historical absence of knots is not enough to prove a zero or even
    the existence of a corresponding physical cord.
    """
    _bounded_int(value, 0, MAX_VALUE, 'value')
    if value == 0:
        return []
    tokens = []
    place = 0
    while value:
        digit = value % 10
        if digit:
            kind = ('figure_eight' if digit == 1 else 'long') if place == 0 else 'single'
            tokens.append({'place': place, 'kind': kind, 'count': digit})
        value //= 10
        place += 1
    return tokens


def decode_decimal(tokens: Any) -> int:
    if type(tokens) is not list or len(tokens) > 12:
        raise CordError('tokens: bounded list required')
    value = 0
    last_place = -1
    for token in tokens:
        t = _object(token, {'place', 'kind', 'count'}, 'token')
        place = _bounded_int(t['place'], 0, 11, 'token.place')
        count = _bounded_int(t['count'], 1, 9, 'token.count')
        if place <= last_place:
            raise CordError('token: places must increase exactly once')
        if place == 0:
            kind = 'figure_eight' if count == 1 else 'long'
        else:
            kind = 'single'
        if t['kind'] != kind:
            raise CordError('token: wrong knot type for declared decimal place')
        value += count * 10**place
        last_place = place
    if value > MAX_VALUE:
        raise CordError('token: value beyond limit')
    return value


def fingerprint(values: Any, challenge: int, prime: int = PRIME) -> int:
    """Ordered polynomial evaluation modulo a fixed prime, no inferred secrecy."""
    if type(prime) is not int or prime not in (PRIME, TEST_PRIME):
        raise CordError('field: only reviewed prime fields supported')
    if type(values) not in (list, tuple) or not 1 <= len(values) <= MAX_CHILDREN:
        raise CordError('values: nonempty bounded sequence required')
    _bounded_int(challenge, 0, prime - 1, 'challenge')
    accum = 0
    power = 1
    for x in values:
        _bounded_int(x, 0, prime - 1, 'field value')
        accum = (accum + x * power) % prime
        power = power * challenge % prime
    return accum


def root_collision_bound(n: int, prime: int = PRIME) -> dict:
    """Upper bound for *nonzero fixed* degree <= n-1 field polynomials."""
    if prime not in (PRIME, TEST_PRIME) or type(prime) is not int:
        raise CordError('unsupported field')
    _bounded_int(n, 1, MAX_CHILDREN, 'length')
    if n >= prime:
        raise CordError('length must be less than field size')
    return {'numerator': n - 1, 'denominator': prime,
            'hypotheses': 'distinct fixed value vectors modulo p; uniform post-commit challenge'}


def compare_committed(reference: Any, candidate: Any, *, expected_reference_sha256: str,
                      challenge: int) -> dict:
    """Offline advisory reconciliation against a caller-supplied pinned reference.

    The expected commitment must be held by an independent authority to serve
    as tamper evidence. Supplying a matching hash from the same untrusted input
    does not make it independent. All mismatches deny promotion; a polynomial
    collision cannot override exact bytes. No public proof, model grade or action.
    """
    a = validate(reference)
    b = validate(candidate)
    if type(expected_reference_sha256) is not str or not _HEX64.fullmatch(expected_reference_sha256):
        raise CordError('expected commitment: exact SHA-256 required')
    # Recheck committed reference before consuming candidate observations.
    reference_sha = commitment(a)
    if reference_sha != expected_reference_sha256:
        raise CordError('REFERENCE_COMMITMENT_MISMATCH')
    if (a['scope'], a['units'], a['source_revision'], a['rights_class']) != (
            b['scope'], b['units'], b['source_revision'], b['rights_class']):
        raise CordError('SCOPE_OR_REVISION_MISMATCH')
    if [x['cord'] for x in a['children']] != [x['cord'] for x in b['children']]:
        raise CordError('CORD_ORDER_OR_COVERAGE_MISMATCH')
    va = [x['value'] for x in a['children']]
    vb = [x['value'] for x in b['children']]
    # The range is smaller than p because MAX_VALUE << PRIME, avoiding
    # modular aliasing between distinct integer counts.
    fa, fb = fingerprint(va, challenge), fingerprint(vb, challenge)
    ca = a['top_total'] == sum(va)
    cb = b['top_total'] == sum(vb)
    exact = a == b
    state = ('RECONCILED_FIXED_REFERENCE' if ca and cb and exact
             else 'DENY_REFERENCE_OR_CONSERVATION_MISMATCH')
    return {
        'schema': 'szl.khipu-cord-reconciliation/v1',
        'state': state,
        'reference_commitment_sha256': reference_sha,
        'candidate_commitment_sha256': commitment(b),
        'reference_conserved': ca,
        'candidate_conserved': cb,
        'exact_content_match': exact,
        'challenge_fingerprint_match': fa == fb,
        'challenge': challenge,
        'prime': PRIME,
        'collision_bound_if_fixed_distinct': root_collision_bound(len(va)),
        'independent_custody_proved': False,
        'history_decipherment_proved': False,
        'model_evaluated': False,
        'action_authority': 'NONE',
        'explanation': 'Polynomial collision never overrides full committed-byte mismatch.'
    }
