"""
Preview render review helpers.
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any

from citevideo.review.models import ensure_review_dirs


def _extract_preview_frames(video_path: str, output_dir: str) -> list[str]:
    os.makedirs(output_dir, exist_ok=True)
    timestamps = [3, 10, 20, 35, 50, 57]
    frames = []
    for second in timestamps:
        output_path = os.path.join(output_dir, f"preview-{second:02d}.png")
        command = [
            "ffmpeg",
            "-y",
            "-ss",
            str(second),
            "-i",
            video_path,
            "-frames:v",
            "1",
            output_path,
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0 and os.path.exists(output_path):
            frames.append(output_path)
    return frames


def run_preview_board(run_dir: str, video_path: str) -> dict[str, Any]:
    review_dirs = ensure_review_dirs(run_dir)
    spec_path = os.path.join(run_dir, "production", "spec.json")
    with open(spec_path, "r", encoding="utf-8") as handle:
        spec = json.load(handle)

    frames = _extract_preview_frames(video_path, review_dirs["preview_frames"])
    scenes = spec.get("scenes", [])
    findings = []

    if scenes:
        opening = scenes[0]
        if opening.get("type") == "title" and not opening.get("imagePath"):
            findings.append(
                {
                    "severity": "major",
                    "scene_id": opening.get("sceneId", ""),
                    "problem": "Opening hook scene relies on design only, so its composition must work much harder.",
                    "fix": "Use a dedicated hook layout with visual contrast, bold comparison, and less empty space.",
                }
            )

    same_register_runs = 0
    previous_register = None
    for scene in scenes[:8]:
        current_register = scene.get("sceneRegister", "neutral")
        if current_register == previous_register:
            same_register_runs += 1
        else:
            same_register_runs = 0
        previous_register = current_register

    if same_register_runs >= 3:
        findings.append(
            {
                "severity": "major",
                "scene_id": "",
                "problem": "Opening stretch stays in the same visual/emotional register too long.",
                "fix": "Introduce stronger register changes or internal scene beats within the first minute.",
            }
        )

    payload: dict[str, Any] = {
        "stage": "preview",
        "video_path": video_path,
        "sample_frames": frames,
        "findings": findings,
        "decision": "revise" if findings else "pass",
    }
    out_path = os.path.join(review_dirs["preview"], "preview_review.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    fixlist_path = os.path.join(review_dirs["fixlists"], "preview_fixlist.json")
    with open(fixlist_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    return payload

