from tools.agent_tools import compare_evidence_tool
from utils.schemas import ReasonedEntity, SearchBrief, ValidatedEntity


class ValidationSkill:
    def run(self, brief: SearchBrief, lead: ReasonedEntity) -> ValidatedEntity:
        result = compare_evidence_tool.invoke(
            {
                "evidence": [item.__dict__ for item in lead.evidence],
                "selected_source_urls": lead.source_urls,
                "fact_match_type": lead.fact_match_type,
            }
        )
        return ValidatedEntity(
            **lead.__dict__,
            validation_status=result["validation_status"],
            validation_notes=result["validation_notes"],
            validation_score=result["validation_score"],
            validation_scope=result["validation_scope"],
            human_review_required=result["human_review_required"],
            human_review_reason=result["human_review_reason"],
            corroborated_fields=result["corroborated_fields"],
            conflicting_fields=result["conflicting_fields"],
            validation_source_urls=result["validation_source_urls"],
        )
