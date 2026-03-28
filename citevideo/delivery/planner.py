"""
Build delivery manifest artifacts from approved scripts and evidence.
"""

from __future__ import annotations

from typing import Any

from citevideo.models import SceneBlueprint, ShortBlueprint


def build_delivery_manifest(script: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    strongest = set(evidence.get("strongest_claims", []))
    weakest = set(evidence.get("weakest_claims", []))
    ratings = {rating.get("claim_id"): rating for rating in evidence.get("ratings", [])}

    scene_blueprints = []
    short_blueprints = []
    used_short_claims: set[str] = set()

    for idx, scene in enumerate(script.get("scenes", []), 1):
        claim_ids = scene.get("claims_referenced", [])
        evidence_ids = []
        evidence_level = scene.get("evidence_strength", "none")
        benefit_harm_mode = "benefit"
        safety_flags = []

        for claim_id in claim_ids:
            rating = ratings.get(claim_id, {})
            evidence_ids.extend(
                f"{claim_id}:evidence:{i:02d}"
                for i, _ in enumerate(rating.get("key_citations", []), 1)
            )
            if claim_id in weakest:
                benefit_harm_mode = "caution"
            if rating.get("evidence_rating", {}).get("extrapolation_risk") == "high":
                safety_flags.append("high-extrapolation-risk")

            if claim_id not in used_short_claims and claim_id in strongest:
                short_blueprints.append(
                    ShortBlueprint(
                        short_id=f"short_{len(short_blueprints) + 1:03d}",
                        title=scene.get("heading") or f"Short {len(short_blueprints) + 1}",
                        claim_id=claim_id,
                        evidence_id=evidence_ids[0] if evidence_ids else "",
                        evidence_level=evidence_level,
                        dossier_anchor_id=f"claim-{claim_id}",
                        cta_target="dossier",
                        caution=rating.get("evidence_rating", {}).get("missing_context", ""),
                        allowed_out_of_context=claim_id in strongest and claim_id not in weakest,
                    ).to_dict()
                )
                used_short_claims.add(claim_id)

        scene_blueprints.append(
            SceneBlueprint(
                scene_id=scene.get("scene_id", f"scene_{idx:03d}"),
                title=scene.get("heading", ""),
                narrative_goal=scene.get("narration", "")[:180],
                claim_ids=claim_ids,
                evidence_ids=evidence_ids,
                evidence_level=evidence_level,
                benefit_harm_mode=benefit_harm_mode,
                visual_type=_infer_visual_type(scene),
                dossier_anchor_id=f"scene-{scene.get('scene_id', idx)}",
                cta_target="dossier" if idx == len(script.get("scenes", [])) else "",
                safety_flags=sorted(set(safety_flags)),
                allowed_out_of_context=all(claim_id in strongest for claim_id in claim_ids),
            ).to_dict()
        )

    return {
        "long_form": {
            "title": script.get("title", "CiteVideo Review"),
            "scene_blueprints": scene_blueprints,
        },
        "shorts": short_blueprints,
    }


def _infer_visual_type(scene: dict[str, Any]) -> str:
    scene_type = scene.get("type", "")
    if scene_type == "citation":
        return "study_card"
    if scene_type == "infographic":
        return "comparison_table"
    if scene_type == "source_list":
        return "source_stack"
    if scene_type == "title":
        return "hook_card"
    return "evidence_overlay"
