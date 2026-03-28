"""
Evidence Rating & Synthesis (Phase 1d-1e).

Combines primary research, counter-research, and consensus into
structured per-claim evidence ratings.
"""

import json
import re
from citevideo.llm import claude

RATING_SYSTEM = (
    "You are a scientific evidence evaluator. You rate health claims based on "
    "the quality of supporting evidence. You are honest, precise, and never "
    "overstate the strength of evidence. You respond with ONLY valid JSON."
)

RATING_PROMPT = """You have the following research data for claims from a health YouTube video.

## Original Claims
{claims_json}

## Primary Research Findings
{primary_research}

## Counter-Research (Contradicting/Qualifying Evidence)
{counter_research}

---

For EACH claim, produce a structured evidence rating. Return a JSON object with a "ratings" array:

{{
  "ratings": [
    {{
      "claim_id": "claim_001",
      "claim_text": "...",
      "verification": {{
        "status": "accurate|partially_accurate|misleading|unverifiable|fabricated",
        "paper_found": true/false,
        "paper": {{
          "title": "...",
          "authors": "...",
          "journal": "...",
          "year": 2024,
          "doi": "...",
          "url": "..."
        }},
        "what_study_actually_found": "...",
        "discrepancy_notes": "..."
      }},
      "evidence_rating": {{
        "accuracy_score": 1-5,
        "accuracy_label": "fabricated|major_misrepresentation|partially_accurate|mostly_accurate|fully_accurate",
        "evidence_strength": 1-6,
        "evidence_label": "expert_opinion|in_vitro|animal_model|observational|rct|meta_analysis",
        "extrapolation_risk": "none|low|medium|high",
        "extrapolation_notes": "...",
        "consensus_alignment": "aligned|mixed|contradicted|no_consensus",
        "missing_context": "...",
        "cherry_picking": true/false
      }},
      "recommended_framing": "How this claim should be honestly presented to viewers",
      "key_citations": [
        {{"label": "Smith et al. (2024)", "detail": "Nature Medicine", "doi": "..."}}
      ]
    }}
  ],
  "overall_assessment": "1-2 paragraph summary of the video's scientific credibility",
  "strongest_claims": ["claim_ids of the best-supported claims"],
  "weakest_claims": ["claim_ids of the least-supported claims"],
  "red_flags": ["Major concerns about the video's presentation of science"]
}}

Rating scales:
- accuracy_score: 1=fabricated/no such study, 2=major misrepresentation, 3=partially accurate with significant omissions, 4=mostly accurate with minor issues, 5=fully accurate
- evidence_strength: 1=expert opinion only, 2=in-vitro, 3=animal model, 4=observational/cohort, 5=RCT, 6=systematic review/meta-analysis
- extrapolation_risk: "high" mainly catches mouse-to-human jumps or in-vitro-to-clinical leaps

Be rigorous. If a study is in mice, it's evidence_strength 3 even if the claim is technically accurate about what the mouse study found. If the video presents a mouse study as if it applies to humans without qualification, that's extrapolation_risk "high"."""


def rate_evidence(claims_data: dict, primary_research: dict, counter_research: dict) -> dict:
    """
    Produce structured evidence ratings for all claims.

    Args:
        claims_data: Output from extractor.extract_claims()
        primary_research: Output from researcher.research_claims()
        counter_research: Output from counter_researcher.research_counter_evidence()

    Returns:
        Dict with "ratings" list and summary fields
    """
    # Format inputs for the prompt
    claims_json = json.dumps(claims_data.get("claims", []), indent=2)

    # Concatenate primary research responses (truncate each to keep prompt manageable)
    max_per_cluster = 4000
    primary_texts = []
    for cluster_name, data in primary_research.items():
        if data.get("skipped"):
            continue
        primary_texts.append(f"### Cluster: {cluster_name}")
        raw = data.get("raw_response", data.get("error", "No data"))
        if len(raw) > max_per_cluster:
            raw = raw[:max_per_cluster] + "\n[... truncated for length ...]"
        primary_texts.append(raw)
        primary_texts.append("")
    primary_text = "\n".join(primary_texts)

    # Concatenate counter-research responses
    counter_texts = []
    for cluster_name, data in counter_research.items():
        counter_texts.append(f"### Cluster: {cluster_name}")
        counter_texts.append(data.get("counter_evidence", data.get("error", "No data")))
        counter_texts.append("")
    counter_text = "\n".join(counter_texts) if counter_texts else "No counter-research available."

    prompt = RATING_PROMPT.format(
        claims_json=claims_json,
        primary_research=primary_text,
        counter_research=counter_text,
    )

    # This is a large prompt -- use extended timeout
    response = claude(prompt, system_prompt=RATING_SYSTEM, timeout=600)

    # Parse JSON
    cleaned = response.replace("```json", "").replace("```", "").strip()
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            result = json.loads(match.group())
        else:
            raise RuntimeError(f"Failed to parse evidence ratings as JSON:\n{cleaned[:500]}")

    ratings = result.get("ratings", [])
    print(f"  Rated {len(ratings)} claims")

    # Summary stats
    if ratings:
        avg_accuracy = sum(r.get("evidence_rating", {}).get("accuracy_score", 0) for r in ratings) / len(ratings)
        high_risk = sum(1 for r in ratings if r.get("evidence_rating", {}).get("extrapolation_risk") == "high")
        print(f"  Average accuracy: {avg_accuracy:.1f}/5")
        print(f"  High extrapolation risk: {high_risk}/{len(ratings)}")

    return result
