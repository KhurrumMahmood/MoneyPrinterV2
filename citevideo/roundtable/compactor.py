"""
Roundtable Conversation Compactor.

After every N rounds, compacts the conversation history into a dense
summary that preserves agent identities, key decisions, active threads,
and unresolved disagreements — while drastically reducing token count.

Each agent is also asked what THEY consider most important to keep,
ensuring the compaction reflects all perspectives.
"""

import json
from citevideo.llm import claude
from citevideo.roundtable.personas import PERSONAS, TURN_ORDER

COMPACTION_SYSTEM = (
    "You are a skilled meeting summarizer. You compress long multi-agent discussions "
    "into dense, structured summaries that preserve every agent's identity, their key "
    "positions, all decisions made, and any unresolved disagreements. You never lose "
    "important details. You respond with ONLY valid JSON."
)

AGENT_PRIORITY_PROMPT = """You are {agent_name}. You've been participating in a roundtable discussion about producing an honest, scientifically-cited health video review.

The discussion is about to be compacted to save context. In 3-5 bullet points, what are THE MOST IMPORTANT things from the conversation so far that MUST be preserved? Think about:
- Decisions that were made and must not be forgotten
- Your key positions that others need to remember
- Unresolved disagreements that still need resolution
- Specific creative ideas (hooks, visual treatments, structural beats) that were agreed on
- Any safety or accuracy concerns that must carry forward

Be specific. Reference claim IDs, scene ideas, and other agents by name.

## Conversation So Far
{conversation}"""

COMPACTION_PROMPT = """Compact the following roundtable conversation into a structured summary. This summary will REPLACE the full conversation as context for future rounds.

## Agent Priorities
Each agent was asked what they consider most important to preserve:

{agent_priorities}

## Full Conversation (Rounds {start_round}-{end_round})
{conversation}

---

Return a JSON object with this structure:

{{
  "rounds_covered": "{start_round}-{end_round}",
  "decisions_made": [
    "Specific decisions the group agreed on, with who proposed them"
  ],
  "unresolved_threads": [
    "Topics where agents disagree or haven't reached conclusion"
  ],
  "per_agent_positions": {{
    "dr_researcher": "Current stance, key concerns, proposals still on the table",
    "the_optimist": "...",
    "everyday_viewer": "...",
    "the_creator": "...",
    "the_director": "..."
  }},
  "video_structure_so_far": {{
    "hook": "Agreed opening hook (if decided)",
    "segments": ["Ordered list of agreed content segments with timing"],
    "visual_system": "Agreed visual approach for evidence levels, citations, etc.",
    "tone": "Agreed tone and approach"
  }},
  "key_creative_ideas": [
    "Specific creative proposals that were well-received (attribute to agent)"
  ],
  "safety_concerns": [
    "Any accuracy or safety issues that must be addressed in the final video"
  ],
  "claims_discussed": {{
    "claim_001": "Current consensus on how to handle this claim",
    "claim_002": "..."
  }}
}}

Be thorough but dense. Every fact in the summary should earn its place. This summary must give agents enough context to continue the discussion seamlessly."""


def collect_agent_priorities(conversation: str) -> dict:
    """
    Ask each agent what they consider most important to preserve.

    Returns dict mapping agent_key -> their priority list.
    """
    priorities = {}

    for agent_key in TURN_ORDER:
        persona = PERSONAS[agent_key]
        prompt = AGENT_PRIORITY_PROMPT.format(
            agent_name=persona["name"],
            conversation=conversation[-30000:],  # Last ~30K chars for context
        )

        try:
            response = claude(
                prompt=prompt,
                system_prompt=persona["system_prompt"],
                timeout=60,
                label=f"compaction:priorities:{agent_key}",
            )
            priorities[agent_key] = response
        except Exception as e:
            priorities[agent_key] = f"(Failed to collect priorities: {e})"

    return priorities


def compact_conversation(
    conversation: str,
    start_round: int,
    end_round: int,
    previous_summary: str = "",
) -> tuple:
    """
    Compact conversation rounds into a structured summary.

    Args:
        conversation: Full conversation markdown
        start_round: First round number being compacted
        end_round: Last round number being compacted
        previous_summary: Summary from earlier compaction (if any)

    Returns:
        Tuple of (summary_json_dict, formatted_summary_text)
    """
    # Step 1: Ask each agent what's important
    print(f"    Collecting agent priorities...")
    priorities = collect_agent_priorities(conversation)

    priorities_text = ""
    for agent_key, priority in priorities.items():
        name = PERSONAS[agent_key]["name"]
        priorities_text += f"\n### {name}\n{priority}\n"

    # Step 2: Generate compacted summary
    print(f"    Generating compacted summary...")
    prompt = COMPACTION_PROMPT.format(
        agent_priorities=priorities_text,
        conversation=conversation,
        start_round=start_round,
        end_round=end_round,
    )

    if previous_summary:
        prompt = f"## Previous Summary (Rounds before {start_round})\n{previous_summary}\n\n{prompt}"

    response = claude(
        prompt=prompt,
        system_prompt=COMPACTION_SYSTEM,
        timeout=180,
        label=f"compaction:summarize:r{start_round}-{end_round}",
    )

    # Parse JSON
    import re
    cleaned = response.replace("```json", "").replace("```", "").strip()
    try:
        summary = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            summary = json.loads(match.group())
        else:
            summary = {"raw_summary": cleaned[:5000], "parse_error": True}

    # Format as readable text for agents
    formatted = format_summary_for_agents(summary, previous_summary)

    return summary, formatted


def format_summary_for_agents(summary: dict, previous_summary: str = "") -> str:
    """Format the compacted summary as readable text for agent prompts."""
    lines = []

    if previous_summary:
        lines.append("## Earlier Discussion Summary")
        lines.append(previous_summary[:3000])
        lines.append("")

    rounds = summary.get("rounds_covered", "?")
    lines.append(f"## Compacted Summary (Rounds {rounds})")
    lines.append("")

    decisions = summary.get("decisions_made", [])
    if decisions:
        lines.append("### Decisions Made")
        for d in decisions:
            lines.append(f"- {d}")
        lines.append("")

    unresolved = summary.get("unresolved_threads", [])
    if unresolved:
        lines.append("### Unresolved Threads")
        for u in unresolved:
            lines.append(f"- {u}")
        lines.append("")

    positions = summary.get("per_agent_positions", {})
    if positions:
        lines.append("### Agent Positions")
        for agent, pos in positions.items():
            name = PERSONAS.get(agent, {}).get("name", agent)
            lines.append(f"**{name}**: {pos}")
        lines.append("")

    structure = summary.get("video_structure_so_far", {})
    if structure:
        lines.append("### Video Structure So Far")
        if structure.get("hook"):
            lines.append(f"**Hook**: {structure['hook']}")
        segments = structure.get("segments", [])
        for s in segments:
            lines.append(f"- {s}")
        if structure.get("visual_system"):
            lines.append(f"**Visuals**: {structure['visual_system']}")
        lines.append("")

    ideas = summary.get("key_creative_ideas", [])
    if ideas:
        lines.append("### Key Creative Ideas")
        for idea in ideas:
            lines.append(f"- {idea}")
        lines.append("")

    safety = summary.get("safety_concerns", [])
    if safety:
        lines.append("### Safety Concerns")
        for s in safety:
            lines.append(f"- {s}")
        lines.append("")

    return "\n".join(lines)
