from utils.schemas import ExtractedEntity, QualifiedEntity, SearchBrief


class QualificationSkill:
    def run(self, brief: SearchBrief, lead: ExtractedEntity) -> QualifiedEntity:
        score = 0

        haystack = " ".join(
            [
                lead.entity_name,
                lead.entity_type,
                lead.location,
                lead.summary,
                " ".join(lead.observed_fact_labels),
                " ".join(lead.signal_labels),
            ]
        ).lower()

        if brief.target_type == lead.entity_type:
            score += 2
        if brief.subject and brief.subject.lower() in haystack:
            score += 2
        if brief.geography and brief.geography.lower() in haystack:
            score += 2
        if brief.requested_attribute and brief.requested_attribute.lower() in haystack:
            score += 2
        if brief.investigation_goal:
            goal_hits = sum(1 for term in brief.investigation_goal.lower().split() if len(term) > 3 and term in haystack)
            score += min(goal_hits, 2)

        if score >= 4:
            fit_label = "high"
            fit_reason = "Entity strongly matches the investigation target and contains relevant evidence."
        elif score >= 2:
            fit_label = "medium"
            fit_reason = "Entity partially matches the requested investigation."
        else:
            fit_label = "low"
            fit_reason = "Entity is too weakly aligned with the current request."

        return QualifiedEntity(
            **lead.__dict__,
            fit_label=fit_label,
            fit_reason=fit_reason,
        )
