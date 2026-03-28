"""
Content Plan Synthesizer (Phase 2b).

Reads the full roundtable conversation and produces a structured
content plan that the scriptwriter can work from.
"""

import os
import json
import re
from citevideo.llm import claude

SYNTHESIS_SYSTEM = (
    "You are a content strategist who reads creative roundtable discussions and "
    "produces structured video production plans. You extract the best ideas from "
    "the discussion, resolve any disagreements by finding consensus, and produce "
    "a clear, actionable plan. You respond with ONLY valid JSON."
)

SYNTHESIS_PROMPT = """You have just observed a {num_rounds}-round roundtable discussion between 5 creative agents about producing an honest, scientifically-cited review video of a health YouTube video.

## Full Roundtable Conversation
{conversation}

## Evidence Summary
{evidence_summary}

---

Now synthesize the discussion into a structured content plan. The plan should capture the best ideas from ALL agents and resolve any disagreements.

Return a JSON object:

{{
  "video_count": 1,
  "videos": [
    {{
      "title": "Working title for this video",
      "hook": "The opening line/hook (5-10 seconds)",
      "hook_variants": ["2-3 alternative hooks discussed"],
      "target_duration_seconds": 300,
      "audience": {{
        "primary": "Description of primary audience",
        "pain_points": ["What brings them to this content"],
        "desired_outcome": "What they should feel/know after watching"
      }},
      "scenes": [
        {{
          "scene_id": "scene_001",
          "type": "title|talking_point|citation|infographic|image|source_list",
          "heading": "Section heading (if applicable)",
          "content_notes": "What this scene covers — key points, claims, evidence",
          "claims_referenced": ["claim_001", "claim_002"],
          "visual_treatment": "Specific visual direction from The Director",
          "evidence_strength_indicator": "strong|moderate|weak|mixed",
          "duration_estimate_seconds": 30,
          "retention_notes": "Any engagement/pacing notes from The Creator"
        }}
      ],
      "key_citations": [
        {{
          "claim_id": "claim_001",
          "citation_label": "Smith et al. (2024)",
          "detail": "Journal, finding summary",
          "must_show_on_screen": true
        }}
      ],
      "warnings": [
        "Any weak evidence that needs disclaimers, per Dr. Researcher"
      ],
      "safety_notes": [
        "Any safety concerns from Everyday Viewer"
      ],
      "emotional_arc": "Description of the emotional journey: tension → resolution → etc.",
      "call_to_action": "What we ask the viewer to do at the end"
    }}
  ],
  "brand_notes": {{
    "tone": "Overall tone direction",
    "visual_style": "Key visual direction from The Director",
    "evidence_visual_system": "How we visually distinguish evidence strength levels",
    "citation_style": "How citations appear on screen"
  }},
  "split_decision": {{
    "should_split": false,
    "reasoning": "Why one video vs multiple"
  }},
  "discussion_highlights": [
    "Key insights or debates from the roundtable worth preserving"
  ]
}}

Be thorough. Every scene should be specific enough for a scriptwriter to work from. Include ALL claims that should be covered and flag which ones need caveats."""


def synthesize_content_plan(
    roundtable_dir: str,
    conversation: str,
    evidence: dict,
) -> dict:
    """
    Synthesize the roundtable conversation into a content plan.

    Args:
        roundtable_dir: Path to roundtable directory
        conversation: Full conversation markdown
        evidence: Parsed evidence.json

    Returns:
        Content plan dict
    """
    # Build condensed evidence summary for the prompt
    evidence_lines = []
    for r in evidence.get("ratings", []):
        er = r.get("evidence_rating", {})
        cid = r.get("claim_id", "?")
        text = r.get("claim_text", "")[:100]
        score = er.get("accuracy_score", "?")
        strength = er.get("evidence_label", "?")
        evidence_lines.append(f"- {cid}: {text} (accuracy: {score}/5, evidence: {strength})")

    evidence_summary = "\n".join(evidence_lines)

    # Count rounds from control.json
    control_path = os.path.join(roundtable_dir, "control.json")
    num_rounds = 12
    if os.path.exists(control_path):
        with open(control_path) as f:
            control = json.load(f)
            num_rounds = control.get("total_rounds", 12)

    # For large conversations, use only the convergence rounds (last ~80K chars)
    # plus a brief note about total scope. The convergence rounds contain the
    # agents' final agreements and resolved decisions.
    MAX_CONVERSATION_CHARS = 80000
    if len(conversation) > MAX_CONVERSATION_CHARS:
        # Find a round boundary near the cutoff point
        cutoff_start = len(conversation) - MAX_CONVERSATION_CHARS
        # Find the next "## " (round header) after the cutoff
        next_header = conversation.find("\n## ", cutoff_start)
        if next_header > 0:
            truncated = conversation[next_header:]
        else:
            truncated = conversation[-MAX_CONVERSATION_CHARS:]
        convo_for_prompt = (
            f"(Earlier rounds 1-7 omitted for brevity — {len(conversation)} chars total. "
            f"The discussion below covers the convergence rounds where agents finalized decisions.)\n\n"
            + truncated
        )
        print(f"  Conversation truncated: {len(conversation)} → {len(convo_for_prompt)} chars (convergence rounds)")
    else:
        convo_for_prompt = conversation

    prompt = SYNTHESIS_PROMPT.format(
        num_rounds=num_rounds,
        conversation=convo_for_prompt,
        evidence_summary=evidence_summary,
    )

    print("  Synthesizing content plan from roundtable...")
    response = claude(prompt, system_prompt=SYNTHESIS_SYSTEM, timeout=600)

    # Parse JSON
    cleaned = response.replace("```json", "").replace("```", "").strip()
    try:
        plan = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            plan = json.loads(match.group())
        else:
            raise RuntimeError(f"Failed to parse content plan JSON:\n{cleaned[:500]}")

    # Save
    plan_path = os.path.join(roundtable_dir, "content_plan.json")
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    videos = plan.get("videos", [])
    scenes = sum(len(v.get("scenes", [])) for v in videos)
    print(f"  Content plan: {len(videos)} video(s), {scenes} scenes total")

    return plan
