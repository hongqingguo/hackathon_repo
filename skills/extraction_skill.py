from tools.agent_tools import extract_entity_tool
from utils.schemas import CandidateEntity, Evidence, ExtractedEntity, SearchBrief


class ExtractionSkill:
    def run(self, brief: SearchBrief, candidate: CandidateEntity) -> ExtractedEntity:
        candidate_payload = {
            **candidate.__dict__,
            "source_documents": [document.__dict__ for document in candidate.source_documents],
        }
        extracted = extract_entity_tool.invoke({"candidate": candidate_payload})
        evidence = [Evidence(**item) for item in extracted["evidence"]]
        return ExtractedEntity(**{**extracted, "evidence": evidence})
