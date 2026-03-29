from langchain_core.messages import HumanMessage, SystemMessage

from llm.client import build_chat_model
from llm.prompts import RETRIEVAL_SYSTEM_PROMPT, build_retrieval_user_prompt
from llm.schemas import RetrievalAssessment


class RetrievalLLM:
    def invoke(
        self,
        raw_query: str,
        target_type: str,
        requested_attribute: str,
        investigation_goal: str,
        document_url: str,
        document_title: str,
        document_snippet: str,
        document_content: str,
        candidate_name: str = "",
        canonical_domain: str = "",
        first_party: bool = False,
    ) -> RetrievalAssessment:
        model = build_chat_model().with_structured_output(RetrievalAssessment)
        return model.invoke(
            [
                SystemMessage(content=RETRIEVAL_SYSTEM_PROMPT),
                HumanMessage(
                    content=build_retrieval_user_prompt(
                        raw_query=raw_query,
                        target_type=target_type,
                        requested_attribute=requested_attribute,
                        investigation_goal=investigation_goal,
                        document_url=document_url,
                        document_title=document_title,
                        document_snippet=document_snippet,
                        document_content=document_content,
                        candidate_name=candidate_name,
                        canonical_domain=canonical_domain,
                        first_party=first_party,
                    )
                ),
            ]
        )
