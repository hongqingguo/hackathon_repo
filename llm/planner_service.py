from langchain_core.messages import HumanMessage, SystemMessage

from llm.client import build_chat_model
from llm.prompts import PLANNER_SYSTEM_PROMPT, build_planner_user_prompt
from llm.schemas import PlannerOutput


class PlannerLLM:
    def invoke(self, query: str) -> PlannerOutput:
        model = build_chat_model().with_structured_output(PlannerOutput)
        return model.invoke(
            [
                SystemMessage(content=PLANNER_SYSTEM_PROMPT),
                HumanMessage(content=build_planner_user_prompt(query)),
            ]
        )
