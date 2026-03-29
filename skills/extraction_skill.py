from tools.agent_tools import extract_entity_tool
from utils.schemas import CandidateEntity, Evidence, ExtractedEntity, SearchBrief


class ExtractionSkill:
    def run(self, brief: SearchBrief, candidate: CandidateEntity) -> ExtractedEntity:
        extracted = extract_entity_tool.invoke({"candidate": candidate.__dict__})
        evidence = [Evidence(**item) for item in extracted["evidence"]]
        return ExtractedEntity(**{**extracted, "evidence": evidence})
