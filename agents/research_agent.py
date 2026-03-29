from typing import List

from agents.search_agent import SearchAgent
from utils.schemas import CandidateEntity, SearchBrief


class ResearchAgent:
    def __init__(self) -> None:
        self.last_stats: dict = {}

    def run(self, brief: SearchBrief) -> List[CandidateEntity]:
        agent = SearchAgent()
        candidates = agent.run(brief)
        self.last_stats = agent.last_stats
        return candidates
