from pydantic import BaseModel, Field
from typing import List


class EvaluationQuery(BaseModel):
    """
    Strict evaluation query schema.

    Enforces:
        - query must exist
        - relevant_clause_ids must be a non-empty list
    """

    query: str = Field(..., min_length=1)
    relevant_clause_ids: List[str] = Field(..., min_items=1)