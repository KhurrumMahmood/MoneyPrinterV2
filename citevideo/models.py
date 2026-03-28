"""
Canonical data models for the CiteVideo evidence + delivery pipeline.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from typing import Any


def _clean(value: Any) -> Any:
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, dict):
        return {
            key: _clean(item)
            for key, item in value.items()
            if item is not None and item != "" and item != [] and item != {}
        }
    if isinstance(value, list):
        return [_clean(item) for item in value if item is not None and item != ""]
    return value


@dataclass
class TopicBrief:
    run_id: str
    topic: str
    title: str = ""
    description: str = ""
    source_ids: list[str] = field(default_factory=list)
    video_url: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return _clean(self)


@dataclass
class SourceDocument:
    source_id: str
    title: str
    source_type: str
    provenance: str
    trust_tier: str
    url: str = ""
    published_at: str = ""
    summary: str = ""
    conflicts: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _clean(self)


@dataclass
class ClaimRecord:
    claim_id: str
    text: str
    category: str = ""
    claim_type: str = ""
    topic_cluster: str = ""
    quoted_source: str = ""
    timestamp_approx: str = ""
    specificity: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    guideline_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _clean(self)


@dataclass
class EvidenceItem:
    evidence_id: str
    claim_id: str
    source_id: str
    citation_label: str
    study_type: str = ""
    population: str = ""
    outcome: str = ""
    summary: str = ""
    contradictions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    human_relevance: str = ""
    direct_quote: str = ""
    url: str = ""
    doi: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _clean(self)


@dataclass
class GuidelinePosition:
    guideline_id: str
    claim_id: str
    organization: str
    stance: str
    summary: str = ""
    url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _clean(self)


@dataclass
class BenefitHarmAssessment:
    claim_id: str
    benefits: list[str] = field(default_factory=list)
    harms: list[str] = field(default_factory=list)
    applicability: str = ""
    conflicts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _clean(self)


@dataclass
class ConfidenceRating:
    claim_id: str
    certainty: str
    evidence_strength: str
    acceptable_phrasing: list[str] = field(default_factory=list)
    disallowed_phrasing: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _clean(self)


@dataclass
class DecisionTable:
    claim_id: str
    claim_text: str
    certainty: str
    benefits: list[str] = field(default_factory=list)
    harms: list[str] = field(default_factory=list)
    applicability: str = ""
    conflicts: list[str] = field(default_factory=list)
    acceptable_phrasing: list[str] = field(default_factory=list)
    disallowed_phrasing: list[str] = field(default_factory=list)
    guideline_alignment: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    evidence_status: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _clean(self)


@dataclass
class SceneBlueprint:
    scene_id: str
    title: str
    narrative_goal: str
    claim_ids: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    evidence_level: str = ""
    benefit_harm_mode: str = "benefit"
    visual_type: str = "study_card"
    dossier_anchor_id: str = ""
    cta_target: str = ""
    safety_flags: list[str] = field(default_factory=list)
    allowed_out_of_context: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _clean(self)


@dataclass
class ShortBlueprint:
    short_id: str
    title: str
    claim_id: str
    evidence_id: str = ""
    evidence_level: str = ""
    dossier_anchor_id: str = ""
    cta_target: str = ""
    caution: str = ""
    allowed_out_of_context: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _clean(self)


@dataclass
class DossierPage:
    page_id: str
    run_id: str
    topic_slug: str
    title: str
    summary: str
    version: str = ""
    last_reviewed_at: str = ""
    claim_cards: list[dict[str, Any]] = field(default_factory=list)
    strongest_evidence: list[dict[str, Any]] = field(default_factory=list)
    contradictory_evidence: list[dict[str, Any]] = field(default_factory=list)
    harms_and_caveats: list[str] = field(default_factory=list)
    what_this_does_not_mean: list[str] = field(default_factory=list)
    practical_takeaway: str = ""
    source_log: list[dict[str, Any]] = field(default_factory=list)
    corrections: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _clean(self)


@dataclass
class TopicHubEntry:
    topic_id: str
    topic_slug: str
    title: str
    summary: str
    version: str = ""
    last_reviewed_at: str = ""
    consensus: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    linked_pages: list[dict[str, Any]] = field(default_factory=list)
    evidence_updates: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _clean(self)


@dataclass
class ChatIndexRecord:
    record_id: str
    record_type: str
    title: str
    content: str
    source_ids: list[str] = field(default_factory=list)
    claim_ids: list[str] = field(default_factory=list)
    confidence: str = ""
    drill_down_anchor: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _clean(self)


def clean_dict(value: Any) -> Any:
    return _clean(value)
