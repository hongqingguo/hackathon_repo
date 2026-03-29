from langchain_core.messages import HumanMessage, SystemMessage

from llm.client import build_chat_model
from llm.prompts import REASONER_SYSTEM_PROMPT, build_reasoner_user_prompt
from llm.schemas import ReasoningOutput


class ReasonerLLM:
    def invoke(self, requested_attribute: str, evidence_lines: list[str]) -> ReasoningOutput:
        model = build_chat_model().with_structured_output(ReasoningOutput)
        return model.invoke(
            [
                SystemMessage(content=REASONER_SYSTEM_PROMPT),
                HumanMessage(content=build_reasoner_user_prompt(requested_attribute, evidence_lines)),
            ]
        )
