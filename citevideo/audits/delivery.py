"""
Delivery audit for hook placement, evidence pacing, and actionability.
"""

from __future__ import annotations

from typing import Any


def run_delivery_audit(
    script: dict[str, Any] | None,
    delivery_manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    script = script or {}
    delivery_manifest = delivery_manifest or {}
    findings = []

    scenes = script.get("scenes", [])
    if scenes:
        first_scene = scenes[0]
        if len(first_scene.get("narration", "").split()) < 8:
            findings.append(
                {
                    "severity": "minor",
                    "scene_id": first_scene.get("scene_id", ""),
                    "issue": "Opening hook may be too short or underdeveloped",
                }
            )

    strong_claim_early = any(
        scene.get("evidence_strength") in {"strong", "moderate"}
        for scene in scenes[:3]
    )
    if not strong_claim_early:
        findings.append(
            {
                "severity": "major",
                "issue": "No strong or moderate evidence scene appears in the first three scenes",
            }
        )

    if not delivery_manifest.get("shorts"):
        findings.append(
            {
                "severity": "minor",
                "issue": "No Shorts manifest entries generated",
            }
        )

    return {
        "audit": "delivery",
        "issue_count": len(findings),
        "issues": findings,
    }
