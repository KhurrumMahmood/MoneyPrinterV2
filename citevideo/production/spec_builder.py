"""
Remotion Spec Builder (Phase 4c).

Assembles the final video spec JSON from script + assets + timings.
This spec is consumed by the Remotion rendering pipeline.
"""

import os
import json
import shutil


def _derive_keywords(scene: dict) -> list[str]:
    existing = scene.get("keywords")
    if isinstance(existing, list) and existing:
        return existing[:4]

    heading = (
        scene.get("heading", "")
        .replace("Rapid-Fire", "")
        .replace("—", " ")
        .replace("-", " ")
        .replace(":", " ")
    )
    heading_words = []
    for raw_word in heading.split():
        cleaned = "".join(ch for ch in raw_word if ch.isalnum())
        if len(cleaned) >= 4 and cleaned.lower() not in {"this", "that", "with", "your", "into", "from"}:
            heading_words.append(cleaned)

    narration_words = []
    for word in scene.get("narration", "").replace("—", " ").split():
        cleaned = "".join(ch for ch in word if ch.isalnum())
        if len(cleaned) >= 5 and cleaned.lower() not in {
            "their",
            "there",
            "which",
            "about",
            "would",
            "these",
        }:
            narration_words.append(cleaned)

    deduped: list[str] = []
    for word in heading_words + narration_words:
        title_word = word.title()
        if title_word not in deduped:
            deduped.append(title_word)
        if len(deduped) >= 4:
            break
    return deduped


def _derive_scene_register(scene: dict, blueprint: dict) -> str:
    combined = " ".join(
        [
            scene.get("heading", ""),
            scene.get("narration", ""),
            scene.get("visual_notes", ""),
            blueprint.get("visual_type", ""),
        ]
    ).lower()

    if any(token in combined for token in ("warning", "danger", "safety", "correction", "free pass")):
        return "warning"
    if any(token in combined for token in ("swap", "choose", "pair", "order", "lentils", "what you can")):
        return "action"
    if scene.get("type") == "citation" or "study" in blueprint.get("visual_type", ""):
        return "clinical"
    if scene.get("type") == "title" or blueprint.get("visual_type") == "hook_card":
        return "hook"
    if scene.get("mood") in {"hopeful", "excited"} or scene.get("evidence_strength") == "strong":
        return "kitchen"
    return "neutral"


def build_spec(run_dir: str) -> dict:
    """
    Assemble the Remotion video spec from all production artifacts.

    Args:
        run_dir: Run directory path

    Returns:
        Complete video spec dict
    """
    prod_dir = os.path.join(run_dir, "production")
    assets_dir = os.path.join(prod_dir, "assets")

    # Load script
    script_path = os.path.join(prod_dir, "script_v3.json")
    if not os.path.exists(script_path):
        script_path = os.path.join(prod_dir, "script_v2.json")
    if not os.path.exists(script_path):
        script_path = os.path.join(prod_dir, "script_v1.json")

    with open(script_path) as f:
        script = json.load(f)

    package_dir = os.path.join(run_dir, "package")
    delivery_manifest_path = os.path.join(package_dir, "delivery_manifest.json")
    delivery_manifest = {}
    if os.path.exists(delivery_manifest_path):
        with open(delivery_manifest_path) as f:
            delivery_manifest = json.load(f)

    corrections_path = os.path.join(package_dir, "corrections.json")
    corrections = {"items": []}
    if os.path.exists(corrections_path):
        with open(corrections_path) as f:
            corrections = json.load(f)

    # Load asset manifest
    manifest_path = os.path.join(assets_dir, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)

    # Load brand kit
    brand_colors = {
        "primary": "#0f172a",
        "secondary": "#1e293b",
        "accent": "#06b6d4",
        "text": "#f8fafc",
        "textSecondary": "#94a3b8",
        "success": "#22c55e",
        "warning": "#eab308",
        "danger": "#ef4444",
    }
    brand_fonts = {
        "heading": "Inter",
        "body": "Inter",
    }

    brand_path = os.path.join(os.path.dirname(run_dir), "brand", "brand_kit.json")
    if os.path.exists(brand_path):
        with open(brand_path) as f:
            brand = json.load(f)
            brand_colors.update(brand.get("colors", {}))
            brand_fonts.update(brand.get("fonts", {}))

    # Copy assets to remotion public directory
    remotion_root = os.path.join(os.path.dirname(os.path.dirname(run_dir)), "remotion")
    remotion_assets = os.path.join(remotion_root, "public", "assets", os.path.basename(run_dir))
    os.makedirs(remotion_assets, exist_ok=True)

    # Copy audio
    wav_src = manifest.get("wav_path", "")
    if wav_src and os.path.exists(wav_src):
        wav_dest = os.path.join(remotion_assets, "narration.wav")
        shutil.copy2(wav_src, wav_dest)

    # Copy SRT
    srt_src = manifest.get("srt_path", "")
    if srt_src and os.path.exists(srt_src):
        srt_dest = os.path.join(remotion_assets, "narration.srt")
        shutil.copy2(srt_src, srt_dest)

    # Copy images
    image_map = manifest.get("image_map", {})
    remotion_image_map = {}
    for scene_id, img_path in image_map.items():
        if os.path.exists(img_path):
            ext = os.path.splitext(img_path)[1]
            dest = os.path.join(remotion_assets, f"{scene_id}{ext}")
            shutil.copy2(img_path, dest)
            # Relative path for Remotion's staticFile()
            remotion_image_map[scene_id] = f"assets/{os.path.basename(run_dir)}/{scene_id}{ext}"

    # Build timings lookup
    timings = {t["scene_id"]: t for t in manifest.get("timings", [])}

    # Evidence strength to visual indicator mapping
    strength_colors = {
        "strong": brand_colors.get("success", "#22c55e"),
        "moderate": brand_colors.get("warning", "#eab308"),
        "weak": brand_colors.get("danger", "#ef4444"),
        "mixed": brand_colors.get("warning", "#eab308"),
        "none": brand_colors.get("textSecondary", "#94a3b8"),
    }

    # Build scenes array for Remotion
    fps = 30
    scenes_spec = []
    blueprints = {
        item.get("scene_id"): item
        for item in delivery_manifest.get("long_form", {}).get("scene_blueprints", [])
    }

    for scene in script.get("scenes", []):
        scene_id = scene.get("scene_id", "")
        timing = timings.get(scene_id, {})
        duration_ms = timing.get("duration_ms", scene.get("duration_estimate_seconds", 10) * 1000)
        duration_frames = max(1, int(duration_ms / 1000 * fps))
        blueprint = blueprints.get(scene_id, {})
        citations = scene.get("citations_to_show", [])

        citation_card = None
        if citations:
            first_citation = citations[0]
            citation_card = {
                "label": first_citation.get("label", ""),
                "detail": first_citation.get("detail", ""),
                "doi": first_citation.get("doi", ""),
            }

        scene_spec = {
            "sceneId": scene_id,
            "type": scene.get("type", "talking_point"),
            "heading": scene.get("heading", ""),
            "narration": scene.get("narration", ""),
            "durationMs": duration_ms,
            "durationFrames": duration_frames,
            "mood": scene.get("mood", "neutral"),
            "evidenceStrength": scene.get("evidence_strength", "none"),
            "evidenceColor": strength_colors.get(scene.get("evidence_strength", "none"), "#94a3b8"),
            "claimsReferenced": scene.get("claims_referenced", []),
            "visualNotes": scene.get("visual_notes", ""),
            "keywords": _derive_keywords(scene),
            "visualType": blueprint.get("visual_type", "evidence_overlay"),
            "benefitHarmMode": blueprint.get("benefit_harm_mode", "benefit"),
            "citationCard": citation_card,
            "visualBeats": _default_visual_beats(scene),
            "safetyFlags": blueprint.get("safety_flags", []),
            "allowedOutOfContext": blueprint.get("allowed_out_of_context", False),
            "ctaTarget": blueprint.get("cta_target", ""),
            "dossierAnchorId": blueprint.get("dossier_anchor_id", f"scene-{scene_id}"),
            "evidenceIds": blueprint.get("evidence_ids", []),
            "sceneRegister": _derive_scene_register(scene, blueprint),
        }

        # Add image path if available
        if scene_id in remotion_image_map:
            scene_spec["imagePath"] = remotion_image_map[scene_id]

        # Add citations
        if citations:
            scene_spec["citations"] = citations

        scenes_spec.append(scene_spec)

    # Compute total duration
    total_frames = sum(s["durationFrames"] for s in scenes_spec)
    total_duration_ms = sum(s["durationMs"] for s in scenes_spec)

    # Build final spec
    run_name = os.path.basename(run_dir)
    spec = {
        "meta": {
            "runId": run_name,
            "title": script.get("title", "CiteVideo Review"),
            "fps": fps,
            "width": 1920,
            "height": 1080,
            "totalDurationFrames": total_frames,
            "totalDurationMs": total_duration_ms,
        },
        "brand": {
            "colors": brand_colors,
            "fonts": brand_fonts,
        },
        "audio": {
            "path": f"assets/{run_name}/narration.wav",
            "srtPath": f"assets/{run_name}/narration.srt",
        },
        "scenes": scenes_spec,
        "sourcesList": script.get("sources_list", []),
        "disclaimer": script.get("closing_disclaimer", ""),
        "web": {
            "dossierAnchorBase": run_name,
        },
        "corrections": corrections.get("items", []),
        "delivery": {
            "shorts": delivery_manifest.get("shorts", []),
        },
    }

    # Save spec
    spec_path = os.path.join(prod_dir, "spec.json")
    with open(spec_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)

    # Also save to remotion public for easy access
    remotion_spec_path = os.path.join(remotion_assets, "spec.json")
    with open(remotion_spec_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)

    print(f"  Spec: {len(scenes_spec)} scenes, {total_frames} frames ({total_duration_ms/1000:.1f}s)")
    print(f"  Saved to {spec_path}")
    print(f"  Remotion assets copied to {remotion_assets}")

    return spec


def _default_visual_beats(scene: dict) -> list[dict]:
    scene_type = scene.get("type", "talking_point")
    beats = [
        {"timeOffset": 0.0, "type": "overlay-enter", "target": "headline"},
        {"timeOffset": 2.5, "type": "highlight", "target": "evidence"},
    ]
    if scene_type in {"infographic", "citation"}:
        beats.append({"timeOffset": 5.0, "type": "reveal", "target": "details"})
    else:
        beats.append({"timeOffset": 5.0, "type": "zoom", "target": "background"})
    return beats
