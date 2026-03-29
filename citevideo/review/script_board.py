"""
Structured script review board for CiteVideo.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from citevideo.backends.factory import get_review_backend
from citevideo.review.models import ensure_review_dirs


def _parse_json_response(raw: str, fallback: dict[str, Any]) -> dict[str, Any]:
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return fallback


REVIEWERS = {
    "creator": {
        "system": (
            "You review health/science YouTube scripts for hook strength, pacing, retention, "
            "and shareability. You are specific and practical. Return JSON only."
        ),
        "prompt": """Review this script as a YouTube creator strategist.

Return JSON with:
{
  "role": "creator",
  "scorecard": {"hook": 1-10, "retention": 1-10, "shareability": 1-10},
  "strengths": ["..."],
  "findings": [
    {"severity": "critical|major|minor", "scene_id": "scene_001", "problem": "...", "fix": "..."}
  ],
  "top_fixes": ["..."]
}

Script:
{script_json}
""",
    },
    "viewer": {
        "system": (
            "You are an intelligent health-interested viewer, not a scientist. You care about "
            "clarity, trust, and practical value. Return JSON only."
        ),
        "prompt": """Review this script as the target viewer.

Return JSON with:
{
  "role": "viewer",
  "scorecard": {"clarity": 1-10, "trust": 1-10, "actionability": 1-10},
  "strengths": ["..."],
  "findings": [
    {"severity": "critical|major|minor", "scene_id": "scene_001", "problem": "...", "fix": "..."}
  ],
  "top_fixes": ["..."]
}

Script:
{script_json}
""",
    },
    "director": {
        "system": (
            "You review scripts as a motion-design documentary director. Your job is to identify "
            "where the visual language will die, become repetitive, or fail to create memorable frames. "
            "Return JSON only."
        ),
        "prompt": """Review this script for visual storytelling potential.

Return JSON with:
{
  "role": "director",
  "scorecard": {"visual_rhythm": 1-10, "scene_variety": 1-10, "brand_potential": 1-10},
  "strengths": ["..."],
  "findings": [
    {"severity": "critical|major|minor", "scene_id": "scene_001", "problem": "...", "fix": "..."}
  ],
  "top_fixes": ["..."]
}

Script:
{script_json}
""",
    },
    "trust": {
        "system": (
            "You review evidence-first health media for honest framing. Flag overclaiming, hype, "
            "missing caveats, or language that sounds too much like the videos being critiqued. "
            "Return JSON only."
        ),
        "prompt": """Review this script for trustworthiness and honest framing.

Return JSON with:
{
  "role": "trust",
  "scorecard": {"honesty": 1-10, "evidence_visibility": 1-10, "tone": 1-10},
  "strengths": ["..."],
  "findings": [
    {"severity": "critical|major|minor", "scene_id": "scene_001", "problem": "...", "fix": "..."}
  ],
  "top_fixes": ["..."]
}

Script:
{script_json}
""",
    },
}


def run_script_board(run_dir: str) -> dict[str, Any]:
    prod_dir = os.path.join(run_dir, "production")
    script_path = os.path.join(prod_dir, "script_v3.json")
    if not os.path.exists(script_path):
        script_path = os.path.join(prod_dir, "script_v2.json")
    if not os.path.exists(script_path):
        script_path = os.path.join(prod_dir, "script_v1.json")

    with open(script_path, "r", encoding="utf-8") as handle:
        script = json.load(handle)

    review_dirs = ensure_review_dirs(run_dir)
    backend = get_review_backend()
    script_json = json.dumps(script, indent=2, ensure_ascii=False)

    results: dict[str, Any] = {"reviewers": {}}
    all_findings: list[dict[str, Any]] = []

    for role, config in REVIEWERS.items():
        response = backend.run(
            config["prompt"].format(script_json=script_json),
            system_prompt=config["system"],
            label=f"review-board:script:{role}",
            timeout=240,
        )
        parsed = _parse_json_response(
            response,
            {
                "role": role,
                "scorecard": {},
                "strengths": [],
                "findings": [],
                "top_fixes": [],
                "raw": response[:4000],
            },
        )
        results["reviewers"][role] = parsed
        all_findings.extend(parsed.get("findings", []))

        out_path = os.path.join(review_dirs["script"], f"{role}.json")
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(parsed, handle, indent=2, ensure_ascii=False)

    severity_order = {"critical": 0, "major": 1, "minor": 2}
    prioritized = sorted(
        all_findings,
        key=lambda item: (
            severity_order.get(item.get("severity", "minor"), 3),
            item.get("scene_id", ""),
            item.get("problem", ""),
        ),
    )

    fixlist = {
        "stage": "script",
        "decision": "revise" if prioritized else "pass",
        "priority_fixes": prioritized[:10],
    }
    fixlist_path = os.path.join(review_dirs["fixlists"], "script_fixlist.json")
    with open(fixlist_path, "w", encoding="utf-8") as handle:
        json.dump(fixlist, handle, indent=2, ensure_ascii=False)

    results["fixlist"] = fixlist
    return results

