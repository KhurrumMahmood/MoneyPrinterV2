"""
Policy audit for risky or non-compliant phrasing.
"""

from __future__ import annotations

from typing import Any

RISKY_PHRASES = [
    "cure",
    "reverse disease",
    "stop your medication",
    "replace your doctor",
    "guaranteed",
    "works for everyone",
]


def run_policy_audit(
    script: dict[str, Any] | None,
    decision_table: dict[str, Any],
) -> dict[str, Any]:
    script = script or {}
    findings = []

    for scene in script.get("scenes", []):
        narration = scene.get("narration", "").lower()
        for phrase in RISKY_PHRASES:
            if phrase in narration:
                findings.append(
                    {
                        "severity": "critical",
                        "scene_id": scene.get("scene_id", ""),
                        "issue": f"Risky phrase detected: '{phrase}'",
                    }
                )

    for row in decision_table.get("rows", []):
        if row.get("evidence_status") == "fabricated":
            findings.append(
                {
                    "severity": "major",
                    "claim_id": row.get("claim_id", ""),
                    "issue": "Fabricated or unverifiable claim must not be presented as advice",
                }
            )

    return {
        "audit": "policy",
        "issue_count": len(findings),
        "issues": findings,
        "guardrails": {
            "grounding_required": True,
            "individualized_advice_allowed": False,
        },
    }
