"""
Build and persist canonical TopicEvidencePackage artifacts from pipeline outputs.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from citevideo.intake.sources import build_source_registry, build_topic_brief
from citevideo.models import ChatIndexRecord, DossierPage, TopicHubEntry

PACKAGE_FILES = {
    "topic_brief": "topic_brief.json",
    "source_registry": "source_registry.json",
    "claims": "claims.json",
    "evidence_graph": "evidence_graph.json",
    "decision_table": "decision_table.json",
    "delivery_manifest": "delivery_manifest.json",
    "web_dossier": "web_dossier.json",
    "topic_hub_fragment": "topic_hub_fragment.json",
    "chat_index": "chat_index.json",
    "corrections": "corrections.json",
}


def _load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: str, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "topic"


def ensure_package_layout(run_dir: str) -> dict[str, str]:
    package_dir = os.path.join(run_dir, "package")
    audits_dir = os.path.join(package_dir, "audits")
    web_dir = os.path.join(run_dir, "web")
    chat_dir = os.path.join(run_dir, "chat")
    for directory in (package_dir, audits_dir, web_dir, chat_dir):
        os.makedirs(directory, exist_ok=True)
    return {
        "package_dir": package_dir,
        "audits_dir": audits_dir,
        "web_dir": web_dir,
        "chat_dir": chat_dir,
        **{
            key: os.path.join(package_dir, filename)
            for key, filename in PACKAGE_FILES.items()
        },
    }


def _collect_citations(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    for rating in evidence.get("ratings", []):
        citations.extend(rating.get("key_citations", []))
    return citations


def _build_evidence_graph(
    claims_data: dict[str, Any],
    evidence: dict[str, Any],
    primary_research: dict[str, Any] | None,
    counter_research: dict[str, Any] | None,
) -> dict[str, Any]:
    ratings_by_claim = {
        rating.get("claim_id"): rating for rating in evidence.get("ratings", [])
    }

    graph_claims = []
    evidence_items = []
    for claim in claims_data.get("claims", []):
        claim_id = claim.get("id")
        rating = ratings_by_claim.get(claim_id, {})
        key_citations = rating.get("key_citations", [])
        evidence_ids = []
        for idx, citation in enumerate(key_citations, 1):
            evidence_id = f"{claim_id}:evidence:{idx:02d}"
            evidence_ids.append(evidence_id)
            evidence_items.append(
                {
                    "evidence_id": evidence_id,
                    "claim_id": claim_id,
                    "citation_label": citation.get("label", ""),
                    "detail": citation.get("detail", ""),
                    "doi": citation.get("doi", ""),
                    "summary": rating.get("verification", {}).get(
                        "what_study_actually_found", ""
                    ),
                    "limitations": [
                        rating.get("verification", {}).get("discrepancy_notes", ""),
                        rating.get("evidence_rating", {}).get("missing_context", ""),
                    ],
                }
            )

        graph_claims.append(
            {
                **claim,
                "evidence_ids": evidence_ids,
                "verification": rating.get("verification", {}),
                "evidence_rating": rating.get("evidence_rating", {}),
                "recommended_framing": rating.get("recommended_framing", ""),
                "guideline_alignment": rating.get("evidence_rating", {}).get(
                    "consensus_alignment", ""
                ),
            }
        )

    return {
        "claims": graph_claims,
        "evidence_items": evidence_items,
        "primary_research_clusters": sorted((primary_research or {}).keys()),
        "counter_research_clusters": sorted((counter_research or {}).keys()),
    }


def _build_decision_table(evidence_graph: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for claim in evidence_graph.get("claims", []):
        rating = claim.get("evidence_rating", {})
        verification = claim.get("verification", {})
        benefits = []
        harms = []
        framing = claim.get("recommended_framing", "")
        if framing:
            benefits.append(framing)
        discrepancy = verification.get("discrepancy_notes", "")
        if discrepancy:
            harms.append(discrepancy)
        missing_context = rating.get("missing_context", "")
        if missing_context:
            harms.append(missing_context)

        rows.append(
            {
                "claim_id": claim.get("id"),
                "claim_text": claim.get("text", ""),
                "certainty": rating.get("evidence_label", "unknown"),
                "benefits": benefits,
                "harms": harms,
                "applicability": rating.get("extrapolation_notes", ""),
                "conflicts": [],
                "acceptable_phrasing": [framing] if framing else [],
                "disallowed_phrasing": [discrepancy] if discrepancy else [],
                "guideline_alignment": claim.get("guideline_alignment", ""),
                "evidence_ids": claim.get("evidence_ids", []),
                "evidence_status": verification.get("status", "unverifiable"),
            }
        )
    return {"rows": rows}


def _build_corrections(factcheck_report: dict[str, Any] | None) -> dict[str, Any]:
    factcheck_report = factcheck_report or {}
    corrections = []
    for issue in factcheck_report.get("issues_found", []):
        corrections.append(
            {
                "kind": "issue",
                "scene_id": issue.get("scene_id", ""),
                "severity": issue.get("severity", ""),
                "summary": issue.get("issue", ""),
                "fix": issue.get("fix", ""),
            }
        )
    for caveat in factcheck_report.get("missing_caveats", []):
        corrections.append(
            {
                "kind": "caveat",
                "scene_id": caveat.get("scene_id", ""),
                "claim_id": caveat.get("claim_id", ""),
                "summary": caveat.get("needed_caveat", ""),
                "fix": caveat.get("suggested_insertion", ""),
            }
        )
    return {
        "count": len(corrections),
        "items": corrections,
    }


def _build_web_dossier(
    run_id: str,
    topic_brief: dict[str, Any],
    evidence: dict[str, Any],
    source_registry: dict[str, Any],
    corrections: dict[str, Any],
) -> dict[str, Any]:
    topic_slug = _slugify(topic_brief.get("title", topic_brief.get("topic", run_id)))
    last_reviewed_at = evidence.get("rated_at", "")
    claim_cards = []
    contradictory = []
    caveats = []
    for rating in evidence.get("ratings", []):
        evidence_rating = rating.get("evidence_rating", {})
        verification = rating.get("verification", {})
        item = {
            "claim_id": rating.get("claim_id", ""),
            "claim_text": rating.get("claim_text", ""),
            "status": verification.get("status", ""),
            "evidence_label": evidence_rating.get("evidence_label", ""),
            "recommended_framing": rating.get("recommended_framing", ""),
            "citations": rating.get("key_citations", []),
        }
        claim_cards.append(item)
        if evidence_rating.get("consensus_alignment") == "contradicted":
            contradictory.append(item)
        if evidence_rating.get("missing_context"):
            caveats.append(evidence_rating.get("missing_context"))
        if verification.get("discrepancy_notes"):
            caveats.append(verification.get("discrepancy_notes"))

    dossier = DossierPage(
        page_id=f"{run_id}:dossier",
        run_id=run_id,
        topic_slug=topic_slug,
        title=topic_brief.get("title", topic_brief.get("topic", run_id)),
        summary=evidence.get("overall_assessment", ""),
        version=run_id,
        last_reviewed_at=last_reviewed_at,
        claim_cards=claim_cards,
        strongest_evidence=[
            card for card in claim_cards if card["claim_id"] in evidence.get("strongest_claims", [])
        ],
        contradictory_evidence=contradictory,
        harms_and_caveats=caveats,
        what_this_does_not_mean=[
            "This content does not replace individualized medical advice.",
            "Preliminary or animal evidence should not be treated as proven human benefit.",
        ],
        practical_takeaway=(
            "Use the strongest-supported claims first, and treat mixed or preliminary claims "
            "as prompts for discussion rather than self-treatment."
        ),
        source_log=source_registry.get("sources", []),
        corrections=corrections.get("items", []),
    )
    return dossier.to_dict()


def _build_topic_hub_fragment(run_id: str, topic_brief: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    topic_slug = _slugify(topic_brief.get("title", topic_brief.get("topic", run_id)))
    entry = TopicHubEntry(
        topic_id=f"{run_id}:topic",
        topic_slug=topic_slug,
        title=topic_brief.get("title", topic_brief.get("topic", run_id)),
        summary=evidence.get("overall_assessment", ""),
        version=run_id,
        last_reviewed_at=evidence.get("rated_at", ""),
        consensus=[
            f"Strongest supported claim: {claim_id}"
            for claim_id in evidence.get("strongest_claims", [])
        ],
        uncertainties=evidence.get("red_flags", []),
        linked_pages=[
            {
                "kind": "dossier",
                "page_id": f"{run_id}:dossier",
                "title": topic_brief.get("title", ""),
            }
        ],
        evidence_updates=[
            {
                "run_id": run_id,
                "rated_at": evidence.get("rated_at", ""),
            }
        ],
    )
    return entry.to_dict()


def _build_chat_index(
    run_id: str,
    evidence_graph: dict[str, Any],
    dossier: dict[str, Any],
    topic_hub: dict[str, Any],
) -> dict[str, Any]:
    records = []
    for claim in evidence_graph.get("claims", []):
        records.append(
            ChatIndexRecord(
                record_id=f"{run_id}:{claim.get('id', 'claim')}",
                record_type="claim",
                title=claim.get("text", "")[:120],
                content="\n".join(
                    [
                        claim.get("text", ""),
                        claim.get("recommended_framing", ""),
                        claim.get("verification", {}).get("what_study_actually_found", ""),
                    ]
                ).strip(),
                source_ids=claim.get("evidence_ids", []),
                claim_ids=[claim.get("id", "")],
                confidence=claim.get("evidence_rating", {}).get("evidence_label", ""),
                drill_down_anchor=f"claim-{claim.get('id', '')}",
            ).to_dict()
        )
    topic_source_ids = [
        source.get("source_id", "")
        for source in dossier.get("source_log", [])
        if source.get("source_id")
    ]
    records.append(
        ChatIndexRecord(
            record_id=f"{run_id}:dossier-summary",
            record_type="summary",
            title=dossier.get("title", ""),
            content=dossier.get("summary", ""),
            source_ids=topic_source_ids,
            confidence="mixed",
            drill_down_anchor=dossier.get("page_id", ""),
        ).to_dict()
    )
    if dossier.get("strongest_evidence"):
        records.append(
            ChatIndexRecord(
                record_id=f"{run_id}:strongest",
                record_type="strongest",
                title="Strongest supported takeaways",
                content="\n".join(
                    ["Strongest supported takeaways:"]
                    + [
                        item.get("recommended_framing") or item.get("claim_text", "")
                        for item in dossier.get("strongest_evidence", [])[:4]
                    ]
                ),
                source_ids=topic_source_ids,
                claim_ids=[
                    item.get("claim_id", "")
                    for item in dossier.get("strongest_evidence", [])[:4]
                    if item.get("claim_id")
                ],
                confidence="moderate",
                drill_down_anchor=dossier.get("page_id", ""),
            ).to_dict()
        )
    caveat_lines = dossier.get("harms_and_caveats", [])[:4] + topic_hub.get("uncertainties", [])[:3]
    if caveat_lines:
        records.append(
            ChatIndexRecord(
                record_id=f"{run_id}:caveats",
                record_type="caveat",
                title="Biggest caveats and limits",
                content="\n".join(["Biggest caveats and limits:"] + caveat_lines[:6]),
                source_ids=topic_source_ids,
                confidence="mixed",
                drill_down_anchor=dossier.get("page_id", ""),
            ).to_dict()
        )
    if dossier.get("what_this_does_not_mean"):
        records.append(
            ChatIndexRecord(
                record_id=f"{run_id}:guardrails",
                record_type="guardrail",
                title="What this package does not mean",
                content="\n".join(
                    ["What this package does not mean:"]
                    + dossier.get("what_this_does_not_mean", [])[:3]
                    + ([f"Practical takeaway: {dossier.get('practical_takeaway', '')}"] if dossier.get("practical_takeaway") else [])
                ),
                source_ids=topic_source_ids,
                confidence="mixed",
                drill_down_anchor=dossier.get("page_id", ""),
            ).to_dict()
        )
    return {
        "run_id": run_id,
        "count": len(records),
        "records": records,
        "policy": {
            "mode": "grounded-explainer",
            "refuse": [
                "individualized diagnosis",
                "treatment planning",
                "emergency advice",
                "unsupported supplement recommendations",
            ],
        },
    }


def build_package_artifacts(run_dir: str) -> dict[str, str]:
    paths = ensure_package_layout(run_dir)
    run_id = os.path.basename(run_dir)

    transcript_path = os.path.join(run_dir, "transcript.txt")
    transcript_text = ""
    if os.path.exists(transcript_path):
        with open(transcript_path, "r", encoding="utf-8") as handle:
            transcript_text = handle.read()

    claims_data = _load_json(os.path.join(run_dir, "claims.json"), {"claims": []}) or {"claims": []}
    evidence = _load_json(os.path.join(run_dir, "evidence.json"), {"ratings": []}) or {"ratings": []}
    primary_research = _load_json(os.path.join(run_dir, "research_raw.json"), {}) or {}
    counter_research = _load_json(os.path.join(run_dir, "counter_research.json"), {}) or {}
    source_bundle = _load_json(os.path.join(run_dir, "source_bundle.json"), {}) or {}
    delivery_manifest = _load_json(os.path.join(paths["package_dir"], PACKAGE_FILES["delivery_manifest"]), {}) or {}
    factcheck = _load_json(os.path.join(run_dir, "production", "factcheck_report.json"), {}) or {}

    bundle_sources = source_bundle.get("sources", [])
    topic_title = (
        claims_data.get("video_title")
        or source_bundle.get("title")
        or evidence.get("video_title", "")
    )
    topic_value = source_bundle.get("topic") or topic_title or run_id.replace("-", " ")
    topic_description = source_bundle.get("description", "")
    topic_video_url = claims_data.get("video_url", "") or source_bundle.get("video_url", "")
    topic_source_ids = [
        source.get("source_id", "")
        for source in bundle_sources
        if source.get("source_id")
    ]

    topic_brief = build_topic_brief(
        run_id=run_id,
        title=topic_title,
        topic=topic_value,
        video_url=topic_video_url,
        description=topic_description,
        source_ids=topic_source_ids,
    )
    source_registry = build_source_registry(
        run_id=run_id,
        transcript_text=transcript_text,
        transcript_path=transcript_path,
        video_title=topic_brief.get("title", ""),
        video_url=topic_brief.get("video_url", ""),
        bundle_sources=bundle_sources,
        citations=_collect_citations(evidence),
    )
    evidence_graph = _build_evidence_graph(claims_data, evidence, primary_research, counter_research)
    decision_table = _build_decision_table(evidence_graph)
    corrections = _build_corrections(factcheck)
    web_dossier = _build_web_dossier(run_id, topic_brief, evidence, source_registry, corrections)
    topic_hub = _build_topic_hub_fragment(run_id, topic_brief, evidence)
    chat_index = _build_chat_index(run_id, evidence_graph, web_dossier, topic_hub)
    package_claims = {
        **claims_data,
        "claims": evidence_graph.get("claims", []),
    }

    payloads = {
        "topic_brief": topic_brief,
        "source_registry": source_registry,
        "claims": package_claims,
        "evidence_graph": evidence_graph,
        "decision_table": decision_table,
        "delivery_manifest": delivery_manifest,
        "web_dossier": web_dossier,
        "topic_hub_fragment": topic_hub,
        "chat_index": chat_index,
        "corrections": corrections,
    }
    for key, payload in payloads.items():
        _write_json(paths[key], payload)

    _write_json(os.path.join(paths["web_dir"], "dossier.json"), web_dossier)
    _write_json(os.path.join(paths["web_dir"], "topic_hub.json"), topic_hub)
    _write_json(os.path.join(paths["chat_dir"], "chat_index.json"), chat_index)

    return paths
