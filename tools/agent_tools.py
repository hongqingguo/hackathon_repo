from urllib.parse import urlparse

from langchain_core.tools import tool


@tool
def extract_entity_tool(candidate: dict) -> dict:
    """Extract observed facts, signals, and evidence from a candidate entity."""
    evidence = []
    for fact in candidate["facts"]:
        evidence.append(
            {
                "field": fact["field"],
                "value": fact["value"],
                "source_url": fact["source_url"],
                "snippet": fact["snippet"],
                "kind": "observed",
            }
        )

    for signal in candidate["signals"]:
        evidence.append(
            {
                "field": "pain_point_signal",
                "value": signal["label"],
                "source_url": signal["source_url"],
                "snippet": signal["snippet"],
                "kind": "observed",
            }
        )

    return {
        "entity_name": candidate["name"],
        "entity_type": candidate["entity_type"],
        "canonical_url": candidate["canonical_url"],
        "location": candidate["location"],
        "summary": candidate["summary"],
        "observed_fact_labels": [f"{fact['field']}:{fact['value']}" for fact in candidate["facts"]],
        "signal_labels": [signal["label"] for signal in candidate["signals"]],
        "source_document_count": len(candidate.get("source_documents", [])),
        "source_domains": sorted(
            {
                document.get("domain", "")
                for document in candidate.get("source_documents", [])
                if document.get("domain", "")
            }
        ),
        "evidence": evidence,
    }


@tool
def compare_evidence_tool(
    evidence: list[dict],
    selected_source_urls: list[str],
    fact_match_type: str,
) -> dict:
    """Compare claims across sources and estimate reliability."""
    field_to_value_sources: dict[str, dict[str, set[str]]] = {}
    validation_source_urls: set[str] = set(selected_source_urls)
    validation_domains: set[str] = set()

    for item in evidence:
        field = item["field"]
        value = item["value"].strip().lower()
        source_url = item["source_url"]
        if not value:
            continue
        field_to_value_sources.setdefault(field, {}).setdefault(value, set()).add(source_url)
        if source_url:
            validation_source_urls.add(source_url)
            domain = _normalize_domain(source_url)
            if domain:
                validation_domains.add(domain)

    corroborated_fields: list[str] = []
    conflicting_fields: list[str] = []
    weak_same_domain_support: list[str] = []

    for field, value_sources in field_to_value_sources.items():
        for value, sources in value_sources.items():
            domains = {_normalize_domain(source) for source in sources if _normalize_domain(source)}
            if len(domains) >= 2:
                corroborated_fields.append(f"{field}:{value}")
            elif len(sources) >= 2:
                weak_same_domain_support.append(f"{field}:{value}")
        if field in {"entity_name", "canonical_url", "location", "category", "pricing_model"} and len(value_sources) > 1:
            conflicting_fields.append(field)

    selected_domains = {_normalize_domain(url) for url in selected_source_urls if _normalize_domain(url)}
    if fact_match_type == "observed_exact" and len(selected_domains) >= 2:
        corroborated_fields.append("best_matching_fact")

    corroborated_fields = sorted(set(corroborated_fields))
    conflicting_fields = sorted(set(conflicting_fields))
    weak_same_domain_support = sorted(set(weak_same_domain_support))

    score = 0.35
    score += min(len(corroborated_fields) * 0.18, 0.36)
    score += min(len(validation_domains) * 0.1, 0.3)
    score += min(len(weak_same_domain_support) * 0.03, 0.09)
    score -= min(len(conflicting_fields) * 0.2, 0.4)
    score = round(max(0.0, min(score, 1.0)), 2)

    if conflicting_fields:
        status = "needs_review"
        validation_scope = "cross_domain_conflict" if len(validation_domains) >= 2 else "same_domain_conflict"
        notes = (
            f"Conflicting source evidence was detected for {', '.join(conflicting_fields)}. "
            "A human should review the attached URLs before acting on the result."
        )
        human_review_required = True
        human_review_reason = "Conflicting source evidence detected."
    elif corroborated_fields:
        status = "high" if score >= 0.75 else "medium"
        validation_scope = "cross_domain"
        notes = (
            f"The result is supported by cross-domain agreement on {', '.join(corroborated_fields)}. "
            f"Fact selection remains {fact_match_type}."
        )
        human_review_required = False
        human_review_reason = ""
    elif weak_same_domain_support:
        status = "low"
        validation_scope = "same_domain_only"
        notes = (
            f"Support was found across multiple pages on the same domain for {', '.join(weak_same_domain_support)}, "
            "but true cross-domain corroboration is still missing."
        )
        human_review_required = True
        human_review_reason = "Only same-domain support was found."
    else:
        status = "low"
        validation_scope = "insufficient"
        notes = "The result relies on limited source overlap and lacks cross-domain corroboration."
        human_review_required = True
        human_review_reason = "Insufficient corroboration for confident automation."

    return {
        "validation_status": status,
        "validation_notes": notes,
        "validation_score": score,
        "validation_scope": validation_scope,
        "human_review_required": human_review_required,
        "human_review_reason": human_review_reason,
        "corroborated_fields": corroborated_fields,
        "conflicting_fields": conflicting_fields,
        "validation_source_urls": sorted(validation_domains),
    }


def _normalize_domain(url: str) -> str:
    parsed = urlparse(url)
    hostname = parsed.netloc.lower().strip()
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname
