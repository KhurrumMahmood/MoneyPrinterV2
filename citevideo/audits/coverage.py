"""
Coverage audit: detect unsupported or insufficiently grounded claim coverage.
"""

from __future__ import annotations

from typing import Any


def run_coverage_audit(
    claims_data: dict[str, Any],
    evidence_graph: dict[str, Any],
    decision_table: dict[str, Any],
) -> dict[str, Any]:
    ratings_by_claim = {
        claim.get("id"): claim for claim in evidence_graph.get("claims", [])
    }
    issues = []

    for claim in claims_data.get("claims", []):
        claim_id = claim.get("id")
        graph_claim = ratings_by_claim.get(claim_id, {})
        if not graph_claim:
            issues.append(
                {
                    "severity": "critical",
                    "claim_id": claim_id,
                    "issue": "Claim missing from evidence graph",
                }
            )
            continue
        if not graph_claim.get("evidence_ids"):
            issues.append(
                {
                    "severity": "major",
                    "claim_id": claim_id,
                    "issue": "Claim has no attached evidence IDs",
                }
            )
        if claim.get("category") == "dosage_recommendation" and not graph_claim.get("verification", {}).get("paper_found"):
            issues.append(
                {
                    "severity": "major",
                    "claim_id": claim_id,
                    "issue": "Dosage recommendation lacks verified supporting paper",
                }
            )

    covered_claims = {row.get("claim_id") for row in decision_table.get("rows", [])}
    missing_decisions = sorted(
        claim.get("id")
        for claim in claims_data.get("claims", [])
        if claim.get("id") not in covered_claims
    )

    return {
        "audit": "coverage",
        "issue_count": len(issues),
        "missing_decision_rows": missing_decisions,
        "issues": issues,
    }
