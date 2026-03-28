"""
Low-cost grounded chat utilities for TopicEvidencePackage artifacts.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from typing import Any


REFUSAL_PATTERNS = {
    "individualized diagnosis": re.compile(r"\bdiagnose|what do i have|do i have\b", re.I),
    "treatment planning": re.compile(r"\bwhat should i take|what should i do|treatment plan|dose\b", re.I),
    "emergency advice": re.compile(r"\bemergency|chest pain|can'?t breathe|stroke|heart attack\b", re.I),
    "unsupported supplement recommendations": re.compile(r"\bwhich supplement should i buy|best brand|brand recommendation\b", re.I),
}


def _load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _tokenize(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())


def _score_record(query_tokens: list[str], record: dict[str, Any]) -> int:
    record_tokens = Counter(_tokenize(" ".join(
        [
            record.get("title", ""),
            record.get("content", ""),
            " ".join(record.get("claim_ids", [])),
            " ".join(record.get("source_ids", [])),
        ]
    )))
    score = sum(record_tokens[token] for token in query_tokens)
    if record.get("record_type") == "claim":
        score += 2
    return score


def should_refuse_question(question: str) -> str | None:
    for label, pattern in REFUSAL_PATTERNS.items():
        if pattern.search(question):
            return label
    return None


def answer_grounded_question(run_dir: str, question: str, max_records: int = 3) -> dict[str, Any]:
    refusal_reason = should_refuse_question(question)
    if refusal_reason:
        return {
            "mode": "grounded-explainer",
            "refused": True,
            "reason": refusal_reason,
            "answer": (
                "I can explain the evidence in this topic package, but I can't provide "
                "individualized medical advice, emergency guidance, or brand-level recommendations."
            ),
            "citations": [],
        }

    chat_index = _load_json(os.path.join(run_dir, "package", "chat_index.json"), {"records": []})
    decision_table = _load_json(os.path.join(run_dir, "package", "decision_table.json"), {"rows": []})
    dossier = _load_json(os.path.join(run_dir, "package", "web_dossier.json"), {})

    query_tokens = _tokenize(question)
    ranked_records = sorted(
        chat_index.get("records", []),
        key=lambda record: _score_record(query_tokens, record),
        reverse=True,
    )
    matches = [record for record in ranked_records if _score_record(query_tokens, record) > 0]
    claim_matches = [record for record in matches if record.get("record_type") == "claim"]
    if claim_matches:
        matches = claim_matches[:max_records]
    else:
        matches = matches[:max_records]

    if not matches:
        return {
            "mode": "grounded-explainer",
            "refused": False,
            "confidence": "insufficient",
            "answer": (
                "I couldn't find enough approved material in this topic package to answer that safely. "
                "Try asking about a claim, harm, caveat, or cited source covered in the dossier."
            ),
            "citations": [],
        }

    rows_by_claim = {
        row.get("claim_id"): row
        for row in decision_table.get("rows", [])
        if row.get("claim_id")
    }

    answer_lines = []
    citations = []
    confidences = []

    for record in matches:
        claim_id = next(iter(record.get("claim_ids", [])), "")
        row = rows_by_claim.get(claim_id, {})
        confidence = row.get("certainty") or record.get("confidence") or "unknown"
        confidences.append(confidence)

        content_lines = [line.strip() for line in record.get("content", "").splitlines() if line.strip()]
        lead = content_lines[0] if content_lines else record.get("title", "").strip()
        support = content_lines[1] if len(content_lines) > 1 else ""
        line_parts = [lead]
        if support:
            line_parts.append(f"Evidence summary: {support}")
        harms = row.get("harms", [])
        if harms:
            line_parts.append(f"Caveats: {'; '.join(harms[:2])}.")
        acceptable = row.get("acceptable_phrasing", [])
        if acceptable:
            line_parts.append(f"Safe framing: {acceptable[0]}")
        answer_lines.append(" ".join(part for part in line_parts if part))

        citations.append(
            {
                "record_id": record.get("record_id", ""),
                "source_ids": record.get("source_ids", []),
                "claim_ids": record.get("claim_ids", []),
                "anchor": record.get("drill_down_anchor", ""),
            }
        )

    confidence_order = {"strong": 4, "moderate": 3, "mixed": 2, "weak": 1, "unknown": 0, "insufficient": 0}
    confidence = sorted(confidences, key=lambda label: confidence_order.get(label, 0), reverse=True)[0]

    return {
        "mode": "grounded-explainer",
        "refused": False,
        "confidence": confidence,
        "answer": "\n\n".join(answer_lines),
        "citations": citations,
        "topic": {
            "title": dossier.get("title", ""),
            "page_id": dossier.get("page_id", ""),
            "topic_slug": dossier.get("topic_slug", ""),
        },
    }
