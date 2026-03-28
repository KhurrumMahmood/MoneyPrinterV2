"""
Script Development (Phase 3a).

Transforms the content plan into a full narration script with
scene-by-scene structure, visual notes, and citation markers.
"""

import os
import json
import re
from citevideo.llm import claude

SCRIPT_SYSTEM = (
    "You are a science video scriptwriter who writes honest, engaging narration. "
    "You never overstate evidence, always cite sources, and make complex science "
    "accessible without dumbing it down. Your scripts are conversational but authoritative. "
    "You respond with ONLY valid JSON."
)

SCRIPT_PROMPT = """Write a full narration script for a scientifically-cited health video review.

## Content Plan
{content_plan}

## Evidence Data
{evidence_summary}

---

Write the script as a JSON array of scenes. Each scene includes the actual narration text that will be spoken, plus production metadata.

Return a JSON object:

{{
  "title": "Final video title",
  "estimated_duration_seconds": 300,
  "scenes": [
    {{
      "scene_id": "scene_001",
      "type": "title|talking_point|citation|infographic|image|source_list|transition",
      "heading": "Section heading shown on screen (if any)",
      "narration": "The exact text to be spoken by the narrator. Write it conversationally, as if talking to a friend who's smart but not a scientist. Include natural pauses with '...' where appropriate.",
      "visual_notes": "Specific description of what appears on screen during this narration",
      "citations_to_show": [
        {{
          "label": "Smith et al. (2024)",
          "detail": "Nature Medicine",
          "doi": "10.1038/...",
          "timestamp": "Show at this narration phrase"
        }}
      ],
      "evidence_strength": "strong|moderate|weak|mixed|none",
      "claims_referenced": ["claim_001"],
      "duration_estimate_seconds": 20,
      "mood": "curious|serious|hopeful|cautionary|excited|neutral"
    }}
  ],
  "closing_disclaimer": "Brief, honest disclaimer about the nature of this review",
  "sources_list": [
    {{
      "label": "Author et al. (Year)",
      "full_citation": "Full citation string",
      "doi": "..."
    }}
  ]
}}

Guidelines:
- The hook must grab attention in 3-5 seconds
- Every claim must reference its evidence strength
- Weak evidence MUST include honest caveats ('this is preliminary', 'only studied in mice')
- Include natural transitions between sections
- End with actionable takeaways, not just facts
- Include a source list scene at the end
- Write for ~{target_duration} seconds of narration (about {word_count} words total)
- Vary scene types for visual variety
- Place citations where the viewer can see them when the claim is being made"""


def write_script(run_dir: str) -> dict:
    """
    Generate the first draft script from the content plan.

    Args:
        run_dir: Run directory path

    Returns:
        Script dict with scenes array
    """
    # Load content plan
    plan_path = os.path.join(run_dir, "roundtable", "content_plan.json")
    with open(plan_path) as f:
        content_plan = json.load(f)

    # Load evidence
    evidence_path = os.path.join(run_dir, "evidence.json")
    with open(evidence_path) as f:
        evidence = json.load(f)

    # Build evidence summary
    evidence_lines = []
    for r in evidence.get("ratings", []):
        er = r.get("evidence_rating", {})
        v = r.get("verification", {})
        cid = r.get("claim_id", "?")
        text = r.get("claim_text", "")

        evidence_lines.append(f"### {cid}: {text}")
        evidence_lines.append(f"Accuracy: {er.get('accuracy_score', '?')}/5 ({er.get('accuracy_label', '?')})")
        evidence_lines.append(f"Evidence: {er.get('evidence_label', '?')}")
        evidence_lines.append(f"Extrapolation risk: {er.get('extrapolation_risk', '?')}")

        if v.get("paper"):
            p = v["paper"]
            evidence_lines.append(f"Paper: {p.get('title', '?')} - {p.get('journal', '?')} ({p.get('year', '?')})")
            if p.get("doi"):
                evidence_lines.append(f"DOI: {p['doi']}")

        if v.get("what_study_actually_found"):
            evidence_lines.append(f"Study found: {v['what_study_actually_found']}")
        if r.get("recommended_framing"):
            evidence_lines.append(f"Framing: {r['recommended_framing']}")

        evidence_lines.append("")

    evidence_summary = "\n".join(evidence_lines)

    # Get target duration — script Video A (first video) by default
    video = content_plan.get("videos", [{}])[0]
    target_duration = video.get("target_duration_seconds", 300)
    word_count = int(target_duration * 2.5)  # ~150 words per minute

    # Trim content plan to just the relevant video + brand notes to control prompt size
    trimmed_plan = {
        "video": video,
        "brand_notes": content_plan.get("brand_notes", {}),
        "split_decision": content_plan.get("split_decision", {}),
    }

    # Truncate evidence summary if very large
    if len(evidence_summary) > 15000:
        evidence_summary = evidence_summary[:15000] + "\n\n(... truncated for brevity)"

    prompt = SCRIPT_PROMPT.format(
        content_plan=json.dumps(trimmed_plan, indent=2),
        evidence_summary=evidence_summary,
        target_duration=target_duration,
        word_count=word_count,
    )

    print(f"  Writing script draft 1... (prompt: {len(prompt)} chars)")
    response = claude(prompt, system_prompt=SCRIPT_SYSTEM, timeout=600,
                      label="scriptwriter:draft1")

    # Parse
    cleaned = response.replace("```json", "").replace("```", "").strip()
    try:
        script = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            script = json.loads(match.group())
        else:
            raise RuntimeError(f"Failed to parse script JSON:\n{cleaned[:500]}")

    # Save
    prod_dir = os.path.join(run_dir, "production")
    os.makedirs(prod_dir, exist_ok=True)
    script_path = os.path.join(prod_dir, "script_v1.json")
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)

    scenes = script.get("scenes", [])
    total_narration = sum(len(s.get("narration", "").split()) for s in scenes)
    print(f"  Draft 1: {len(scenes)} scenes, ~{total_narration} words (~{total_narration // 2.5:.0f}s)")
    print(f"  Saved to {script_path}")

    return script
