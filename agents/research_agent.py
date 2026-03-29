from typing import List

from tools.agent_tools import search_entities_tool
from utils.schemas import CandidateEntity, SearchBrief


class ResearchAgent:
    def run(self, brief: SearchBrief) -> List[CandidateEntity]:
        raw_candidates = search_entities_tool.invoke(
            {
                "target_type": brief.target_type,
                "subject": brief.subject,
                "geography": brief.geography,
                "requested_attribute": brief.requested_attribute,
                "investigation_goal": brief.investigation_goal,
            }
        )
        return [CandidateEntity(**candidate) for candidate in raw_candidates]
