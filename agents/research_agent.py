from typing import List

from tools.agent_tools import search_entities_tool
from utils.schemas import CandidateEntity, SearchBrief, SourceDocument


class ResearchAgent:
    def run(self, brief: SearchBrief) -> List[CandidateEntity]:
        raw_candidates = search_entities_tool.invoke(
            {
                "raw_query": brief.raw_query,
                "target_type": brief.target_type,
                "subject": brief.subject,
                "geography": brief.geography,
                "requested_attribute": brief.requested_attribute,
                "investigation_goal": brief.investigation_goal,
                "search_queries": brief.search_queries,
                "search_backend": brief.search_backend,
            }
        )
        candidates: List[CandidateEntity] = []
        for candidate in raw_candidates:
            source_documents = [SourceDocument(**doc) for doc in candidate.get("source_documents", [])]
            candidates.append(CandidateEntity(**{**candidate, "source_documents": source_documents}))
        return candidates
