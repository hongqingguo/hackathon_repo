from utils.query_parser import parse_query
from utils.schemas import SearchBrief


class PlannerAgent:
    def run(self, query: str) -> SearchBrief:
        return parse_query(query)
