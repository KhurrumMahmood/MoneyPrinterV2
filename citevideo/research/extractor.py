"""
Claim Extraction (Phase 1a).

Parses a health/medical video transcript and extracts structured claims
that can be researched and verified.
"""

import json
import re
from citevideo.llm import claude

EXTRACTION_SYSTEM = (
    "You are a scientific claim extractor. You read health/medical video transcripts "
    "and identify specific, verifiable factual claims. You distinguish between: "
    "empirical claims (references a study), causal claims (X causes Y), "
    "correlational claims, and anecdotal claims (personal experience). "
    "You always respond with ONLY valid JSON."
)

EXTRACTION_PROMPT = """Analyze this health/medical video transcript and extract all verifiable claims.

<transcript>
{transcript}
</transcript>

For each claim, provide:
- "id": sequential identifier like "claim_001"
- "text": the claim as a self-contained statement (paraphrased to stand alone)
- "category": one of "study_reference", "mechanism_claim", "dosage_recommendation", "food_health_claim", "general_health_claim"
- "quoted_source": if the speaker names a study, institution, or researcher, include it here (otherwise null)
- "topic_cluster": a short slug grouping related claims (e.g., "fasting_autophagy", "polyphenols_autophagy", "olive_oil_benefits", "drink_recipe")
- "claim_type": one of "empirical" (cites a study), "causal" (X causes Y), "correlational" (X associated with Y), "anecdotal" (personal experience)
- "timestamp_approx": rough position in the transcript (e.g., "early", "middle", "late")
- "specificity": "high" (names specific study/numbers), "medium" (general mechanism), "low" (vague assertion)

Rules:
- Extract ALL verifiable claims, not just the obvious ones
- Paraphrase each claim to be self-contained (don't reference "the drink" without saying what it is)
- Include dosage/recipe claims as separate entries
- Skip pure transitions, greetings, and promotional/affiliate pitches
- Group related claims under the same topic_cluster for efficient batch research

Return a JSON object: {{"video_title": "...", "claims": [...]}}"""


def extract_claims(transcript: str, video_title: str = "") -> dict:
    """
    Extract structured claims from a transcript.

    Args:
        transcript: Full video transcript text
        video_title: Optional title for metadata

    Returns:
        Dict with "video_title" and "claims" list
    """
    prompt = EXTRACTION_PROMPT.format(transcript=transcript)
    response = claude(prompt, system_prompt=EXTRACTION_SYSTEM, timeout=120)

    # Parse JSON, stripping any markdown fences
    cleaned = response.replace("```json", "").replace("```", "").strip()

    # Try to find JSON object in the response
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        # Look for JSON object between braces
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            result = json.loads(match.group())
        else:
            raise RuntimeError(f"Failed to parse claim extraction response as JSON:\n{cleaned[:500]}")

    if video_title and not result.get("video_title"):
        result["video_title"] = video_title

    claims = result.get("claims", [])
    print(f"  Extracted {len(claims)} claims across "
          f"{len(set(c.get('topic_cluster', '') for c in claims))} topic clusters")

    return result
