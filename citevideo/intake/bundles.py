"""
Helpers for low-cost topic bundle intake.
"""

from __future__ import annotations

import json
import os
from typing import Any


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _resolve_path(base_dir: str, path: str) -> str:
    if not path:
        return ""
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(base_dir, path))


def _render_json_segments(
    path: str,
    *,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
) -> str:
    segments = _load_json(path)
    if not isinstance(segments, list):
        return json.dumps(segments, ensure_ascii=False)

    lines: list[str] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        start = segment.get("start")
        if start_seconds is not None and isinstance(start, (int, float)) and start < start_seconds:
            continue
        if end_seconds is not None and isinstance(start, (int, float)) and start > end_seconds:
            continue
        text = str(segment.get("text", "")).strip()
        if text:
            lines.append(text)
    return "\n".join(lines).strip()


def _read_source_excerpt(source: dict[str, Any], base_dir: str) -> str:
    inline_excerpt = str(source.get("excerpt_text", "")).strip()
    if inline_excerpt:
        return inline_excerpt

    transcript_path = _resolve_path(base_dir, str(source.get("transcript_path", "")).strip())
    if not transcript_path:
        return ""

    if transcript_path.endswith(".json"):
        return _render_json_segments(
            transcript_path,
            start_seconds=source.get("start_seconds"),
            end_seconds=source.get("end_seconds"),
        )
    return _read_text(transcript_path).strip()


def _build_research_notes(bundle: dict[str, Any], base_dir: str) -> str:
    explicit_notes = str(
        bundle.get("external_research_notes") or bundle.get("research_notes") or ""
    ).strip()
    if explicit_notes:
        return explicit_notes

    sections: list[str] = []
    for source in bundle.get("sources", []):
        title = source.get("title", "Untitled source")
        url = source.get("url", "")
        summary = str(source.get("summary", "")).strip()
        key_points = [str(item).strip() for item in source.get("key_points", []) if str(item).strip()]
        excerpt = _read_source_excerpt(source, base_dir)

        section_lines = [f"Source: {title}"]
        if url:
            section_lines.append(f"URL: {url}")
        if summary:
            section_lines.append(f"Summary: {summary}")
        if key_points:
            section_lines.append("Key points:")
            section_lines.extend(f"- {item}" for item in key_points)
        if excerpt:
            section_lines.append("Excerpt:")
            section_lines.append(excerpt[:4000])
        sections.append("\n".join(section_lines))

    if not sections:
        return ""

    preface = (
        "These notes are a low-cost source bundle compiled from provided creator materials. "
        "Use them to summarize support, caveats, and contradictions. "
        "Do not invent study metadata when the notes do not identify a paper clearly."
    )
    return preface + "\n\n" + "\n\n---\n\n".join(sections)


def load_topic_bundle(bundle_path: str) -> dict[str, Any]:
    resolved_path = os.path.abspath(bundle_path)
    bundle = _load_json(resolved_path)
    base_dir = os.path.dirname(resolved_path)

    normalized_sources = []
    source_sections = []
    for index, source in enumerate(bundle.get("sources", []), 1):
        normalized = dict(source)
        normalized["source_id"] = normalized.get("source_id") or f"bundle-source-{index:03d}"
        normalized["title"] = normalized.get("title") or normalized["source_id"]
        for path_key in ("transcript_path", "provenance"):
            if normalized.get(path_key):
                normalized[path_key] = _resolve_path(base_dir, normalized[path_key])

        excerpt = _read_source_excerpt(normalized, base_dir)
        normalized["excerpt_text"] = excerpt
        normalized_sources.append(normalized)

        if excerpt:
            section = [
                f"Source {index}: {normalized['title']}",
                f"Source ID: {normalized['source_id']}",
            ]
            if normalized.get("summary"):
                section.append(f"Summary: {normalized['summary']}")
            section.append(excerpt)
            source_sections.append("\n".join(section))

    combined_transcript = "\n\n---\n\n".join(source_sections).strip()

    normalized_bundle = {
        **bundle,
        "bundle_path": resolved_path,
        "sources": normalized_sources,
        "external_research_notes": _build_research_notes(bundle, base_dir),
    }
    return {
        "bundle": normalized_bundle,
        "transcript": combined_transcript,
    }
