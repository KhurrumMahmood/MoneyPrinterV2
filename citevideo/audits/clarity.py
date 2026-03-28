"""
Clarity audit for jargon density and explanation gaps.
"""

from __future__ import annotations

from typing import Any

JARGON_TERMS = [
    "autophagy",
    "cytokine",
    "metabolic flexibility",
    "oxidative stress",
    "bioavailability",
    "methylation",
]


def run_clarity_audit(script: dict[str, Any] | None) -> dict[str, Any]:
    script = script or {}
    findings = []

    for scene in script.get("scenes", []):
        narration = scene.get("narration", "").lower()
        for term in JARGON_TERMS:
            if term in narration and "means" not in narration and "called" not in narration:
                findings.append(
                    {
                        "severity": "minor",
                        "scene_id": scene.get("scene_id", ""),
                        "issue": f"Potential unexplained jargon: {term}",
                    }
                )

    return {
        "audit": "clarity",
        "issue_count": len(findings),
        "issues": findings,
    }
