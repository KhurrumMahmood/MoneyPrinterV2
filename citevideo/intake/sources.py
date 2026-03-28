"""
Helpers to normalize source documents into a shared registry.
"""

from __future__ import annotations

import os
from typing import Any

from citevideo.models import SourceDocument, TopicBrief


def build_topic_brief(run_id: str, title: str = "", topic: str = "", video_url: str = "") -> dict[str, Any]:
    resolved_topic = topic or title or run_id.replace("-", " ")
    return TopicBrief(
        run_id=run_id,
        topic=resolved_topic,
        title=title or resolved_topic,
        video_url=video_url,
    ).to_dict()


def build_source_registry(
    *,
    run_id: str,
    transcript_text: str,
    transcript_path: str,
    video_title: str = "",
    video_url: str = "",
    citations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    sources.append(
        SourceDocument(
            source_id=f"{run_id}:transcript",
            title=video_title or os.path.basename(transcript_path) or "Transcript",
            source_type="transcript",
            provenance=transcript_path,
            trust_tier="input",
            url=video_url,
            summary=f"Primary transcript input ({len(transcript_text.split())} words)",
        ).to_dict()
    )

    for idx, citation in enumerate(citations or [], 1):
        sources.append(
            SourceDocument(
                source_id=f"{run_id}:citation:{idx:03d}",
                title=citation.get("label") or citation.get("title") or f"Citation {idx}",
                source_type="citation",
                provenance="pipeline",
                trust_tier="derived",
                url=citation.get("url", ""),
                summary=citation.get("detail", ""),
                citations=[citation.get("doi", "")] if citation.get("doi") else [],
            ).to_dict()
        )

    return {
        "run_id": run_id,
        "count": len(sources),
        "sources": sources,
    }
