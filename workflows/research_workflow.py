from langgraph.graph import END, START, StateGraph

from agents.planner_agent import PlannerAgent
from agents.reasoning_agent import ReasoningAgent
from agents.research_agent import ResearchAgent
from skills.extraction_skill import ExtractionSkill
from skills.formatting_skill import FormattingSkill
from skills.qualification_skill import QualificationSkill
from skills.scoring_skill import ScoringSkill
from skills.validation_skill import ValidationSkill
from state.graph_state import GraphState


def build_research_workflow():
    graph = StateGraph(GraphState)

    graph.add_node("plan_request", _plan_request)
    graph.add_node("research", _research)
    graph.add_node("extract", _extract)
    graph.add_node("qualify", _qualify)
    graph.add_node("reason", _reason)
    graph.add_node("validate", _validate)
    graph.add_node("score", _score)
    graph.add_node("format", _format)

    graph.add_edge(START, "plan_request")
    graph.add_edge("plan_request", "research")
    graph.add_edge("research", "extract")
    graph.add_edge("extract", "qualify")
    graph.add_edge("qualify", "reason")
    graph.add_edge("reason", "validate")
    graph.add_edge("validate", "score")
    graph.add_edge("score", "format")
    graph.add_edge("format", END)

    return graph.compile()


def _plan_request(state: GraphState) -> GraphState:
    agent = PlannerAgent()
    brief = agent.run(state["query"])
    return {
        "brief": brief,
        "trace": [f"[planner] Target type={brief.target_type}, subject={brief.subject or 'n/a'}, attribute={brief.requested_attribute or 'n/a'}"],
    }


def _research(state: GraphState) -> GraphState:
    agent = ResearchAgent()
    candidates = agent.run(state["brief"])
    return {
        "candidates": candidates,
        "trace": [f"[research] Retrieved {len(candidates)} candidate entities via tool-backed search."],
    }


def _extract(state: GraphState) -> GraphState:
    skill = ExtractionSkill()
    extracted_entities = [skill.run(state["brief"], candidate) for candidate in state.get("candidates", [])]
    return {
        "extracted_entities": extracted_entities,
        "trace": [f"[extract] Built normalized evidence for {len(extracted_entities)} entities."],
    }


def _qualify(state: GraphState) -> GraphState:
    skill = QualificationSkill()
    qualified_entities = [skill.run(state["brief"], entity) for entity in state.get("extracted_entities", [])]
    qualified_entities = [entity for entity in qualified_entities if entity.fit_label != "low"]
    return {
        "qualified_entities": qualified_entities,
        "trace": [f"[qualify] Retained {len(qualified_entities)} entities after fit filtering."],
    }


def _reason(state: GraphState) -> GraphState:
    agent = ReasoningAgent()
    reasoned_entities = [agent.run(state["brief"], entity) for entity in state.get("qualified_entities", [])]
    return {
        "reasoned_entities": reasoned_entities,
        "trace": [f"[reason] Matched requested attributes across {len(reasoned_entities)} entities."],
    }


def _validate(state: GraphState) -> GraphState:
    skill = ValidationSkill()
    validated_entities = [skill.run(state["brief"], entity) for entity in state.get("reasoned_entities", [])]
    return {
        "validated_entities": validated_entities,
        "trace": [f"[validate] Compared source evidence for {len(validated_entities)} entities."],
    }


def _score(state: GraphState) -> GraphState:
    skill = ScoringSkill()
    investigation_records = [skill.run(state["brief"], entity) for entity in state.get("validated_entities", [])]
    investigation_records.sort(key=lambda item: item.priority_score, reverse=True)
    return {
        "investigation_records": investigation_records,
        "trace": [f"[score] Ranked {len(investigation_records)} findings for output."],
    }


def _format(state: GraphState) -> GraphState:
    skill = FormattingSkill()
    skill.run(state["brief"], state.get("investigation_records", []))
    return {
        "trace": ["[format] Final results are ready for CSV and summary output."],
    }
