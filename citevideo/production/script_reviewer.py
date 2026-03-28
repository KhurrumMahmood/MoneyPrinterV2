"""
Script Review (Phase 3b).

Two specialist review passes on the draft script:
1. Marketer review: hooks, pacing, engagement
2. Layperson review: clarity, jargon, actionability

Then applies revisions to produce script_v2.
"""

import os
import json
import re
from citevideo.llm import claude

MARKETER_SYSTEM = (
    "You are a YouTube content strategist who specializes in health/science channels. "
    "You have grown 3 channels past 100K subscribers. You know exactly what makes "
    "viewers click, watch, and share. You review scripts for engagement, pacing, and "
    "retention. You respond with ONLY valid JSON."
)

MARKETER_PROMPT = """Review this video script for engagement and retention. You are looking at Draft 1.

## Script
{script_json}

---

Produce a JSON review:

{{
  "hook_rating": 1-10,
  "hook_feedback": "What works, what doesn't, specific improvement",
  "pacing_rating": 1-10,
  "pacing_notes": [
    {{"scene_id": "scene_001", "issue": "Too slow / too fast / missing transition", "suggestion": "..."}}
  ],
  "retention_risks": [
    {{"timestamp_approx": "30s", "risk": "Viewer might drop here because...", "fix": "..."}}
  ],
  "missing_elements": ["Pattern interrupts, callbacks, open loops that should be added"],
  "strongest_moments": ["Scenes that will land well and why"],
  "overall_engagement_score": 1-10,
  "top_3_improvements": ["Most impactful changes, in order"]
}}

Be specific. Reference scene IDs. Think about the viewer's second-by-second experience."""

LAYPERSON_SYSTEM = (
    "You are an intelligent adult who is NOT a scientist. You watch health content on YouTube "
    "to improve your health. You have a good BS detector. You care about clarity and honesty. "
    "If something is confusing, you'll say so. If something feels like hype, you'll flag it. "
    "You respond with ONLY valid JSON."
)

LAYPERSON_PROMPT = """Read this video script as if you're watching the video. You are the target audience: 40-55, health-conscious, not a scientist.

## Script
{script_json}

---

Produce a JSON review:

{{
  "clarity_rating": 1-10,
  "jargon_issues": [
    {{"scene_id": "scene_001", "term": "autophagy", "suggestion": "Explain it as '...'"}}
  ],
  "confusing_sections": [
    {{"scene_id": "scene_003", "what_confused_me": "...", "what_would_help": "..."}}
  ],
  "trust_issues": [
    {{"scene_id": "...", "concern": "This feels like hype / unsupported / scary without context"}}
  ],
  "actionability_rating": 1-10,
  "what_i_would_do": "After watching this, here's what I would actually DO",
  "missing_questions": ["Questions I still have that the video didn't answer"],
  "emotional_reactions": [
    {{"scene_id": "...", "reaction": "This made me feel hopeful / skeptical / confused / etc."}}
  ],
  "would_i_share": true/false,
  "share_reason": "Why or why not I'd share this with friends/family",
  "overall_score": 1-10,
  "top_3_improvements": ["Most impactful changes for someone like me"]
}}

Be honest. If the script talks down to you, say so. If it's too academic, say so."""

REVISION_SYSTEM = (
    "You are a script editor. You take a draft script and two reviews (marketer + layperson) "
    "and produce an improved version. You make targeted edits — don't rewrite everything, "
    "just fix the issues flagged. Preserve all citations and evidence ratings. "
    "You respond with ONLY valid JSON in the same format as the input script."
)

REVISION_PROMPT = """Revise this video script based on two specialist reviews.

## Current Script (Draft 1)
{script_json}

## Marketer Review
{marketer_review}

## Layperson Review
{layperson_review}

---

Apply the most impactful improvements from both reviews. Your priorities:
1. Fix any clarity issues (if the layperson was confused, fix it)
2. Strengthen the hook and pacing (per marketer feedback)
3. Add jargon explanations where needed
4. Address trust concerns (add caveats, honest framing)
5. Improve transitions and retention elements

Return the FULL revised script in the same JSON format as the input.
Keep all citations, evidence_strength ratings, and claims_referenced intact.
Add a "revision_notes" field listing what you changed and why."""


def review_and_revise(run_dir: str) -> dict:
    """
    Run marketer + layperson reviews, then apply revisions.

    Args:
        run_dir: Run directory path

    Returns:
        Revised script dict (v2)
    """
    prod_dir = os.path.join(run_dir, "production")

    # Load draft 1
    with open(os.path.join(prod_dir, "script_v1.json")) as f:
        script = json.load(f)

    script_json = json.dumps(script, indent=2)

    # Marketer review
    print("  Running marketer review...")
    marketer_response = claude(
        MARKETER_PROMPT.format(script_json=script_json),
        system_prompt=MARKETER_SYSTEM,
        timeout=600,
        label="reviewer:marketer",
    )
    marketer_cleaned = marketer_response.replace("```json", "").replace("```", "").strip()
    try:
        marketer_review = json.loads(marketer_cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", marketer_cleaned, re.DOTALL)
        marketer_review = json.loads(match.group()) if match else {"raw": marketer_cleaned[:2000]}

    # Save marketer review
    with open(os.path.join(prod_dir, "review_marketer.json"), "w") as f:
        json.dump(marketer_review, f, indent=2, ensure_ascii=False)
    print(f"    Hook: {marketer_review.get('hook_rating', '?')}/10, "
          f"Engagement: {marketer_review.get('overall_engagement_score', '?')}/10")

    # Layperson review
    print("  Running layperson review...")
    layperson_response = claude(
        LAYPERSON_PROMPT.format(script_json=script_json),
        system_prompt=LAYPERSON_SYSTEM,
        timeout=600,
        label="reviewer:layperson",
    )
    layperson_cleaned = layperson_response.replace("```json", "").replace("```", "").strip()
    try:
        layperson_review = json.loads(layperson_cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", layperson_cleaned, re.DOTALL)
        layperson_review = json.loads(match.group()) if match else {"raw": layperson_cleaned[:2000]}

    # Save layperson review
    with open(os.path.join(prod_dir, "review_layperson.json"), "w") as f:
        json.dump(layperson_review, f, indent=2, ensure_ascii=False)
    print(f"    Clarity: {layperson_review.get('clarity_rating', '?')}/10, "
          f"Would share: {layperson_review.get('would_i_share', '?')}")

    # Apply revisions
    print("  Applying revisions → draft 2...")
    revision_response = claude(
        REVISION_PROMPT.format(
            script_json=script_json,
            marketer_review=json.dumps(marketer_review, indent=2),
            layperson_review=json.dumps(layperson_review, indent=2),
        ),
        system_prompt=REVISION_SYSTEM,
        timeout=600,
        label="reviewer:revision",
    )

    revision_cleaned = revision_response.replace("```json", "").replace("```", "").strip()
    try:
        script_v2 = json.loads(revision_cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", revision_cleaned, re.DOTALL)
        if match:
            script_v2 = json.loads(match.group())
        else:
            raise RuntimeError(f"Failed to parse revised script:\n{revision_cleaned[:500]}")

    # Save
    v2_path = os.path.join(prod_dir, "script_v2.json")
    with open(v2_path, "w", encoding="utf-8") as f:
        json.dump(script_v2, f, indent=2, ensure_ascii=False)

    scenes = script_v2.get("scenes", [])
    total_words = sum(len(s.get("narration", "").split()) for s in scenes)
    print(f"  Draft 2: {len(scenes)} scenes, ~{total_words} words")
    print(f"  Saved to {v2_path}")

    return script_v2
