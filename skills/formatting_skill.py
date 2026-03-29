from utils.schemas import InvestigationRecord, SearchBrief


class FormattingSkill:
    def run(self, brief: SearchBrief, records: list[InvestigationRecord]) -> dict:
        return {
            "record_count": len(records),
            "top_result": records[0].entity_name if records else "",
        }
