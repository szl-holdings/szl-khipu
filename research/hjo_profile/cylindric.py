"""Source-pinned, finite cylindric-partition laboratory for the HJO challenge.

We implement only the *definitions* of profile, IsCylindric, BoundedBy, and
boundedGF from AxiomMath/HJO Challenge/Basic.lean (pinned git object).
Two independent finite enumeration algorithms compare coefficients through a
strictly bounded volume. This does NOT compute HJO.Finite.poly or formally replay
the theorem, and no match here proves a generating-function identity.

No external calls, data, packages, GPU or training; Python standard library.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
from functools import lru_cache

SCHEMA = "szl.khipu.hjo-cylindric-finite/v1"
DOMAIN = b"szl.khipu.hjo-cylindric-finite/v1\x00"
HJO_REPO = "https://github.com/AxiomMath/HJO"
HJO_REVISION = "6a58dfa6ab98bd35d841cb2cf8fd9081f62fad03"
HJO_CHALLENGE_BLOB = "f641f5432891737d7b8ad6b0bf21a663dcf32901"
HJO_CHALLENGE_SHA256 = "dc96a4b2f1bdeda0027968924ba480f8fc0e29e34eb56fb6cfbdbce2e235b48e"
HJO_SOURCE_PATH = "Challenge/Basic.lean"
MAX_A = 4
MAX_B = 9
MAX_N = 3
MAX_DEGREE = 8


class Hold(ValueError):
    """Invalid scope or disagreement between separately implemented methods."""


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _validate(a: int, b: int, rank: int, degree: int) -> None:
    if type(a) is not int or not 2 <= a <= MAX_A:
        raise Hold("A_BOUND_INVALID")
    if type(b) is not int or not a < b <= MAX_B:
        raise Hold("B_BOUND_INVALID")
    if math.gcd(a, b) != 1:
        raise Hold("HJO_REQUIRES_COPRIME_PAIR")
    if type(rank) is not int or not 0 <= rank <= MAX_N:
        raise Hold("MAX_ENTRY_BOUND_INVALID")
    if type(degree) is not int or not 0 <= degree <= MAX_DEGREE:
        raise Hold("MAX_VOLUME_BOUND_INVALID")


def profile(a: int, b: int) -> tuple[int, ...]:
    """HJO.Cylindric.profile a b i, period a, for a restricted coprime domain."""
    _validate(a, b, 0, 0)
    return tuple(((i+1)*b)//a - (i*b)//a for i in range(a))


@lru_cache(maxsize=16)
def _bounded_rows(rank: int, degree: int) -> tuple[tuple[int, ...], ...]:
    """All nonincreasing positive finite rows with cells <=rank, volume <=degree."""
    if type(rank) is not int or not 0 <= rank <= MAX_N:
        raise Hold("ROW_RANK_INVALID")
    if type(degree) is not int or not 0 <= degree <= MAX_DEGREE:
        raise Hold("ROW_VOLUME_INVALID")
    out: list[tuple[int, ...]] = []
    def rec(row: tuple[int, ...], maximum: int, remaining: int):
        out.append(row)
        for value in range(min(maximum, remaining), 0, -1):
            rec((*row, value), value, remaining-value)
    rec((), rank, degree)
    return tuple(sorted(out, key=lambda r: (sum(r), r)))


def _outgoing_direct(previous: tuple[int, ...],
                     following: tuple[int, ...], offset: int) -> bool:
    """Check l(i+1,j+c_i) <= l(i,j), including zero extension."""
    for j in range(max(len(previous), len(following))):
        left = following[j+offset] if j+offset < len(following) else 0
        right = previous[j] if j < len(previous) else 0
        if left > right:
            return False
    return True


def _direct_coefficients(a: int, c: tuple[int, ...],
                         rows: tuple[tuple[int, ...], ...],
                         degree: int) -> tuple[int, ...]:
    """Independent brute-force recursive enumeration with early weight pruning."""
    counts = [0]*(degree+1)
    def visit(chosen: tuple[tuple[int, ...], ...], weight: int):
        i = len(chosen)
        if i == a:
            if _outgoing_direct(chosen[-1], chosen[0], c[-1]):
                counts[weight] += 1
            return
        for row in rows:
            v = sum(row)
            if weight + v > degree:
                break  # rows sorted by increasing volume
            if i and not _outgoing_direct(chosen[-1], row, c[i-1]):
                continue
            visit((*chosen, row), weight+v)
    visit((), 0)
    return tuple(counts)


def _transfer_allowed(previous: tuple[int, ...],
                      following: tuple[int, ...], offset: int) -> bool:
    """Separate transfer-matrix edge test; no direct enumerator function reuse."""
    # Only positions where following has a potentially nonzero shifted cell
    # can constrain its predecessor. Remaining positions are zero <= any Nat.
    for position in range(max(0, len(following)-offset)):
        earlier = previous[position] if position < len(previous) else 0
        if following[position+offset] > earlier:
            return False
    return True


def _transfer_coefficients(a: int, c: tuple[int, ...],
                           rows: tuple[tuple[int, ...], ...],
                           degree: int) -> tuple[int, ...]:
    """Trace of bounded weighted transfer maps around the labelled cylinder."""
    coeffs = [0]*(degree+1)
    sizes = tuple(map(sum, rows))
    for start, start_size in enumerate(sizes):
        state: dict[tuple[int, int], int] = {(start, start_size): 1}
        for i in range(a-1):
            next_state: dict[tuple[int, int], int] = {}
            for (prior, spent), multiplicity in state.items():
                for index, weight in enumerate(sizes):
                    cost = spent + weight
                    if cost > degree:
                        break
                    if _transfer_allowed(rows[prior], rows[index], c[i]):
                        key = (index, cost)
                        next_state[key] = next_state.get(key, 0) + multiplicity
            state = next_state
        for (last, cost), multiplicity in state.items():
            if _transfer_allowed(rows[last], rows[start], c[-1]):
                coeffs[cost] += multiplicity
    return tuple(coeffs)


def example_nonzero(a: int, c: tuple[int, ...],
                    rows: tuple[tuple[int, ...], ...], degree: int) -> dict | None:
    """Show one feasible nonzero cylindric array, never claim uniqueness."""
    # Try the simplest one-cell example first; c_i >=1 in a<b range.
    if degree == 0:
        return None
    trial = ((1,),) + tuple(() for _ in range(a-1))
    if all(_outgoing_direct(trial[i], trial[(i+1)%a], c[i]) for i in range(a)):
        return {"rows": [list(row) for row in trial], "volume": 1, "entry_max": 1}
    for candidate in itertools.product(rows, repeat=a):
        total = sum(map(sum, candidate))
        if not 0 < total <= degree:
            continue
        if all(_outgoing_direct(candidate[i], candidate[(i+1)%a], c[i]) for i in range(a)):
            return {"rows": [list(row) for row in candidate], "volume": total,
                    "entry_max": max((max(row) for row in candidate if row), default=0)}
    return None


def witness(a: int = 3, b: int = 5,
            rank: int = 2, degree: int = 6) -> dict:
    """Reproduce bounded cylindric generating-function coefficients, not HJO poly."""
    _validate(a, b, rank, degree)
    c = profile(a, b)
    if sum(c) != b or any(not 1 <= v <= MAX_B for v in c):
        raise Hold("PROFILE_INVARIANT_DISAGREEMENT")
    if any(
        ((i+a+1)*b)//a - ((i+a)*b)//a != c[i]
        for i in range(a)
    ):
        raise Hold("PROFILE_PERIODICITY_DISAGREEMENT")
    floor_b_a = b//a
    if any(v not in (floor_b_a, floor_b_a+1) for v in c):
        raise Hold("PROFILE_BALANCE_DISAGREEMENT")
    rows = _bounded_rows(rank, degree)
    direct = _direct_coefficients(a, c, rows, degree)
    transfer = _transfer_coefficients(a, c, rows, degree)
    if direct != transfer:
        first = next(i for i in range(degree+1) if direct[i] != transfer[i])
        raise Hold(f"INDEPENDENT_CYLINDRIC_COUNT_DISAGREEMENT_N_{first}")
    core = {
        "schema": SCHEMA,
        "source_repository": HJO_REPO,
        "source_revision": HJO_REVISION,
        "challenge_path": HJO_SOURCE_PATH,
        "challenge_git_blob_sha": HJO_CHALLENGE_BLOB,
        "challenge_sha256": HJO_CHALLENGE_SHA256,
        "source_formal_definitions": [
            "HJO.Cylindric.profile",
            "HJO.Cylindric.IsCylindric",
            "HJO.Cylindric.BoundedBy",
            "HJO.Cylindric.boundedGF",
        ],
        "a": a, "b": b, "gcd": math.gcd(a, b),
        "bounded_entry_max_N": rank,
        "finite_volume_limit": degree,
        "profile": list(c),
        "profile_sum_equals_b": True,
        "profile_period_a_checked": True,
        "cylindric_coefficients_by_volume": list(direct),
        "two_finite_enumerators_agree": True,
        "finite_rows_considered": len(rows),
        "example_cylindric_rows": (
            example_nonzero(a, c, rows, degree)
            if rank > 0 else None
        ),
        "status": "FINITE_CYLINDRIC_DEFINITION_CONTROL",
        "HJO_rank_N_polynomial_computed": False,
        "HJO_equality_verified_here": False,
        "Lean_kernel_replayed": False,
        "challenge_template_sorry_is_not_proof": True,
        "historical_khipu_encoding_inferred": False,
        "new_infinite_theorem_proved": False,
        "independent_scientific_replication": False,
        "signature_verified": False,
        "production_qualification": "NOT_ASSESSED",
    }
    return {**core, "sha256": hashlib.sha256(DOMAIN + canonical(core)).hexdigest()}
