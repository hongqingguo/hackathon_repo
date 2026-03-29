import operator
from typing import Annotated, TypedDict

from utils.schemas import (
    CandidateEntity,
    ExtractedEntity,
    InvestigationRecord,
    QualifiedEntity,
    ReasonedEntity,
    SearchBrief,
    ValidatedEntity,
)


class GraphState(TypedDict, total=False):
    query: str
    brief: SearchBrief
    candidates: list[CandidateEntity]
    extracted_entities: list[ExtractedEntity]
    qualified_entities: list[QualifiedEntity]
    reasoned_entities: list[ReasonedEntity]
    validated_entities: list[ValidatedEntity]
    investigation_records: list[InvestigationRecord]
    trace: Annotated[list[str], operator.add]
