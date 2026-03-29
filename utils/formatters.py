import csv
import json
from pathlib import Path
from typing import Iterable

from utils.schemas import InvestigationRecord, SearchBrief


def write_csv(path: Path, leads: Iterable[InvestigationRecord], brief: SearchBrief) -> None:
    fieldnames = [
        "entity_name",
        "entity_type",
        "canonical_url",
        "location",
        "search_backend",
        "requested_attribute",
        "best_matching_fact",
        "fact_match_type",
        "fit_label",
        "fit_reason",
        "signal_labels",
        "source_document_count",
        "source_domains",
        "reasoning_summary",
        "confidence",
        "validation_status",
        "validation_notes",
        "validation_score",
        "validation_scope",
        "human_review_required",
        "human_review_reason",
        "corroborated_fields",
        "conflicting_fields",
        "validation_sources",
        "priority_score",
        "why_relevant",
        "recommended_action",
        "source_urls",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for lead in leads:
            writer.writerow(
                {
                    "entity_name": lead.entity_name,
                    "entity_type": lead.entity_type,
                    "canonical_url": lead.canonical_url,
                    "location": lead.location,
                    "search_backend": brief.search_backend,
                    "requested_attribute": lead.requested_attribute,
                    "best_matching_fact": lead.best_matching_fact,
                    "fact_match_type": lead.fact_match_type,
                    "fit_label": lead.fit_label,
                    "fit_reason": lead.fit_reason,
                    "signal_labels": "; ".join(lead.signal_labels),
                    "source_document_count": lead.source_document_count,
                    "source_domains": "; ".join(lead.source_domains),
                    "reasoning_summary": lead.reasoning_summary,
                    "confidence": lead.confidence,
                    "validation_status": lead.validation_status,
                    "validation_notes": lead.validation_notes,
                    "validation_score": lead.validation_score,
                    "validation_scope": lead.validation_scope,
                    "human_review_required": lead.human_review_required,
                    "human_review_reason": lead.human_review_reason,
                    "corroborated_fields": "; ".join(lead.corroborated_fields),
                    "conflicting_fields": "; ".join(lead.conflicting_fields),
                    "validation_sources": "; ".join(lead.validation_source_urls),
                    "priority_score": lead.priority_score,
                    "why_relevant": lead.why_relevant,
                    "recommended_action": lead.recommended_action,
                    "source_urls": "; ".join(lead.source_urls),
                }
            )


def write_summary(path: Path, leads: list[InvestigationRecord], brief: SearchBrief) -> None:
    top_leads = leads[:5]
    common_signals = _most_common_signals(leads)

    lines = [
        "# Summary",
        "",
        "## Investigation Request",
        "",
        f"- Query: {brief.raw_query}",
        f"- Target type: {brief.target_type}",
        f"- Subject: {brief.subject or 'not specified'}",
        f"- Geography: {brief.geography or 'not specified'}",
        f"- Requested attribute: {brief.requested_attribute or 'not specified'}",
        f"- Investigation goal: {brief.investigation_goal}",
        f"- Search backend: {brief.search_backend}",
        "",
        "## Results",
        "",
        f"- Results found: {len(leads)}",
        f"- Common signals: {', '.join(common_signals) if common_signals else 'none'}",
        "",
        "## Top 5 Ranked Findings",
        "",
    ]

    for lead in top_leads:
        lines.extend(
            [
                f"### {lead.entity_name} ({lead.priority_score})",
                f"- Entity type: {lead.entity_type}",
                f"- Source documents: {lead.source_document_count}",
                f"- Source domains: {', '.join(lead.source_domains) if lead.source_domains else 'none'}",
                f"- Best matching fact: {lead.best_matching_fact} [{lead.fact_match_type}]",
                f"- Why relevant: {lead.why_relevant}",
                f"- Reasoning: {lead.reasoning_summary}",
                f"- Reliability: {lead.validation_status} ({lead.validation_score})",
                f"- Validation scope: {lead.validation_scope}",
                f"- Validation notes: {lead.validation_notes}",
                f"- Human review required: {lead.human_review_required}",
                f"- Human review reason: {lead.human_review_reason or 'none'}",
                f"- Validation sources: {', '.join(lead.validation_source_urls)}",
                f"- Evidence URLs: {', '.join(lead.source_urls)}",
                "",
            ]
        )

    lines.extend(
        [
            "## Reasoning Notes",
            "",
            "Observed facts and inferred conclusions are kept separate. If an exact requested attribute is missing, the system returns the nearest relevant fact and explains why.",
            "",
            "## Evidence Trail",
            "",
            "Each result keeps source URLs so a reviewer can audit where the recommendation came from. Cross-source validation highlights what is corroborated and what still needs review.",
            "",
            "## Human Review Queue",
            "",
        ]
    )

    review_queue = [lead for lead in leads if lead.human_review_required][:5]
    if review_queue:
        for lead in review_queue:
            lines.extend(
                [
                    f"- {lead.entity_name}: {lead.human_review_reason}",
                ]
            )
    else:
        lines.extend(["- No items currently require manual review."])

    lines.extend(
        [
            "",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def write_json(path: Path, leads: list[InvestigationRecord], brief: SearchBrief) -> None:
    payload = {
        "query": brief.raw_query,
        "target_type": brief.target_type,
        "subject": brief.subject,
        "geography": brief.geography,
        "requested_attribute": brief.requested_attribute,
        "investigation_goal": brief.investigation_goal,
        "search_backend": brief.search_backend,
        "result_count": len(leads),
        "results": [
            {
                "entity_name": lead.entity_name,
                "entity_type": lead.entity_type,
                "canonical_url": lead.canonical_url,
                "location": lead.location,
                "requested_attribute": lead.requested_attribute,
                "best_matching_fact": lead.best_matching_fact,
                "fact_match_type": lead.fact_match_type,
                "fit_label": lead.fit_label,
                "fit_reason": lead.fit_reason,
                "signal_labels": lead.signal_labels,
                "source_document_count": lead.source_document_count,
                "source_domains": lead.source_domains,
                "reasoning_summary": lead.reasoning_summary,
                "confidence": lead.confidence,
                "validation_status": lead.validation_status,
                "validation_notes": lead.validation_notes,
                "validation_score": lead.validation_score,
                "validation_scope": lead.validation_scope,
                "human_review_required": lead.human_review_required,
                "human_review_reason": lead.human_review_reason,
                "corroborated_fields": lead.corroborated_fields,
                "conflicting_fields": lead.conflicting_fields,
                "validation_sources": lead.validation_source_urls,
                "priority_score": lead.priority_score,
                "why_relevant": lead.why_relevant,
                "recommended_action": lead.recommended_action,
                "source_urls": lead.source_urls,
            }
            for lead in leads
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _most_common_signals(leads: list[InvestigationRecord]) -> list[str]:
    counts: dict[str, int] = {}
    for lead in leads:
        for signal in lead.signal_labels:
            counts[signal] = counts.get(signal, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    return [item[0] for item in ranked[:3]]
