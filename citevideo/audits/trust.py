"""
Trust audit: attribution, uncertainty, and correction visibility checks.
"""

from __future__ import annotations

from typing import Any


def run_trust_audit(
    script: dict[str, Any] | None,
    corrections: dict[str, Any],
    source_registry: dict[str, Any],
) -> dict[str, Any]:
    script = script or {}
    findings = []

    if source_registry.get("count", 0) == 0:
        findings.append(
            {
                "severity": "critical",
                "issue": "Source registry is empty",
            }
        )

    if corrections.get("count", 0) == 0:
        findings.append(
            {
                "severity": "minor",
                "issue": "No corrections log items present yet",
            }
        )

    for scene in script.get("scenes", []):
        if scene.get("claims_referenced") and not scene.get("citations_to_show"):
            findings.append(
                {
                    "severity": "major",
                    "scene_id": scene.get("scene_id", ""),
                    "issue": "Claim-bearing scene lacks citations_to_show",
                }
            )

    return {
        "audit": "trust",
        "issue_count": len(findings),
        "issues": findings,
    }
