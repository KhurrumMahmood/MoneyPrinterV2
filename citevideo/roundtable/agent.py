"""
Roundtable Agent Turn Handler.

Each agent turn is a stateless Claude CLI call. The full conversation
history is passed as context so the agent can reference what others said.
"""

from citevideo.llm import claude
from citevideo.roundtable.personas import PERSONAS, CONVERGENCE_ROUND


def _build_turn_prompt(
    persona_key: str,
    conversation_so_far: str,
    evidence_summary: str,
    round_num: int,
    total_rounds: int,
    transcript_excerpt: str = "",
) -> str:
    """Build the prompt for a single agent turn."""
    persona = PERSONAS[persona_key]

    convergence_note = ""
    if round_num >= CONVERGENCE_ROUND:
        rounds_left = total_rounds - round_num
        convergence_note = (
            f"\n\n⚠️ CONVERGENCE MODE: Only {rounds_left + 1} rounds left (including this one). "
            f"Focus on:\n"
            f"- Finalizing recommendations (not opening new threads)\n"
            f"- Resolving any disagreements\n"
            f"- Confirming the content structure everyone can agree on\n"
            f"- Being specific about what goes in the final video"
        )

    split_note = ""
    if round_num >= 3:
        split_note = (
            "\n\nIf you believe the content should be split into multiple videos "
            "(e.g., the material is too dense for one 5-minute video), say "
            "'SPLIT_RECOMMENDATION:' followed by your reasoning and proposed split."
        )

    prompt = f"""You are participating in round {round_num} of {total_rounds} in a creative roundtable discussion.

Your role: {persona['name']} — focused on {persona['focus']}.

## Research Evidence Summary
{evidence_summary}

## Original Video Transcript (excerpt)
{transcript_excerpt[:3000] if transcript_excerpt else "(See evidence summary for claim details)"}

## Conversation So Far
{conversation_so_far if conversation_so_far else "(You are starting the discussion. Set the tone and identify the key issues.)"}

---

## Your Turn

Contribute your perspective as {persona['name']}. Guidelines:
- Keep your response under 500 words
- Reference other agents by name when agreeing, disagreeing, or building on their points
- Be specific: name claim IDs, suggest exact visual treatments, propose specific hooks
- Don't repeat what's already been said — add NEW value
- If this is your first turn, introduce the main issues from your perspective{convergence_note}{split_note}

Respond as {persona['name']} only. Do not break character."""

    return prompt


def take_turn(
    persona_key: str,
    conversation_so_far: str,
    evidence_summary: str,
    round_num: int,
    total_rounds: int,
    transcript_excerpt: str = "",
    model: str = None,
) -> str:
    """
    Execute one agent's turn in the roundtable.

    Returns the agent's response text (without persona header — caller adds that).
    """
    persona = PERSONAS[persona_key]
    prompt = _build_turn_prompt(
        persona_key=persona_key,
        conversation_so_far=conversation_so_far,
        evidence_summary=evidence_summary,
        round_num=round_num,
        total_rounds=total_rounds,
        transcript_excerpt=transcript_excerpt,
    )

    response = claude(
        prompt=prompt,
        system_prompt=persona["system_prompt"],
        model=model,
        timeout=300,
    )

    return response
