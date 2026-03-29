from llm.config import has_openai_config
from llm.planner_service import PlannerLLM
from utils.query_parser import parse_query
from utils.schemas import SearchBrief


class PlannerAgent:
    def run(self, query: str, search_backend_override: str = "") -> SearchBrief:
        fallback = parse_query(query, search_backend_override=search_backend_override)
        if not has_openai_config():
            return fallback

        try:
            llm_output = PlannerLLM().invoke(query)
            return SearchBrief(
                raw_query=query,
                target_type=llm_output.target_type,
                subject=llm_output.subject,
                geography=llm_output.geography,
                requested_attribute=llm_output.requested_attribute,
                investigation_goal=llm_output.investigation_goal,
                search_queries=llm_output.search_queries or fallback.search_queries,
                search_backend=fallback.search_backend,
            )
        except Exception:
            return fallback
