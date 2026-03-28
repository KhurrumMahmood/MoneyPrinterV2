"""
Roundtable Orchestrator.

Runs the multi-agent roundtable discussion: 5 personas × N rounds.
Each turn is a stateless Claude CLI call with the full conversation
as context. Saves after every turn for crash recovery.
"""

import os
import json
from datetime import datetime

from citevideo.config import get_roundtable_rounds
from citevideo.roundtable.personas import PERSONAS, TURN_ORDER
from citevideo.roundtable.agent import take_turn
from citevideo.roundtable.synthesizer import synthesize_content_plan
from citevideo.roundtable.compactor import compact_conversation

COMPACT_EVERY_N_ROUNDS = 4  # Compact after rounds 4, 8, etc.


def _build_evidence_summary(evidence: dict) -> str:
    """Condense evidence.json into a readable summary for agents."""
    lines = []
    ratings = evidence.get("ratings", [])

    lines.append(f"## Overall Assessment\n{evidence.get('overall_assessment', 'N/A')}\n")

    strongest = evidence.get("strongest_claims", [])
    if strongest:
        lines.append(f"**Strongest claims**: {', '.join(strongest)}")

    weakest = evidence.get("weakest_claims", [])
    if weakest:
        lines.append(f"**Weakest claims**: {', '.join(weakest)}")

    red_flags = evidence.get("red_flags", [])
    if red_flags:
        lines.append(f"**Red flags**: " + "; ".join(red_flags))

    lines.append("\n## Per-Claim Evidence Ratings\n")

    for r in ratings:
        er = r.get("evidence_rating", {})
        v = r.get("verification", {})
        cid = r.get("claim_id", "?")
        text = r.get("claim_text", "")[:120]

        accuracy = er.get("accuracy_label", "?")
        strength = er.get("evidence_label", "?")
        extrap = er.get("extrapolation_risk", "?")
        consensus = er.get("consensus_alignment", "?")
        score = er.get("accuracy_score", "?")

        lines.append(f"### {cid}: {text}")
        lines.append(f"- **Accuracy**: {score}/5 ({accuracy})")
        lines.append(f"- **Evidence**: {strength} | Extrapolation risk: {extrap}")
        lines.append(f"- **Consensus**: {consensus}")

        if v.get("what_study_actually_found"):
            lines.append(f"- **What study found**: {v['what_study_actually_found'][:200]}")
        if v.get("discrepancy_notes"):
            lines.append(f"- **Discrepancy**: {v['discrepancy_notes'][:200]}")
        if r.get("recommended_framing"):
            lines.append(f"- **Recommended framing**: {r['recommended_framing'][:200]}")

        lines.append("")

    return "\n".join(lines)


def _save_conversation(roundtable_dir: str, conversation: str):
    """Save conversation markdown."""
    path = os.path.join(roundtable_dir, "conversation.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(conversation)


def _save_control(roundtable_dir: str, control: dict):
    """Save control state JSON."""
    path = os.path.join(roundtable_dir, "control.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(control, f, indent=2)


def _load_control(roundtable_dir: str) -> dict:
    """Load control state if resuming."""
    path = os.path.join(roundtable_dir, "control.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None


def run_roundtable(run_dir: str, transcript: str, evidence: dict) -> dict:
    """
    Run the full multi-agent roundtable discussion.

    Args:
        run_dir: Path to the run directory
        transcript: Original video transcript
        evidence: Parsed evidence.json data

    Returns:
        Content plan dict (output of synthesis)
    """
    roundtable_dir = os.path.join(run_dir, "roundtable")
    os.makedirs(roundtable_dir, exist_ok=True)

    total_rounds = get_roundtable_rounds()
    evidence_summary = _build_evidence_summary(evidence)

    # Check for resume
    control = _load_control(roundtable_dir)
    if control and control.get("status") == "in_progress":
        conversation = open(os.path.join(roundtable_dir, "conversation.md"), "r").read()
        completed_turns = control.get("completed_turns", 0)
        print(f"  Resuming from turn {completed_turns + 1}")
    else:
        conversation = "# CiteVideo Roundtable Discussion\n\n"
        conversation += f"**Video**: {evidence.get('video_title', 'Unknown')}\n"
        conversation += f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        conversation += f"**Rounds**: {total_rounds}\n"
        conversation += f"**Agents**: {', '.join(PERSONAS[k]['name'] for k in TURN_ORDER)}\n\n"
        conversation += "---\n\n"
        completed_turns = 0
        control = {
            "status": "in_progress",
            "total_rounds": total_rounds,
            "total_turns": total_rounds * len(TURN_ORDER),
            "completed_turns": 0,
            "started_at": datetime.now().isoformat(),
            "split_recommendations": [],
            "compactions": [],
        }
        _save_control(roundtable_dir, control)

    # Compaction state: agents get compacted_context + recent rounds
    compacted_context = control.get("compacted_context", "")
    last_compacted_round = control.get("last_compacted_round", 0)

    total_turns = total_rounds * len(TURN_ORDER)
    turn_index = completed_turns

    for round_num in range(1, total_rounds + 1):
        # Compaction check: at start of a new round boundary
        if (round_num > 1
            and round_num % COMPACT_EVERY_N_ROUNDS == 1
            and round_num - 1 > last_compacted_round
            and len(conversation) > 40000):  # Only compact if conversation is large enough

            compact_end = round_num - 1
            compact_start = last_compacted_round + 1
            print(f"\n  === Compacting rounds {compact_start}-{compact_end} ===")

            summary_dict, summary_text = compact_conversation(
                conversation=conversation,
                start_round=compact_start,
                end_round=compact_end,
                previous_summary=compacted_context,
            )

            # Save compaction artifact
            compact_path = os.path.join(
                roundtable_dir, f"compaction_r{compact_start}_{compact_end}.json"
            )
            with open(compact_path, "w", encoding="utf-8") as f:
                json.dump(summary_dict, f, indent=2, ensure_ascii=False)

            # Update state: keep only last 2 rounds of full conversation
            compacted_context = summary_text
            last_compacted_round = compact_end

            # Trim conversation to recent rounds only
            # Find the marker for the start of recent rounds
            recent_marker = f"## "  # All agent turns start with ##
            recent_rounds_start = round_num - 2  # Keep last 2 rounds
            marker_text = f"— Round {recent_rounds_start}"
            marker_pos = conversation.find(marker_text)
            if marker_pos > 0:
                # Find the ## before this marker
                line_start = conversation.rfind("\n## ", 0, marker_pos)
                if line_start > 0:
                    conversation = conversation[line_start:]

            control["compacted_context"] = compacted_context
            control["last_compacted_round"] = last_compacted_round
            control["compactions"].append({
                "rounds": f"{compact_start}-{compact_end}",
                "timestamp": datetime.now().isoformat(),
                "original_size": len(conversation),
            })

            print(f"  Compaction done. Context: {len(compacted_context)} chars, "
                  f"Recent convo: {len(conversation)} chars")

        for persona_key in TURN_ORDER:
            turn_index_for_round = (round_num - 1) * len(TURN_ORDER) + TURN_ORDER.index(persona_key)
            if turn_index_for_round < completed_turns:
                continue

            persona = PERSONAS[persona_key]
            turn_label = f"Round {round_num}, Turn {TURN_ORDER.index(persona_key) + 1}"
            global_turn = turn_index_for_round + 1

            print(f"  [{global_turn}/{total_turns}] {persona['emoji']} {persona['name']} "
                  f"({turn_label})...")

            # Build context: compacted summary + recent conversation
            agent_context = ""
            if compacted_context:
                agent_context = compacted_context + "\n\n---\n\n## Recent Discussion\n\n"
            agent_context += conversation

            response = take_turn(
                persona_key=persona_key,
                conversation_so_far=agent_context,
                evidence_summary=evidence_summary,
                round_num=round_num,
                total_rounds=total_rounds,
                transcript_excerpt=transcript[:3000],
            )

            # Append to conversation
            conversation += f"## {persona['emoji']} {persona['name']} — Round {round_num}\n\n"
            conversation += response + "\n\n---\n\n"

            # Check for split recommendation
            if "SPLIT_RECOMMENDATION:" in response:
                control["split_recommendations"].append({
                    "agent": persona_key,
                    "round": round_num,
                    "text": response.split("SPLIT_RECOMMENDATION:")[1].strip()[:500],
                })

            # Save after every turn
            completed_turns = turn_index_for_round + 1
            control["completed_turns"] = completed_turns
            control["last_turn"] = {
                "agent": persona_key,
                "round": round_num,
                "timestamp": datetime.now().isoformat(),
            }
            _save_conversation(roundtable_dir, conversation)
            _save_control(roundtable_dir, control)

            print(f"    {len(response)} chars")

    # Mark roundtable complete
    control["status"] = "completed"
    control["completed_at"] = datetime.now().isoformat()
    _save_control(roundtable_dir, control)

    print(f"\n  Roundtable complete: {total_turns} turns across {total_rounds} rounds")
    print(f"  Conversation: {len(conversation)} chars")

    # Synthesize content plan
    print("\n=== Phase 2b: Synthesizing content plan ===")
    content_plan = synthesize_content_plan(roundtable_dir, conversation, evidence)

    return content_plan
