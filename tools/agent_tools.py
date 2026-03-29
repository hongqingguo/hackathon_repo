from langchain_core.tools import tool

from utils.mock_data import MOCK_ENTITIES


@tool
def search_entities_tool(
    target_type: str,
    subject: str,
    geography: str,
    requested_attribute: str,
    investigation_goal: str,
) -> list[dict]:
    """Search candidate entities from the local knowledge source."""
    scored_candidates = []
    for entity in MOCK_ENTITIES:
        score = 0
        haystack = " ".join(
            [
                entity.name,
                entity.entity_type,
                entity.location,
                entity.summary,
                " ".join(entity.tags),
                " ".join(fact["value"] for fact in entity.facts),
                " ".join(signal["label"] for signal in entity.signals),
            ]
        ).lower()

        if entity.entity_type == target_type:
            score += 3
        if subject and subject.lower() in haystack:
            score += 3
        if geography and geography.lower() in entity.location.lower():
            score += 2
        if requested_attribute:
            requested_terms = [term for term in requested_attribute.lower().split() if len(term) > 2]
            score += sum(1 for term in requested_terms if term in haystack)
        if investigation_goal:
            goal_terms = [term for term in investigation_goal.lower().split() if len(term) > 3]
            score += sum(1 for term in goal_terms if term in haystack)

        if score > 0:
            scored_candidates.append((score, entity))

    scored_candidates.sort(key=lambda item: item[0], reverse=True)
    return [item[1].__dict__ for item in scored_candidates[:10]]


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

    for item in evidence:
        field = item["field"]
        value = item["value"].strip().lower()
        source_url = item["source_url"]
        if not value:
            continue
        field_to_value_sources.setdefault(field, {}).setdefault(value, set()).add(source_url)
        if source_url:
            validation_source_urls.add(source_url)

    corroborated_fields: list[str] = []
    conflicting_fields: list[str] = []

    for field, value_sources in field_to_value_sources.items():
        for value, sources in value_sources.items():
            if len(sources) >= 2:
                corroborated_fields.append(f"{field}:{value}")
        if field in {"entity_name", "canonical_url", "location", "category", "pricing_model"} and len(value_sources) > 1:
            conflicting_fields.append(field)

    if fact_match_type == "observed_exact" and selected_source_urls:
        corroborated_fields.append("best_matching_fact")

    corroborated_fields = sorted(set(corroborated_fields))
    conflicting_fields = sorted(set(conflicting_fields))

    score = 0.35
    score += min(len(corroborated_fields) * 0.18, 0.36)
    score += min(len(validation_source_urls) * 0.07, 0.21)
    score -= min(len(conflicting_fields) * 0.2, 0.4)
    score = round(max(0.0, min(score, 1.0)), 2)

    if conflicting_fields:
        status = "needs_review"
        notes = (
            f"Conflicting source evidence was detected for {', '.join(conflicting_fields)}. "
            "A human should review the attached URLs before acting on the result."
        )
    elif corroborated_fields:
        status = "high" if score >= 0.75 else "medium"
        notes = (
            f"The result is supported by cross-source agreement on {', '.join(corroborated_fields)}. "
            f"Fact selection remains {fact_match_type}."
        )
    else:
        status = "low"
        notes = "The result relies on limited source overlap, so the evidence is useful but not strongly corroborated yet."

    return {
        "validation_status": status,
        "validation_notes": notes,
        "validation_score": score,
        "corroborated_fields": corroborated_fields,
        "conflicting_fields": conflicting_fields,
        "validation_source_urls": sorted(validation_source_urls),
    }
