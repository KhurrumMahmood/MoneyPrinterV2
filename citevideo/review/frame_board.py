"""
Scene-frame review helpers for CiteVideo.
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any

from citevideo.review.models import ensure_review_dirs


def _load_spec(run_dir: str) -> dict[str, Any]:
    spec_path = os.path.join(run_dir, "production", "spec.json")
    with open(spec_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def capture_scene_frames(run_dir: str) -> list[str]:
    review_dirs = ensure_review_dirs(run_dir)
    remotion_root = os.path.join(os.path.dirname(os.path.dirname(run_dir)), "remotion")
    public_spec = os.path.join(
        remotion_root,
        "public",
        "assets",
        os.path.basename(run_dir),
        "spec.json",
    )
    capture_script = os.path.join(remotion_root, "capture-frames.ts")
    tsx_binary = os.path.join(remotion_root, "node_modules", ".bin", "tsx")
    node_binary = os.environ.get("CITEVIDEO_NODE_BINARY") or "/Users/khurrummahmood/.nvm/versions/node/v22.21.1/bin/node"

    if not (os.path.exists(capture_script) and os.path.exists(tsx_binary) and os.path.exists(public_spec)):
        return []

    os.makedirs(review_dirs["frame_captures"], exist_ok=True)
    public_arg = f"assets/{os.path.basename(run_dir)}/spec.json"
    command = [node_binary, tsx_binary, capture_script, public_arg, review_dirs["frame_captures"]]
    result = subprocess.run(command, cwd=remotion_root, capture_output=True, text=True)
    if result.returncode != 0:
        return []
    return sorted(
        os.path.join(review_dirs["frame_captures"], name)
        for name in os.listdir(review_dirs["frame_captures"])
        if name.endswith(".png")
    )


def run_frame_board(run_dir: str) -> dict[str, Any]:
    review_dirs = ensure_review_dirs(run_dir)
    spec = _load_spec(run_dir)
    captured = capture_scene_frames(run_dir)
    capture_map = {
        os.path.splitext(os.path.basename(path))[0]: path
        for path in captured
    }

    findings: list[dict[str, Any]] = []
    previous_visual_type = None
    repetitive_run = 0

    for scene in spec.get("scenes", []):
        scene_id = scene.get("sceneId", "")
        visual_type = scene.get("visualType", "unknown")
        if visual_type == previous_visual_type:
            repetitive_run += 1
        else:
            repetitive_run = 0
        previous_visual_type = visual_type

        scene_findings = []
        if not scene.get("imagePath") and visual_type in {"hook_card", "evidence_overlay"}:
            scene_findings.append(
                {
                    "severity": "major",
                    "scene_id": scene_id,
                    "problem": "Scene has no generated image and depends entirely on renderer design.",
                    "fix": "Use a stronger programmatic visual layout or add image-backed coverage.",
                }
            )
        if len(scene.get("keywords", [])) == 0:
            scene_findings.append(
                {
                    "severity": "major",
                    "scene_id": scene_id,
                    "problem": "Scene has no keyword layer for fast visual comprehension.",
                    "fix": "Derive 1-3 keywords and make them visible in the composition.",
                }
            )
        if repetitive_run >= 2:
            scene_findings.append(
                {
                    "severity": "major",
                    "scene_id": scene_id,
                    "problem": "Multiple consecutive scenes use the same visual mode.",
                    "fix": "Introduce a different scene family or a stronger internal beat change.",
                }
            )
        if scene.get("type") == "citation" and not scene.get("citationCard") and not scene.get("citations"):
            scene_findings.append(
                {
                    "severity": "critical",
                    "scene_id": scene_id,
                    "problem": "Citation scene has no visible citation payload.",
                    "fix": "Populate citation card metadata or downgrade the scene type.",
                }
            )

        review_payload = {
            "scene_id": scene_id,
            "frame_path": capture_map.get(scene_id, ""),
            "visual_type": visual_type,
            "scene_register": scene.get("sceneRegister", "neutral"),
            "checks": {
                "has_keywords": bool(scene.get("keywords")),
                "has_image": bool(scene.get("imagePath")),
                "has_trust_signal": bool(
                    scene.get("citationCard")
                    or scene.get("citations")
                    or scene.get("evidenceIds")
                    or scene.get("safetyFlags")
                ),
                "repetitive_visual_run": repetitive_run >= 2,
            },
            "findings": scene_findings,
        }
        out_path = os.path.join(review_dirs["frames"], f"{scene_id}.json")
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(review_payload, handle, indent=2, ensure_ascii=False)
        findings.extend(scene_findings)

    fixlist = {
        "stage": "frames",
        "decision": "revise" if findings else "pass",
        "priority_fixes": findings[:12],
        "captured_frames": captured,
    }
    fixlist_path = os.path.join(review_dirs["fixlists"], "frame_fixlist.json")
    with open(fixlist_path, "w", encoding="utf-8") as handle:
        json.dump(fixlist, handle, indent=2, ensure_ascii=False)
    return fixlist
