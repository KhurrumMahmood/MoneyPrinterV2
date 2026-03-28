"""
Topic hub aggregation across multiple TopicEvidencePackage runs.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Any


def _load_json(path: str) -> dict[str, Any] | None:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def aggregate_topic_hubs(workspace_dir: str) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    if not os.path.isdir(workspace_dir):
        return {"topics": []}

    for run_id in sorted(os.listdir(workspace_dir)):
        fragment_path = os.path.join(workspace_dir, run_id, "package", "topic_hub_fragment.json")
        fragment = _load_json(fragment_path)
        if not fragment:
            continue
        topic_slug = fragment.get("topic_slug") or run_id
        grouped[topic_slug].append(fragment)

    topics = []
    for topic_slug, fragments in grouped.items():
        fragments.sort(
            key=lambda item: item.get("last_reviewed_at") or item.get("version") or item.get("topic_id", ""),
            reverse=True,
        )
        newest = fragments[0]
        consensus = sorted(
            {
                item
                for fragment in fragments
                for item in fragment.get("consensus", [])
                if item
            }
        )
        uncertainties = sorted(
            {
                item
                for fragment in fragments
                for item in fragment.get("uncertainties", [])
                if item
            }
        )
        linked_pages = []
        seen_pages: set[tuple[str, str]] = set()
        for fragment in fragments:
            for page in fragment.get("linked_pages", []):
                page_key = (page.get("kind", ""), page.get("page_id", ""))
                if page_key in seen_pages:
                    continue
                seen_pages.add(page_key)
                linked_pages.append(page)

        evidence_updates = []
        for fragment in fragments:
            evidence_updates.extend(fragment.get("evidence_updates", []))
        evidence_updates.sort(
            key=lambda item: item.get("rated_at", ""),
            reverse=True,
        )

        topics.append(
            {
                "topic_slug": topic_slug,
                "title": newest.get("title", topic_slug.replace("-", " ").title()),
                "summary": newest.get("summary", ""),
                "version": newest.get("version", ""),
                "last_reviewed_at": newest.get("last_reviewed_at", ""),
                "runs": [fragment.get("version", "") for fragment in fragments if fragment.get("version")],
                "consensus": consensus,
                "uncertainties": uncertainties,
                "linked_pages": linked_pages,
                "evidence_updates": evidence_updates,
            }
        )

    topics.sort(
        key=lambda item: item.get("last_reviewed_at") or item.get("version") or item.get("title", ""),
        reverse=True,
    )
    return {"topics": topics}


def export_topic_hubs(workspace_dir: str) -> dict[str, str]:
    topic_hubs_dir = os.path.join(workspace_dir, "topic_hubs")
    os.makedirs(topic_hubs_dir, exist_ok=True)

    aggregated = aggregate_topic_hubs(workspace_dir)
    index_path = os.path.join(topic_hubs_dir, "index.json")
    with open(index_path, "w", encoding="utf-8") as handle:
        json.dump(aggregated, handle, indent=2, ensure_ascii=False)

    paths = {"index": index_path}
    for topic in aggregated.get("topics", []):
        topic_path = os.path.join(topic_hubs_dir, f"{topic['topic_slug']}.json")
        with open(topic_path, "w", encoding="utf-8") as handle:
            json.dump(topic, handle, indent=2, ensure_ascii=False)
        paths[topic["topic_slug"]] = topic_path
    return paths
