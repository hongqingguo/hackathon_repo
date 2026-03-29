from typing import Literal

from pydantic import BaseModel, Field


class PlannerOutput(BaseModel):
    target_type: Literal["company", "person", "product"] = Field(...)
    subject: str = Field(default="")
    geography: str = Field(default="")
    requested_attribute: str = Field(default="")
    investigation_goal: str = Field(default="")
    search_queries: list[str] = Field(default_factory=list)


class ReasoningOutput(BaseModel):
    best_matching_fact: str = Field(...)
    fact_match_type: Literal["observed_exact", "inferred_adjacent", "inferred_weak"] = Field(...)
    reasoning_summary: str = Field(...)
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_values: list[str] = Field(default_factory=list)
