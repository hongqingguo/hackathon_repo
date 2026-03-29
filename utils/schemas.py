from dataclasses import dataclass
from typing import List


@dataclass
class SearchBrief:
    raw_query: str
    target_type: str
    subject: str
    geography: str
    requested_attribute: str
    investigation_goal: str
    search_queries: List[str]
    search_backend: str


@dataclass
class Evidence:
    field: str
    value: str
    source_url: str
    snippet: str
    kind: str


@dataclass
class SourceDocument:
    url: str
    domain: str
    title: str
    snippet: str
    content: str


@dataclass
class CandidateEntity:
    name: str
    entity_type: str
    canonical_url: str
    location: str
    summary: str
    tags: List[str]
    facts: List[dict]
    signals: List[dict]
    source_documents: List[SourceDocument]


@dataclass
class ExtractedEntity:
    entity_name: str
    entity_type: str
    canonical_url: str
    location: str
    summary: str
    observed_fact_labels: List[str]
    signal_labels: List[str]
    source_document_count: int
    source_domains: List[str]
    evidence: List[Evidence]


@dataclass
class QualifiedEntity(ExtractedEntity):
    fit_label: str
    fit_reason: str


@dataclass
class ReasonedEntity(QualifiedEntity):
    requested_attribute: str
    best_matching_fact: str
    fact_match_type: str
    reasoning_summary: str
    confidence: float
    source_urls: List[str]


@dataclass
class ValidatedEntity(ReasonedEntity):
    validation_status: str
    validation_notes: str
    validation_score: float
    validation_scope: str
    human_review_required: bool
    human_review_reason: str
    corroborated_fields: List[str]
    conflicting_fields: List[str]
    validation_source_urls: List[str]


@dataclass
class InvestigationRecord(ValidatedEntity):
    priority_score: int
    why_relevant: str
    recommended_action: str
