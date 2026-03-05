from typing import Literal, List
from pydantic import BaseModel, Field, field_validator, model_validator


class Citation(BaseModel):
    clause_id: str = Field(..., description="Canonical clause ID")
    start_page: int = Field(..., description="Starting page number of clause")


class RAGResponse(BaseModel):
    answer: str
    found: bool
    citations: List[Citation] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]

    @field_validator("citations")
    @classmethod
    def validate_citations(cls, v):
        if not isinstance(v, list):
            raise ValueError("citations must be a list")

        if len(v) > 3:
            raise ValueError("Maximum of 3 citations allowed.")

        clause_ids = [c.clause_id for c in v]

        if len(clause_ids) != len(set(clause_ids)):
            raise ValueError("Duplicate clause_ids in citations.")

        return v

    @model_validator(mode="after")
    def consistency_check(self):

        if not self.found:
            if self.citations:
                raise ValueError(
                    "Citations must be empty when found is False."
                )

            if self.answer.strip() != "Answer not found in provided policy context.":
                raise ValueError(
                    "Answer must match not-found message when found is False."
                )

        return self