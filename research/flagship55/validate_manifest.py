"""Fail-closed, metadata-only Flagship55 Khipu research manifest validator.

No Hugging Face calls, trained weights, raw dataset reads, policy action, or launch.
Exit 0 validates the design structure ONLY and grants no training authority.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SCHEMA = "szl.khipu.flagship55-provenance-design/v0"
SHA = re.compile(r"[0-9a-f]{40}")
LOCKED = ("F1", "F4", "F7", "F11", "F12", "F18", "F19", "F22")
ROLES = ("YACHAY_TEACHER", "WILLAY_GUIDE", "KHIPU_SKEPTIC")
FALSE_GATES = (
    "private_graph_training", "auto_ingest", "auto_train", "auto_publish",
    "auto_merge", "auto_deploy", "model_weights_modified",
    "independent_eval_accepted", "rights_cleared", "teacher_benchmarked",
    "adapter_compatibility_verified", "compute_budget_approved_for_this_proposal",
    "final_model_qualified",
)
MAX_BYTES = 128 * 1024


class ManifestHold(ValueError):
    """A bounded nonsecret reason. No remediation side effect."""


def require(value, reason: str) -> None:
    if not value:
        raise ManifestHold(reason)


def strict_loads(raw: bytes) -> dict:
    require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_BYTES, "BYTE_BUDGET")
    def pairs(items):
        result = {}
        for k, v in items:
            require(k not in result, "DUPLICATE_FIELD")
            result[k] = v
        return result
    def bad_constant(_):
        raise ManifestHold("NONFINITE_JSON")
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=bad_constant)
    except (ValueError, UnicodeError) as err:
        if isinstance(err, ManifestHold):
            raise
        raise ManifestHold("INVALID_JSON") from None
    require(isinstance(value, dict), "MANIFEST_NOT_OBJECT")
    return value


def check(data: dict) -> dict:
    require(isinstance(data, dict), "MANIFEST_NOT_OBJECT")
    require(data.get("schema") == SCHEMA, "SCHEMA_MISMATCH")
    require(data.get("status") == "DESIGN_ONLY", "FALSE_TRAINING_STATUS")
    require(data.get("reference_only") is True, "NOT_REFERENCE_ONLY")
    require(data.get("receipt_signature") == "UNSIGNED", "FALSE_SIGNATURE_STATUS")
    require(data.get("source_owner") == "szl-holdings/szl-khipu", "WRONG_SOURCE_OWNER")

    base = data.get("baseline")
    require(isinstance(base, dict), "BASELINE_MISSING")
    require(base.get("model_repo") == "SZLHOLDINGS/salad-flagship54-v1", "BASELINE_RENAMED")
    require(isinstance(base.get("revision"), str) and SHA.fullmatch(base["revision"]), "BASELINE_NOT_PINNED")
    require(base.get("checkpoint_step") == 37000, "BASELINE_STEP_MISMATCH")
    require(base.get("artifact_state") == "ARTIFACT_VERIFIED_OWNER_LAPTOP", "BASELINE_ARTIFACT_CLAIM")
    require(base.get("actual_shutdown") == "UNOBSERVED", "FALSE_SHUTDOWN_CLAIM")
    require(base.get("evaluation") == "NOT_ESTABLISHED", "FALSE_EVAL_CLAIM")
    require(base.get("production_qualification") == "NOT_ESTABLISHED", "FALSE_QUALIFICATION_CLAIM")

    topology = data.get("topology")
    require(isinstance(topology, dict), "TOPOLOGY_MISSING")
    require(topology.get("method") == "THREE_PROPOSED_COMPATIBLE_SPECIALIST_ADAPTERS", "TOPOLOGY_METHOD_CHANGED")
    require(topology.get("teacher_external_at_training") is True, "TEACHER_SOURCE_UNKNOWN")
    require(topology.get("three_standalone_models_embedded") is False, "FALSE_EMBEDDED_WEIGHTS_CLAIM")
    require(topology.get("router") == "UNIMPLEMENTED", "FALSE_ROUTER_CLAIM")
    require(topology.get("new_controller_created") is False, "COMPETING_CONTROLLER")
    require(topology.get("proof_authority") == "EXTERNAL_LEAN_KERNEL_AND_EXISTING_DETERMINISTIC_POLICY", "REFEREE_REPLACED")
    experts = topology.get("experts")
    require(isinstance(experts, list) and len(experts) == 3, "THREE_EXPERT_ROLES_REQUIRED")
    require(tuple(x.get("role") for x in experts if isinstance(x, dict)) == ROLES, "EXPERT_ROLE_OR_ORDER_CHANGED")
    for expert in experts:
        require(expert.get("implementation") == "PROPOSED_LORA_ADAPTER", "UNREVIEWED_IMPLEMENTATION")
        require(expert.get("weights_revision") is None, "UNVERIFIED_EXPERT_WEIGHTS")
        require(expert.get("trained") is False and expert.get("deployed") is False, "FALSE_EXPERT_STATUS")

    math = data.get("math")
    require(isinstance(math, dict), "MATH_MISSING")
    require(math.get("source_repo") == "szl-holdings/lutar-lean", "MATH_OWNER_CHANGED")
    require(isinstance(math.get("source_revision"), str) and SHA.fullmatch(math["source_revision"]), "MATH_NOT_PINNED")
    require(math.get("claims_path") == "claims/locked-formulas.v1.json", "MATH_CLAIM_LEDGER_CHANGED")
    require(tuple(math.get("locked_ids", ())) == LOCKED, "LOCKED_EIGHT_CHANGED")
    require(tuple(math.get("axioms", ())) == ("A1","A2","A3","A4","A5"), "AXIOM_LABELS_CHANGED")
    require(math.get("lambda_uniqueness") == "UNCONDITIONAL_A1_A5_REFUTED_AS_STATED", "FALSE_UNIQUENESS_CLAIM")
    require(math.get("lambda_counterexample") == "maxAgg_ne_Lambda", "COUNTEREXAMPLE_OMITTED")
    require(math.get("conditional_uniqueness") == "EXTRA_ASSUMPTIONS_REQUIRED", "CONDITIONAL_SCOPE_LOST")
    require(math.get("lambda_authority") is False and math.get("conjectures_auto_proven") is False, "LEARNED_PROOF_AUTHORITY")

    census = data.get("dataset_census")
    require(isinstance(census, dict), "DATASET_CENSUS_MISSING")
    require(census.get("owner") == "SZLHOLDINGS" and census.get("provider") == "HUGGING_FACE", "DATASET_OWNER_CHANGED")
    require(census.get("metadata_only") is True, "RAW_DATA_MISLABELLED")
    require(type(census.get("requested_cap")) is int and census["requested_cap"] >= 1, "INVALID_CAP")
    for key in ("returned", "public", "private", "with_license_tag", "without_license_tag"):
        require(type(census.get(key)) is int and census[key] >= 0, "BAD_DATASET_COUNT")
    require(census["returned"] < census["requested_cap"], "CAP_EXHAUSTED")
    require(census["returned"] == census["public"] + census["private"], "VISIBILITY_DENOMINATOR")
    require(census["returned"] == census["with_license_tag"] + census["without_license_tag"], "LICENSE_DENOMINATOR")
    require(census.get("complete_within_accessible_hf_scope") is True, "CLAIMED_HF_COVERAGE_UNKNOWN")
    require(census.get("all_global_data_covered") is False, "FALSE_GLOBAL_COVERAGE")
    require(census.get("training_admitted") == 0, "UNAPPROVED_DATA_ADMISSION")
    require(census.get("private_identities_in_public_document") is False, "PRIVATE_DATA_DISCLOSURE")
    for key in ("rights_review", "privacy_review", "evaluation_decontamination"):
        require(census.get(key) == "NOT_PERFORMED", "FALSE_REVIEW_STATUS")

    roots = data.get("owner_roots")
    require(isinstance(roots, list) and len(roots) >= 5, "SOURCE_ROOTS_MISSING")
    owners = set()
    for item in roots:
        require(isinstance(item, dict), "INVALID_SOURCE_ROOT")
        repo = item.get("repository")
        require(isinstance(repo, str) and repo.startswith("szl-holdings/") and repo not in owners, "SOURCE_IDENTITY")
        owners.add(repo)
        require(isinstance(item.get("revision"), str) and SHA.fullmatch(item["revision"]), "SOURCE_NOT_PINNED")
        require(item.get("status") == "REFERENCE_ONLY", "IMPLICIT_SOURCE_ADMISSION")

    examples = data.get("public_dataset_examples")
    require(isinstance(examples, list) and 0 < len(examples) < census["returned"], "DATASET_EXAMPLES_NOT_SUBSET")
    seen = set()
    for item in examples:
        require(isinstance(item, dict), "BAD_DATASET_ENTRY")
        repo = item.get("repo")
        require(isinstance(repo, str) and repo.startswith("SZLHOLDINGS/") and repo not in seen, "DATASET_IDENTITY")
        seen.add(repo)
        require(isinstance(item.get("revision"), str) and SHA.fullmatch(item["revision"]), "DATASET_REVISION_UNPINNED")
        require(item.get("training_admitted") is False, "UNAUTHORIZED_TRAINING_DATA")
        require(item.get("role") in {"RETRIEVAL_REVIEW", "PROOF_REFERENCE_REVIEW", "SFT_REVIEW",
                                    "EVAL_PROOF_REFERENCE_REVIEW", "STATEMENT_CONTEXT_ONLY",
                                    "RIGHTS_UNKNOWN_REVIEW", "EXCLUDED_EXISTING_BOM"}, "DATASET_ROLE_UNREVIEWED")
        if repo == "SZLHOLDINGS/szl-quant-sft-v1":
            require(item.get("role") == "EXCLUDED_EXISTING_BOM", "BOM_BLOCK_BYPASSED")
    require("SZLHOLDINGS/szl-quant-sft-v1" in seen, "BOM_EXCLUSION_NOT_LISTED")
    gates = data.get("gates")
    require(isinstance(gates, dict), "GATES_MISSING")
    for key in FALSE_GATES:
        require(gates.get(key) is False, "UNAPPROVED_AUTHORITY_" + key.upper())
    require(gates.get("flagship54_guard_authority_unchanged") is True, "GUARD_AUTHORITY_CHANGED")
    return {"status": "DESIGN_STRUCTURE_VERIFIED_ONLY", "roles": len(experts),
            "source_roots": len(roots), "public_dataset_examples": len(examples),
            "accessible_hf_dataset_count": census["returned"], "train_launch_authorized": False,
            "model_weights_created": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    if args.manifest.is_symlink() or not args.manifest.is_file():
        print(json.dumps({"status": "HOLD", "reason": "MANIFEST_NOT_REGULAR"}))
        return 2
    try:
        with args.manifest.open("rb") as f:
            data = strict_loads(f.read(MAX_BYTES + 1))
        result = check(data)
    except ManifestHold as err:
        print(json.dumps({"status": "HOLD", "reason": str(err)}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
