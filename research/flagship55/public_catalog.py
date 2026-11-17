"""Metadata-only public Hugging Face dataset reference index for Khipu.

A public listing and a license tag confer NO rights, training admission,
data quality, evaluation protection, inference, or publication authority.
This module performs no provider requests or model execution.
"""
from __future__ import annotations

import re
from .triad_packet import read_json, require

SCHEMA = "szl.khipu.flagship55.public-reference-index/v1"
CENSUS_SHA = "21c6c7b1d04e80dba4237ec836c58db6247f04e2b08654930db2637d43d741e8"
REPO = re.compile(r"SZLHOLDINGS/[A-Za-z0-9_.-]+\Z")
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
EXPECTED_PUBLIC = 91


def validate_public_catalog(catalog: dict) -> dict:
    require(type(catalog) is dict, "CATALOG_NOT_OBJECT")
    require(catalog.get("schema") == SCHEMA, "CATALOG_SCHEMA")
    require(catalog.get("provider") == "HUGGING_FACE", "CATALOG_PROVIDER")
    require(catalog.get("owner") == "SZLHOLDINGS", "CATALOG_OWNER")
    require(catalog.get("source_private_census_sha256") == CENSUS_SHA, "CATALOG_CENSUS_PIN")
    require(catalog.get("census_observed_at_utc") == "2026-11-17T07:09:41.034580+00:00",
            "CATALOG_CENSUS_TIME")
    require(catalog.get("private_names_emitted") == 0, "PRIVATE_NAMES_EXPORTED")
    require(catalog.get("approval_authority") == "NONE", "CATALOG_FALSE_AUTHORITY")
    require(catalog.get("source_metadata_only") is True, "CATALOG_FALSE_SOURCE_SCOPE")
    require(catalog.get("inaccessible_sources_inferred") is False, "CATALOG_FALSE_COVERAGE")
    require(catalog.get("scope") ==
            "PUBLIC_DATASET_IDENTITIES_ONLY_NOT_TRAINING_OR_PRIVACY_CLEARANCE",
            "CATALOG_FALSE_RIGHTS_SCOPE")
    require(type(catalog.get("public_count")) is int and catalog["public_count"] == EXPECTED_PUBLIC,
            "CATALOG_COUNT_PIN")
    rows = catalog.get("all_references")
    require(type(rows) is list and len(rows) == EXPECTED_PUBLIC, "CATALOG_COUNT_MISMATCH")
    seen = set()
    last = ""
    for item in rows:
        require(type(item) is dict and
                set(item) == {"id", "source_revision", "license_tags", "source_visibility",
                              "index_role", "rights_state", "data_bytes_inspected",
                              "training_admitted", "eval_holdout_safe"},
                "CATALOG_FIELDS")
        repo, rev = item["id"], item["source_revision"]
        require(type(repo) is str and REPO.fullmatch(repo) is not None and repo not in seen
                and repo > last, "CATALOG_PUBLIC_ID_OR_SORT")
        require(type(rev) is str and SHA40.fullmatch(rev) is not None, "CATALOG_REVISION")
        seen.add(repo)
        last = repo
        tags = item["license_tags"]
        require(type(tags) is list and len(tags) <= 8 and tags == sorted(set(tags)),
                "CATALOG_LICENSE_LIST")
        require(all(type(t) is str and t.startswith("license:") and 8 <= len(t) <= 120
                    for t in tags), "CATALOG_LICENSE_TAG")
        require(item["source_visibility"] == "PUBLIC_AT_CENSUS_TIME", "CATALOG_VISIBILITY")
        require(item["index_role"] == "REFERENCE_ONLY", "CATALOG_TRAINING_ROLE")
        require(item["rights_state"] == "NOT_REVIEWED", "CATALOG_RIGHTS_CLAIM")
        require(item["data_bytes_inspected"] is False and
                item["training_admitted"] is False, "CATALOG_IMPLICIT_DATA_ADMISSION")
        require(item["eval_holdout_safe"] == "UNVERIFIED", "CATALOG_HOLDOUT_CLAIM")
    return {
        "status": "PUBLIC_METADATA_REFERENCES_VALIDATED_ONLY",
        "public_refs": len(seen),
        "source_census_sha256": CENSUS_SHA,
        "private_names_emitted": 0,
        "training_admitted": 0,
        "provider_revision_reobserved": False,
        "license_clearance": "NOT_PERFORMED",
    }


def read_public_catalog(path):
    catalog, digest = read_json(path)
    checked = validate_public_catalog(catalog)
    require(SHA64.fullmatch(digest) is not None, "CATALOG_FILE_HASH")
    return catalog, digest, checked


def find_reference(catalog, repo_id):
    validate_public_catalog(catalog)
    require(type(repo_id) is str and REPO.fullmatch(repo_id) is not None,
            "CATALOG_LOOKUP_ID")
    return next(({"repo": item["id"], "revision": item["source_revision"],
                  "license_tags": item["license_tags"],
                  "rights_state": "NOT_REVIEWED",
                  "training_admitted": False}
                 for item in catalog["all_references"] if item["id"] == repo_id), None)
