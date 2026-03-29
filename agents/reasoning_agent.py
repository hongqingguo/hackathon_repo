from typing import Dict, List, Optional, Tuple

from llm.config import has_openai_config
from llm.reasoner_service import ReasonerLLM
from utils.schemas import Evidence, QualifiedEntity, ReasonedEntity, SearchBrief


class ReasoningAgent:
    ATTRIBUTE_FALLBACKS: Dict[str, List[str]] = {
        "cto": ["VP Engineering", "Head of Engineering", "Director of Engineering", "Head of Platform"],
        "vp engineering": ["Head of Engineering", "Director of Engineering", "Engineering Manager"],
        "head of ai": ["Director of Data Science", "ML Engineering Lead", "Head of Data"],
        "coo": ["Head of Operations", "Director of Operations", "Operations Manager"],
        "pricing": ["pricing_model", "enterprise plan", "contact sales"],
        "security": ["soc 2", "compliance", "security posture"],
        "integrations": ["integration", "api", "connector"],
    }

    def run(self, brief: SearchBrief, lead: QualifiedEntity) -> ReasonedEntity:
        requested_attribute = brief.requested_attribute or "relevant facts"
        llm_result = self._run_llm_reasoner(requested_attribute, lead.evidence)
        if llm_result:
            source_urls = self._source_urls_for_supporting_values(llm_result.supporting_values, lead.evidence)
            if not source_urls:
                source_urls = sorted({item.source_url for item in lead.evidence})
            return ReasonedEntity(
                **lead.__dict__,
                requested_attribute=requested_attribute,
                best_matching_fact=llm_result.best_matching_fact,
                fact_match_type=llm_result.fact_match_type,
                reasoning_summary=llm_result.reasoning_summary,
                confidence=llm_result.confidence,
                source_urls=source_urls,
            )

        direct_match = self._find_direct_match(requested_attribute, lead.evidence)

        if direct_match:
            source_urls = self._source_urls_for_value(direct_match.value, lead.evidence)
            return ReasonedEntity(
                **lead.__dict__,
                requested_attribute=requested_attribute,
                best_matching_fact=f"{direct_match.field}: {direct_match.value}",
                fact_match_type="observed_exact",
                reasoning_summary=(
                    f"Found evidence directly matching '{requested_attribute}' in field '{direct_match.field}'."
                ),
                confidence=0.96,
                source_urls=source_urls,
            )

        fallback_fact, fallback_evidence = self._find_fallback(requested_attribute, lead.evidence)
        if fallback_fact:
            source_urls = sorted({item.source_url for item in fallback_evidence})
            return ReasonedEntity(
                **lead.__dict__,
                requested_attribute=requested_attribute,
                best_matching_fact=f"{fallback_fact.field}: {fallback_fact.value}",
                fact_match_type="inferred_adjacent",
                reasoning_summary=(
                    f"No exact match for '{requested_attribute}' was found. "
                    f"The agent selected '{fallback_fact.field}: {fallback_fact.value}' as the closest relevant fact."
                ),
                confidence=0.78,
                source_urls=source_urls,
            )

        fallback_fact = lead.evidence[0] if lead.evidence else None
        source_urls = sorted({item.source_url for item in lead.evidence})
        best_matching_fact = (
            f"{fallback_fact.field}: {fallback_fact.value}" if fallback_fact else "unknown"
        )
        return ReasonedEntity(
            **lead.__dict__,
            requested_attribute=requested_attribute,
            best_matching_fact=best_matching_fact,
            fact_match_type="inferred_weak",
            reasoning_summary=(
                f"No exact match for '{requested_attribute}' was found, so the agent returned the strongest available nearby fact."
            ),
            confidence=0.52,
            source_urls=source_urls,
        )

    def _find_direct_match(self, requested_attribute: str, evidence: List[Evidence]) -> Optional[Evidence]:
        requested = requested_attribute.lower()
        for item in evidence:
            if requested in item.field.lower() or requested in item.value.lower():
                return item
        return None

    def _find_fallback(
        self, requested_attribute: str, evidence: List[Evidence]
    ) -> Tuple[Optional[Evidence], List[Evidence]]:
        fallback_options = self.ATTRIBUTE_FALLBACKS.get(requested_attribute.lower(), [])
        for option in fallback_options:
            for item in evidence:
                if option.lower() in item.value.lower() or option.lower() in item.field.lower():
                    related_evidence = [
                        evidence_item for evidence_item in evidence if evidence_item.field == item.field or evidence_item.value == item.value
                    ]
                    return item, related_evidence
        return None, []

    def _source_urls_for_value(self, value: str, evidence: List[Evidence]) -> List[str]:
        return sorted({item.source_url for item in evidence if item.value.lower() == value.lower()})

    def _source_urls_for_supporting_values(self, values: List[str], evidence: List[Evidence]) -> List[str]:
        normalized_values = {value.lower() for value in values}
        return sorted({item.source_url for item in evidence if item.value.lower() in normalized_values})

    def _run_llm_reasoner(self, requested_attribute: str, evidence: List[Evidence]):
        if not has_openai_config():
            return None

        evidence_lines = [
            f"- field={item.field}; value={item.value}; source={item.source_url}; snippet={item.snippet}"
            for item in evidence
        ]
        try:
            return ReasonerLLM().invoke(requested_attribute, evidence_lines)
        except Exception:
            return None
