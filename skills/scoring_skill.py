from utils.schemas import InvestigationRecord, SearchBrief, ValidatedEntity


class ScoringSkill:
    def run(self, brief: SearchBrief, lead: ValidatedEntity) -> InvestigationRecord:
        score = 40

        haystack = " ".join(
            [
                lead.entity_name,
                lead.entity_type,
                lead.location,
                lead.summary,
                lead.best_matching_fact,
                " ".join(lead.signal_labels),
            ]
        ).lower()

        if brief.target_type == lead.entity_type:
            score += 20
        if brief.subject and brief.subject.lower() in haystack:
            score += 15
        if brief.geography and brief.geography.lower() in lead.location.lower():
            score += 15
        if lead.signal_labels:
            score += 10
        if lead.fact_match_type == "observed_exact":
            score += 15
        elif lead.fact_match_type == "inferred_adjacent":
            score += 8

        score += min(int(lead.confidence * 10), 10)
        score += int(lead.validation_score * 10)
        if lead.validation_status == "needs_review":
            score -= 8
        score = min(score, 100)

        why_relevant = f"{lead.entity_name} matches the query and the best fact found is '{lead.best_matching_fact}'."
        if lead.signal_labels:
            why_relevant = f"{why_relevant} The entity also shows signal '{lead.signal_labels[0]}'."

        recommended_action = (
            f"Review the evidence for '{lead.best_matching_fact}' and compare it against the requested attribute '{lead.requested_attribute}'."
        )

        return InvestigationRecord(
            **lead.__dict__,
            priority_score=score,
            why_relevant=why_relevant,
            recommended_action=recommended_action,
        )
