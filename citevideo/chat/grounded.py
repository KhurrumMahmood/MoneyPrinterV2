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

PACKAGE_QUESTION_PATTERNS = {
    "caveats": re.compile(r"\bcaveat|caveats|limits?|warnings?|uncertaint(?:y|ies)\b", re.I),
    "strongest": re.compile(r"\bstrongest|best[- ]supported|most supported|best evidence\b", re.I),
    "disagreement": re.compile(r"\bdisagree|disagreement|contradict|conflict\b", re.I),
    "guardrails": re.compile(r"\bnot conclude|does not mean|misinterpret|wrong takeaway\b", re.I),
}


def _load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _tokenize(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())


def _score_record(
    query_tokens: list[str],
    record: dict[str, Any],
    package_intent: str | None = None,
) -> int:
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
    if record.get("source_ids"):
        score += 1
    if package_intent == "caveats" and record.get("record_type") in {"summary", "caveat", "uncertainty"}:
        score += 5
    if package_intent == "strongest" and record.get("record_type") in {"strongest", "summary"}:
        score += 5
    if package_intent == "disagreement" and record.get("record_type") in {"uncertainty", "caveat", "summary"}:
        score += 5
    if package_intent == "guardrails" and record.get("record_type") in {"guardrail", "summary", "caveat"}:
        score += 5
    return score


def _detect_package_intent(question: str) -> str | None:
    for intent, pattern in PACKAGE_QUESTION_PATTERNS.items():
        if pattern.search(question):
            return intent
    return None


def _collect_source_ids(dossier: dict[str, Any]) -> list[str]:
    source_ids = [
        source.get("source_id", "")
        for source in dossier.get("source_log", [])
        if source.get("source_id")
    ]
    return list(dict.fromkeys(source_ids))


def _dedupe_lines(lines: list[str], limit: int = 4) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for line in lines:
        normalized = " ".join(line.split())
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
        if len(deduped) >= limit:
            break
    return deduped


def _citation_payload(
    record_id: str,
    source_ids: list[str],
    anchor: str,
    claim_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "record_id": record_id,
        "source_ids": source_ids,
        "claim_ids": claim_ids or [],
        "anchor": anchor,
    }


def _answer_package_level_question(
    run_dir: str,
    package_intent: str,
    dossier: dict[str, Any],
    topic_hub: dict[str, Any],
) -> dict[str, Any] | None:
    source_ids = _collect_source_ids(dossier)
    run_id = os.path.basename(run_dir.rstrip(os.sep))
    audits_dir = os.path.join(run_dir, "package", "audits")
    coverage = _load_json(os.path.join(audits_dir, "coverage.json"), {})
    delivery = _load_json(os.path.join(audits_dir, "delivery.json"), {})
    trust = _load_json(os.path.join(audits_dir, "trust.json"), {})

    if package_intent == "caveats":
        lines = _dedupe_lines(
            [
                "The biggest caveats here are traceability and over-precise effect sizes, not that the whole topic package is directionally wrong.",
                *topic_hub.get("uncertainties", [])[:2],
                *[
                    issue.get("issue", "")
                    for issue in coverage.get("issues", [])
                    if issue.get("severity") == "major"
                ][:2],
                *dossier.get("harms_and_caveats", [])[:2],
            ],
            limit=5,
        )
        if not lines:
            return None
        return {
            "mode": "grounded-explainer",
            "refused": False,
            "confidence": "mixed",
            "answer": "\n\n".join(lines),
            "citations": [
                _citation_payload(
                    f"{run_id}:package-caveats",
                    source_ids,
                    dossier.get("page_id", ""),
                ),
                _citation_payload(
                    f"{run_id}:coverage-audit",
                    source_ids,
                    "audit-coverage",
                ),
            ],
            "topic": {
                "title": dossier.get("title", ""),
                "page_id": dossier.get("page_id", ""),
                "topic_slug": dossier.get("topic_slug", ""),
            },
        }

    if package_intent == "strongest":
        strongest = dossier.get("strongest_evidence", [])[:3]
        if not strongest:
            return None
        lines = [
            "The strongest supported takeaways in this package are the simple meal-structure ideas, not the flashy percentage claims."
        ]
        claim_ids = []
        for card in strongest:
            claim_ids.append(card.get("claim_id", ""))
            lines.append(card.get("recommended_framing") or card.get("claim_text", ""))
        return {
            "mode": "grounded-explainer",
            "refused": False,
            "confidence": strongest[0].get("evidence_label", "mixed"),
            "answer": "\n\n".join(_dedupe_lines(lines, limit=4)),
            "citations": [
                _citation_payload(
                    f"{run_id}:package-strongest",
                    source_ids,
                    dossier.get("page_id", ""),
                    claim_ids=[claim_id for claim_id in claim_ids if claim_id],
                )
            ],
            "topic": {
                "title": dossier.get("title", ""),
                "page_id": dossier.get("page_id", ""),
                "topic_slug": dossier.get("topic_slug", ""),
            },
        }

    if package_intent == "disagreement":
        contradictory = dossier.get("contradictory_evidence", [])[:2]
        lines = []
        claim_ids = []
        if contradictory:
            lines.append("The main disagreements here are explicit contradictions in the evidence base.")
            for card in contradictory:
                claim_ids.append(card.get("claim_id", ""))
                lines.append(card.get("recommended_framing") or card.get("claim_text", ""))
        else:
            lines.append(
                "This package is lighter on direct study-vs-study contradictions than on uncertainty created by weak sourcing and overextended interpretation."
            )
            lines.extend(topic_hub.get("uncertainties", [])[:3])
        lines = _dedupe_lines(lines, limit=4)
        return {
            "mode": "grounded-explainer",
            "refused": False,
            "confidence": "mixed",
            "answer": "\n\n".join(lines),
            "citations": [
                _citation_payload(
                    f"{run_id}:package-disagreement",
                    source_ids,
                    dossier.get("page_id", ""),
                    claim_ids=[claim_id for claim_id in claim_ids if claim_id],
                )
            ],
            "topic": {
                "title": dossier.get("title", ""),
                "page_id": dossier.get("page_id", ""),
                "topic_slug": dossier.get("topic_slug", ""),
            },
        }

    if package_intent == "guardrails":
        lines = _dedupe_lines(
            [
                *dossier.get("what_this_does_not_mean", [])[:3],
                dossier.get("practical_takeaway", ""),
                *[
                    issue.get("issue", "")
                    for issue in delivery.get("issues", [])
                    if issue.get("severity") == "major"
                ][:1],
                *[
                    issue.get("issue", "")
                    for issue in trust.get("issues", [])
                ][:1],
            ],
            limit=5,
        )
        if not lines:
            return None
        return {
            "mode": "grounded-explainer",
            "refused": False,
            "confidence": "mixed",
            "answer": "\n\n".join(lines),
            "citations": [
                _citation_payload(
                    f"{run_id}:package-guardrails",
                    source_ids,
                    dossier.get("page_id", ""),
                )
            ],
            "topic": {
                "title": dossier.get("title", ""),
                "page_id": dossier.get("page_id", ""),
                "topic_slug": dossier.get("topic_slug", ""),
            },
        }

    return None


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
    topic_hub = _load_json(os.path.join(run_dir, "package", "topic_hub_fragment.json"), {})
    package_intent = _detect_package_intent(question)

    package_answer = _answer_package_level_question(run_dir, package_intent, dossier, topic_hub)
    if package_answer:
        return package_answer

    query_tokens = _tokenize(question)
    ranked_records = sorted(
        chat_index.get("records", []),
        key=lambda record: _score_record(query_tokens, record, package_intent),
        reverse=True,
    )
    matches = [
        record
        for record in ranked_records
        if _score_record(query_tokens, record, package_intent) > 0
    ]
    claim_matches = [record for record in matches if record.get("record_type") == "claim"]
    if package_intent:
        package_matches = [record for record in matches if record.get("record_type") != "claim"]
        if package_matches:
            matches = package_matches[:max_records]
        elif claim_matches:
            sourced_claim_matches = [record for record in claim_matches if record.get("source_ids")]
            matches = (sourced_claim_matches or claim_matches)[:max_records]
        else:
            matches = matches[:max_records]
    elif claim_matches:
        sourced_claim_matches = [record for record in claim_matches if record.get("source_ids")]
        matches = (sourced_claim_matches or claim_matches)[:max_records]
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
        if record.get("record_type") == "claim":
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
        else:
            answer_lines.append("\n".join(content_lines[:4] or [record.get("title", "").strip()]))

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
