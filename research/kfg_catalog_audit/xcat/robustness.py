"""Descriptive sensitivity of the frozen strict cross-catalog overlap."""
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

CORPUS_SHA = "6ef204b641826b37c320509952ed4181e93865af20f1cdfefd7516a49cf8ad0d"

def read_report():
    source = Path("result.json").read_bytes()
    raw = Path("corpus.json.gz").read_bytes()
    if hashlib.sha256(raw).hexdigest() != CORPUS_SHA:
        raise ValueError("pinned corpus hash mismatch")
    comparison = json.loads(source)
    corpus = json.loads(gzip.decompress(raw))
    idx = {field: i for i, field in enumerate(corpus["cord_fields"])}
    artifacts = {row["id"]: row for row in corpus["khipus"]}
    conditions = defaultdict(list)
    matching = comparison["rows_in_both"]
    if len(matching) != 39 or comparison["concordant_id_and_okr_name"] != 557:
        raise ValueError("frozen baseline count mismatch")
    by_object = {}
    for r in matching:
        obj = r["object_id"]
        if obj not in by_object:
            by_object[obj] = []
        by_object[obj].append(r)
        artifact = artifacts[obj]
        cords = {row[0]: row for row in artifact["cords"]}
        members = [cords[r["top_cord_id"]], *[cords[i] for i in r["summand_ids"]]]
        if members[0][idx["value"]] != r["value"] or sum(m[idx["value"]] for m in members[1:]) != r["value"]:
            raise ValueError("exact arithmetic mismatch")
        prov = artifact["prov"].strip()
        known_provenance = bool(prov and prov.casefold() != "unknown")
        all_summands_nonzero = all(m[idx["value"]] > 0 for m in members[1:])
        no_broken_termination = all(m[idx["term"]] not in ("B", "C") for m in members)
        tests = {
            "baseline": True, "recorded_non_unknown_provenance": known_provenance,
            "no_zero_valued_summand": all_summands_nonzero,
            "no_B_or_C_termination_code": no_broken_termination,
            "all_three_filters": known_provenance and all_summands_nonzero and no_broken_termination,
        }
        for key, passed in tests.items():
            if passed:
                conditions[key].append(r)
    n = len(matching)
    n_obj = len(by_object)
    den = comparison["concordant_id_and_okr_name"]
    block_counts = {i: len(rs) for i, rs in by_object.items()}
    rank = sorted(block_counts, key=lambda i: (-block_counts[i], artifacts[i]["okr"]))
    counts = [block_counts[i] for i in rank]
    def counts_of(rows):
        return dict(rows=len(rows), matching_artifacts=len({r["object_id"] for r in rows}))
    output = {
        "baseline_sha256": hashlib.sha256(source).hexdigest(), "corpus_sha256": CORPUS_SHA,
        "shared_identity_records": den,
        "strictly_mapped_KFG_positive_rows_on_shared_records": comparison["kfg_shared_positive_rows"],
        "all_single_group_OKR_positive_rows_on_shared_records": comparison["okr_shared_positive_rows"],
        "row_sensitivity": {k: counts_of(conditions[k]) for k in tests},
        "largest_artifact_share": {"numerator": counts[0], "denominator": n},
        "top_four_share": {"numerator": sum(counts[:4]), "denominator": n},
        "leave_four_largest_out": {"remaining_rows": n - sum(counts[:4]), "remaining_matching_artifacts": n_obj-4},
        "leave_one_matching_artifact_out": {
            "rows_min": n-max(counts), "rows_max": n-min(counts), "matching_artifacts": n_obj-1
        },
        "leave_any_shared_artifact_out": {
            "rows_min": n-max(counts), "rows_max": n,
            "matching_artifacts_min": n_obj-1, "matching_artifacts_max": n_obj
        },
        "artifact_omissions": [
            {"okr": artifacts[i]["okr"], "kfg": by_object[i][0]["kfg"],
             "numeric_id": i, "reported_provenance": artifacts[i]["prov"],
             "omitted_rows": block_counts[i], "remaining_rows": n-block_counts[i]}
            for i in rank
        ],
        "leave_one_artifact_distribution": dict(sorted(Counter(n-k for k in counts).items())),
        "interpretation": [
            "Deletion is at the artifact level; prints exact finite-catalog counts rather than treating cord rows as independent.",
            "Reported provenance is secondary catalog metadata, not confirmed geography.",
            "The B/C exclusion applies the recorded termination codes used by the pinned SZL source; it is not a universal damage adjudication.",
            "557 is the identity concordance frame, not a detector eligibility denominator. The 39 KFG rows are already selected mapped positives, and the 47 OKR rows are selected positives as well.",
            "No confidence interval, p-value, sensitivity, false-negative rate, or independent validation is estimated."
        ]
    }
    return output

if __name__ == "__main__":
    print(json.dumps(read_report(), indent=2))
