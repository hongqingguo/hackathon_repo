from typing import List

from agents.search_agent import SearchAgent
from utils.schemas import CandidateEntity, SearchBrief


class ResearchAgent:
    def run(self, brief: SearchBrief) -> List[CandidateEntity]:
        return SearchAgent().run(brief)
