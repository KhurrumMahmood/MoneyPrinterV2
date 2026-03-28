"""
Counter-Research (Phase 1c).

Actively searches for evidence that contradicts or qualifies the claims.
This catches cherry-picking and ensures balanced presentation.
"""

import json
import time
from collections import defaultdict
from citevideo.backends.factory import get_research_backend
from citevideo.config import allow_openrouter_research
from citevideo.llm import openrouter_chat
from citevideo.config import get_openrouter_research_model

COUNTER_QUERY_TEMPLATE = """I am creating a balanced, scientifically honest review of health claims from a YouTube video. I already have the supporting evidence. Now I need you to actively look for the OTHER side -- evidence that contradicts, qualifies, or provides important context that the original claims omit.

For each claim below, search specifically for:

1. **CONTRADICTING STUDIES**: Studies that found different, null, or opposing results
2. **IMPORTANT QUALIFICATIONS**: Context that significantly changes the interpretation (e.g., "only studied in mice", "effect only seen at pharmacological doses", "not replicated")
3. **EXPERT/AUTHORITY POSITIONS**: What do major medical authorities (WHO, NIH, AHA, major medical associations) say about this topic? Do they support or caution against these claims?
4. **RISKS AND SIDE EFFECTS**: Are there known risks associated with the recommended intervention that the original video didn't mention?
5. **CONFLICTS OF INTEREST**: If the original study was funded by an industry with financial interest in the outcome, note that

Be thorough and cite your sources with DOIs where possible.

---

CLAIMS TO EXAMINE:

{claims_text}

---

The goal is NOT to debunk everything, but to ensure we have the complete picture. Some claims may be well-supported -- say so. But if there are important caveats, we need to know them."""


def research_counter_evidence(claims_data: dict, primary_research: dict, save_callback=None) -> dict:
    """
    Search for contradicting/qualifying evidence for major claims.

    Only researches high-value clusters (those with empirical or causal claims).
    Uses the primary research context to ask more targeted questions.

    Args:
        claims_data: Output from extractor.extract_claims()
        primary_research: Output from researcher.research_claims()
        save_callback: Optional function(dict) called after each cluster

    Returns:
        Dict mapping cluster_name -> counter-research result
    """
    claims = claims_data.get("claims", [])
    model = get_openrouter_research_model()

    # Group claims by cluster, but only include clusters worth counter-researching
    clusters = defaultdict(list)
    for claim in claims:
        if claim.get("claim_type") in ("empirical", "causal"):
            cluster = claim.get("topic_cluster", "uncategorized")
            clusters[cluster].append(claim)

    if not clusters:
        print("  No empirical/causal claims to counter-research")
        return {}

    if not allow_openrouter_research():
        print("  OpenRouter counter-research disabled; using low-cost backend mode")
        notes = claims_data.get("external_research_notes", "")
        if not notes:
            return {
                cluster_name: {
                    "cluster": cluster_name,
                    "claims": [c["id"] for c in cluster_claims],
                    "skipped": True,
                    "reason": (
                        "OpenRouter counter-research disabled and no external_research_notes provided."
                    ),
                }
                for cluster_name, cluster_claims in clusters.items()
            }

        backend = get_research_backend()
        results = {}
        for cluster_name, cluster_claims in clusters.items():
            claims_text = "\n".join(f"- {claim['text']}" for claim in cluster_claims)
            prompt = (
                "Using the supplied research notes only, identify contradictions, harms, "
                "or context omitted by the claims below.\n\n"
                f"## Research Notes\n{notes}\n\n## Claims\n{claims_text}"
            )
            try:
                content = backend.run(prompt, label=f"counter:{cluster_name}", timeout=300)
                results[cluster_name] = {
                    "cluster": cluster_name,
                    "claims": [c["id"] for c in cluster_claims],
                    "counter_evidence": content,
                    "citations": [],
                    "model": backend.name,
                    "latency_seconds": 0,
                }
            except Exception as exc:
                results[cluster_name] = {
                    "cluster": cluster_name,
                    "claims": [c["id"] for c in cluster_claims],
                    "error": str(exc),
                    "latency_seconds": 0,
                }
            if save_callback:
                save_callback(results)
        return results

    results = {}
    total = len(clusters)

    for i, (cluster_name, cluster_claims) in enumerate(clusters.items(), 1):
        print(f"  [{i}/{total}] Counter-researching: {cluster_name} "
              f"({len(cluster_claims)} claims)...")

        # Format claims with any primary findings for context
        lines = []
        for j, claim in enumerate(cluster_claims, 1):
            lines.append(f"Claim {j} (ID: {claim['id']}): {claim['text']}")
            lines.append(f"  Attributed source: {claim.get('quoted_source', 'None')}")
            lines.append("")

        claims_text = "\n".join(lines)
        query = COUNTER_QUERY_TEMPLATE.format(claims_text=claims_text)

        start_time = time.time()
        try:
            response = openrouter_chat(
                messages=[{"role": "user", "content": query}],
                model=model,
                timeout=600,
            )

            content = ""
            choices = response.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")

            citations = []
            for choice in choices:
                msg = choice.get("message", {})
                if "citations" in msg:
                    citations = msg["citations"]

            elapsed = time.time() - start_time

            results[cluster_name] = {
                "cluster": cluster_name,
                "claims": [c["id"] for c in cluster_claims],
                "counter_evidence": content,
                "citations": citations,
                "model": model,
                "latency_seconds": round(elapsed, 1),
            }

            print(f"    Done in {elapsed:.0f}s ({len(content)} chars)")

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"    FAILED after {elapsed:.0f}s: {e}")
            results[cluster_name] = {
                "cluster": cluster_name,
                "claims": [c["id"] for c in cluster_claims],
                "error": str(e),
                "latency_seconds": round(elapsed, 1),
            }

        if save_callback:
            save_callback(results)

        if i < total:
            time.sleep(2)

    return results
