"""
Helpers to normalize source documents into a shared registry.
"""

from __future__ import annotations

import os
from typing import Any

from citevideo.models import SourceDocument, TopicBrief


def build_topic_brief(
    run_id: str,
    title: str = "",
    topic: str = "",
    video_url: str = "",
    description: str = "",
    source_ids: list[str] | None = None,
) -> dict[str, Any]:
    resolved_topic = topic or title or run_id.replace("-", " ")
    return TopicBrief(
        run_id=run_id,
        topic=resolved_topic,
        title=title or resolved_topic,
        description=description,
        source_ids=source_ids or [],
        video_url=video_url,
    ).to_dict()


def build_source_registry(
    *,
    run_id: str,
    transcript_text: str,
    transcript_path: str,
    video_title: str = "",
    video_url: str = "",
    bundle_sources: list[dict[str, Any]] | None = None,
    citations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    for source in bundle_sources or []:
        summary = source.get("summary", "")
        key_points = [str(item).strip() for item in source.get("key_points", []) if str(item).strip()]
        if key_points:
            joined_points = "; ".join(key_points[:4])
            summary = f"{summary} Key points: {joined_points}".strip()

        sources.append(
            SourceDocument(
                source_id=source.get("source_id") or f"{run_id}:source:{len(sources) + 1:03d}",
                title=source.get("title") or "Source",
                source_type=source.get("source_type") or "bundle_source",
                provenance=source.get("provenance")
                or source.get("transcript_path")
                or source.get("bundle_path")
                or "bundle",
                trust_tier=source.get("trust_tier") or "bundle_input",
                url=source.get("url", ""),
                published_at=source.get("published_at", ""),
                summary=summary,
                conflicts=source.get("conflicts", []),
                citations=source.get("citations", []),
            ).to_dict()
        )

    transcript_type = "bundle_transcript" if bundle_sources else "transcript"
    transcript_tier = "derived" if bundle_sources else "input"
    sources.append(
        SourceDocument(
            source_id=f"{run_id}:transcript",
            title=video_title or os.path.basename(transcript_path) or "Transcript",
            source_type=transcript_type,
            provenance=transcript_path,
            trust_tier=transcript_tier,
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
