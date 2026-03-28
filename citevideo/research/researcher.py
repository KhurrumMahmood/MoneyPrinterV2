"""
Perplexity Deep Research (Phase 1b).

Researches extracted claims using perplexity/sonar-deep-research via OpenRouter.
Groups claims by topic cluster for efficient batching.
"""

import json
import time
from collections import defaultdict
from citevideo.backends.factory import get_research_backend
from citevideo.config import allow_openrouter_research
from citevideo.llm import openrouter_chat
from citevideo.config import get_openrouter_research_model

RESEARCH_QUERY_TEMPLATE = """I am fact-checking health claims from a YouTube video. For each claim below, I need rigorous scientific verification.

For EACH claim, provide:

1. **PAPER FOUND?** Did you find the actual study referenced? If yes, provide the full citation:
   - Authors (first author et al. is fine)
   - Title
   - Journal
   - Year
   - DOI (if available)
   - PubMed ID (if available)

2. **WHAT THE STUDY ACTUALLY FOUND**: Quote or closely paraphrase the actual findings. Be specific about effect sizes, confidence intervals, and statistical significance where available.

3. **STUDY DESIGN**: What type of study was this?
   - Systematic review / meta-analysis
   - Randomized controlled trial (RCT)
   - Observational / cohort study
   - Animal model (specify species)
   - In-vitro / cell culture
   - Case study / report
   - Expert opinion / review (non-systematic)
   Note the sample size and population studied.

4. **ACCURACY CHECK**: Does the claim accurately represent the study's findings? Be specific about any discrepancies, exaggerations, or missing context.

5. **LIMITATIONS**: What limitations did the study authors themselves note? What additional limitations are important?

6. **CONTRADICTING EVIDENCE**: Are there studies that found different or opposing results?

---

CLAIMS TO VERIFY:

{claims_text}

---

Be thorough and precise. If a study cannot be found, say so clearly. If the claim misrepresents the research, explain exactly how. Include DOIs and URLs where possible."""


def _group_by_cluster(claims: list) -> dict:
    """Group claims by their topic_cluster field."""
    clusters = defaultdict(list)
    for claim in claims:
        cluster = claim.get("topic_cluster", "uncategorized")
        clusters[cluster].append(claim)
    return dict(clusters)


def _format_claims_for_query(claims: list) -> str:
    """Format a list of claims into text for the research query."""
    lines = []
    for i, claim in enumerate(claims, 1):
        source = claim.get("quoted_source", "No specific source cited")
        lines.append(f"Claim {i} (ID: {claim['id']}): {claim['text']}")
        lines.append(f"  Attributed source: {source}")
        lines.append(f"  Claim type: {claim.get('claim_type', 'unknown')}")
        lines.append("")
    return "\n".join(lines)


def research_claims(claims_data: dict, save_callback=None) -> dict:
    """
    Research all claims using Perplexity deep research.

    Groups claims by topic_cluster and sends one API call per cluster.
    Calls save_callback(results_so_far) after each cluster for crash safety.

    Args:
        claims_data: The output from extractor.extract_claims()
        save_callback: Optional function(dict) called after each cluster

    Returns:
        Dict mapping cluster_name -> research result
    """
    claims = claims_data.get("claims", [])
    model = get_openrouter_research_model()
    clusters = _group_by_cluster(claims)

    if not allow_openrouter_research():
        print("  OpenRouter research disabled; using low-cost backend mode")
        notes = claims_data.get("external_research_notes", "")
        if not notes:
            return {
                cluster_name: {
                    "cluster": cluster_name,
                    "claims": [c["id"] for c in cluster_claims],
                    "skipped": True,
                    "reason": (
                        "OpenRouter research disabled and no external_research_notes provided. "
                        "Provide a research bundle or enable CITEVIDEO_ENABLE_OPENROUTER_RESEARCH."
                    ),
                }
                for cluster_name, cluster_claims in clusters.items()
            }

        backend = get_research_backend()
        results = {}
        for i, (cluster_name, cluster_claims) in enumerate(clusters.items(), 1):
            claims_text = _format_claims_for_query(cluster_claims)
            prompt = (
                "Use the supplied research notes to summarize support, limitations, and "
                "contradictions for the claims below. Do not invent papers not present in the notes.\n\n"
                f"## Research Notes\n{notes}\n\n## Claims\n{claims_text}"
            )
            try:
                content = backend.run(
                    prompt,
                    label=f"research:{cluster_name}",
                    timeout=300,
                )
                results[cluster_name] = {
                    "cluster": cluster_name,
                    "claims": [c["id"] for c in cluster_claims],
                    "raw_response": content,
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
        # Skip anecdotal-only clusters
        if all(c.get("claim_type") == "anecdotal" for c in cluster_claims):
            print(f"  [{i}/{total}] Skipping anecdotal cluster: {cluster_name}")
            results[cluster_name] = {
                "cluster": cluster_name,
                "skipped": True,
                "reason": "All claims are anecdotal",
                "claims": [c["id"] for c in cluster_claims],
            }
            continue

        print(f"  [{i}/{total}] Researching cluster: {cluster_name} "
              f"({len(cluster_claims)} claims)...")

        claims_text = _format_claims_for_query(cluster_claims)
        query = RESEARCH_QUERY_TEMPLATE.format(claims_text=claims_text)

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

            # Extract any citations from the response metadata
            citations = []
            for choice in choices:
                msg = choice.get("message", {})
                if "citations" in msg:
                    citations = msg["citations"]

            elapsed = time.time() - start_time

            results[cluster_name] = {
                "cluster": cluster_name,
                "claims": [c["id"] for c in cluster_claims],
                "raw_response": content,
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

        # Save after each cluster for crash safety
        if save_callback:
            save_callback(results)

        # Brief pause between clusters to avoid rate limiting
        if i < total:
            time.sleep(2)

    return results
