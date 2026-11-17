"""Flagship55 Khipu three-role *proposal* and synthetic risk-coverage contracts.

This is a local, deterministic, stdlib-only research tool. It does NOT call or
contain the three proposed learned specialists, run Lean, train, sign, approve,
publish, or control a provider. All outputs remain REVIEW_REQUIRED.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from .validate_manifest import check as validate_manifest

PACKET_SCHEMA = "szl.khipu.flagship55.triad-packet/v1"
REQUEST_SCHEMA = "szl.khipu.flagship55.triad-request/v1"
RISK_SCHEMA = "szl.khipu.flagship55.synthetic-risk-coverage/v1"
ROLES = (
    ("YACHAY_TEACHER", "SOURCE_GROUNDED_PROOF_PLAN"),
    ("WILLAY_GUIDE", "RIGHTS_SCOPE_AND_DOCTRINE_REVIEW"),
    ("KHIPU_SKEPTIC", "COUNTEREXAMPLE_AND_ABSTENTION_CHALLENGE"),
)
CATEGORIES = (
    "ANSWERABLE",
    "INSUFFICIENT_EVIDENCE",
    "CONTRADICTORY",
    "REFUTED_AS_STATED",
    "OPEN_PROBLEM",
)
MAX_INPUT_BYTES = 128 * 1024
MAX_REFS = 8
MAX_CASES = 512
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")


class ContractHold(ValueError):
    """Stable, nonsecret input-rejection code."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ContractHold(code)


def read_json(path: Path) -> tuple[dict | list, str]:
    require(path.is_file() and not path.is_symlink(), "NOT_REGULAR_FILE")
    with path.open("rb") as source:
        raw = source.read(MAX_INPUT_BYTES + 1)
    require(0 < len(raw) <= MAX_INPUT_BYTES, "INPUT_BYTE_BUDGET")

    def pair_check(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, "DUPLICATE_JSON_KEY")
            value[key] = item
        return value

    def reject_nonfinite(_):
        raise ContractHold("NONFINITE_JSON")

    try:
        parsed = json.loads(
            raw, object_pairs_hook=pair_check, parse_constant=reject_nonfinite
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ContractHold("INVALID_JSON") from exc
    return parsed, hashlib.sha256(raw).hexdigest()


def _canonical(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=True,
                       allow_nan=False, separators=(",", ":")) + "\n").encode("ascii")


def make_packet(manifest: dict, manifest_sha256: str, request: dict) -> dict:
    """Build an immutable, nonauthoritative role packet using public handles.

    A referenced public dataset is NOT rights-cleared or training-admitted.
    This never passes any free text or private asset names to a model.
    """
    validate_manifest(manifest)
    require(isinstance(manifest_sha256, str) and re.fullmatch(r"[0-9a-f]{64}", manifest_sha256) is not None,
            "MANIFEST_DIGEST_REQUIRED")
    require(manifest_sha256 == hashlib.sha256(_canonical(manifest)).hexdigest(),
            "MANIFEST_CONTENT_DIGEST_MISMATCH")
    require(type(request) is dict, "REQUEST_NOT_OBJECT")
    require(set(request) == {"schema", "request_id", "claim_id", "source_refs"},
            "REQUEST_FIELDS_NOT_ALLOWLISTED")
    require(request["schema"] == REQUEST_SCHEMA, "REQUEST_SCHEMA_MISMATCH")
    require(type(request["request_id"]) is str and ID.fullmatch(request["request_id"]) is not None,
            "REQUEST_ID_INVALID")
    math = manifest["math"]
    locked = math["locked_ids"]
    claim = request["claim_id"]
    require(type(claim) is str and (claim in locked or claim == "F23"),
            "CLAIM_OUTSIDE_PINNED_REGISTRY")
    refs = request["source_refs"]
    require(type(refs) is list and 0 < len(refs) <= MAX_REFS,
            "SOURCE_REF_BUDGET")
    approved_catalog = {
        entry["repo"]: entry for entry in manifest["public_dataset_examples"]
        if entry["role"] not in ("EXCLUDED_EXISTING_BOM", "RIGHTS_UNKNOWN_REVIEW")
    }
    checked, seen = [], set()
    for entry in refs:
        require(type(entry) is dict and set(entry) == {"repo", "revision"},
                "SOURCE_REF_SHAPE")
        repo, revision = entry["repo"], entry["revision"]
        require(type(repo) is str and type(revision) is str and SHA40.fullmatch(revision) is not None,
                "SOURCE_REF_IDENTITY")
        require(repo not in seen, "DUPLICATE_SOURCE_REF")
        seen.add(repo)
        candidate = approved_catalog.get(repo)
        require(candidate is not None and candidate["revision"] == revision,
                "SOURCE_NOT_PINNED_OR_EXCLUDED")
        require(candidate["training_admitted"] is False, "SOURCE_ALREADY_ADMITTED_CONFLICT")
        checked.append({"repo": repo, "revision": revision,
                        "catalog_role": candidate["role"],
                        "training_rights": "NOT_CLEARED"})
    packet = {
        "schema": PACKET_SCHEMA,
        "status": "REVIEW_REQUIRED",
        "request_id": request["request_id"],
        "manifest_canonical_sha256": manifest_sha256,
        "math_repository": math["source_repo"],
        "math_revision": math["source_revision"],
        "claim_id": claim,
        "claim_scope": (
            "UNCONDITIONAL_LAMBDA_UNIQUENESS_REFUTED_AS_STATED"
            if claim == "F23" else "LOCKED_ID_REFERENCE_ONLY_NO_KERNEL_REPLAY"
        ),
        "public_source_handles": checked,
        "roles": [
            {"role": role, "assignment": assignment,
             "execution_status": "NOT_EXECUTED_NO_COMPATIBLE_SPECIALIST_WEIGHTS",
             "model_revision": None, "output": None}
            for role, assignment in ROLES
        ],
        "independent_lean_referee": "NOT_RUN",
        "independent_policy_referee": "NOT_RUN",
        "quality_evaluation": "NOT_RUN",
        "training_authority": "NONE",
        "inference_authority": "NONE",
        "publication_authority": "NONE",
        "cloud_mutations": 0,
        "raw_source_rows_included": False,
        "signing_status": "UNSIGNED",
        "limitation": "PROPOSAL_ONLY_NOT_THREE_EMBEDDED_OR_TRAINED_MODELS",
    }
    # A digest is tamper detection relative to a retained expected digest,
    # not evidence of a signature, owner approval, independent checking or truth.
    blob = _canonical(packet)
    return {**packet, "packet_sha256": hashlib.sha256(
        b"szl.khipu.flagship55.triad-packet/v1\0" + blob
    ).hexdigest()}


def synthetic_risk_coverage(cases: list) -> dict:
    """Descriptive development-only selective risk; NOT an independent eval.

    Each case has a developer-asserted outcome. Empty answered denominator is
    UNAVAILABLE, not a zero-risk or quality claim. No threshold is optimized.
    """
    require(type(cases) is list and 0 < len(cases) <= MAX_CASES,
            "SYNTHETIC_CASE_BUDGET")
    seen = set()
    table = {category: {"total": 0, "answered": 0, "wrong": 0}
             for category in CATEGORIES}
    for item in cases:
        require(type(item) is dict and set(item) == {"id", "category", "outcome"},
                "SYNTHETIC_CASE_FIELDS")
        case_id = item["id"]
        require(type(case_id) is str and ID.fullmatch(case_id) is not None,
                "CASE_ID_INVALID")
        require(case_id not in seen, "DUPLICATE_CASE")
        seen.add(case_id)
        category = item["category"]
        outcome = item["outcome"]
        require(type(category) is str and category in table,
                "CASE_CATEGORY_UNKNOWN")
        require(type(outcome) is str and outcome in ("CORRECT", "INCORRECT", "ABSTAIN"),
                "CASE_OUTCOME_UNKNOWN")
        row = table[category]
        row["total"] += 1
        if outcome != "ABSTAIN":
            row["answered"] += 1
            row["wrong"] += int(outcome == "INCORRECT")
    total = sum(v["total"] for v in table.values())
    answered = sum(v["answered"] for v in table.values())
    wrong = sum(v["wrong"] for v in table.values())

    def measured(row: dict) -> dict:
        n, selected = row["total"], row["answered"]
        return {
            **row,
            "coverage": selected / n if n else None,
            "selective_risk": row["wrong"] / selected if selected else None,
            "selective_risk_status": "OBSERVED_SYNTHETIC" if selected else "UNAVAILABLE_ZERO_ANSWERED",
        }

    return {
        "schema": RISK_SCHEMA,
        "scope": "DEVELOPER_ASSERTED_SYNTHETIC_ONLY_NOT_INDEPENDENT_EVALUATION",
        "total_cases": total,
        "answered_cases": answered,
        "wrong_answered_cases": wrong,
        "overall": measured({"total": total, "answered": answered, "wrong": wrong}),
        "by_category": {name: measured(row) for name, row in table.items()},
        "threshold_selected": False,
        "model_quality_qualified": False,
        "heldout_independent": False,
        "signing_status": "UNSIGNED",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--request", type=Path, required=True)
    args = p.parse_args()
    try:
        manifest, _ = read_json(args.manifest)
        request, _ = read_json(args.request)
        canonical_digest = hashlib.sha256(_canonical(manifest)).hexdigest()
        packet = make_packet(manifest, canonical_digest, request)
    except (ContractHold, ValueError, OSError) as error:
        reason = str(error) if isinstance(error, ContractHold) else "INPUT_READ_FAILURE"
        print(json.dumps({"status": "HOLD", "reason": reason}, sort_keys=True))
        return 2
    sys.stdout.buffer.write(_canonical(packet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
