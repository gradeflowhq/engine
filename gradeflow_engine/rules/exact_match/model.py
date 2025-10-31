"""
Exact Match Rule model definition.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ExactMatchRule(BaseModel):
    """
    Simple exact match grading: student answer must match the correct answer.

    Supports case-insensitive comparison and whitespace trimming for flexibility.
    Best for factual questions with single correct answers.
    """

    type: Literal["EXACT_MATCH"] = "EXACT_MATCH"
    question_id: str = Field(..., description="Question identifier to grade")
    correct_answer: str = Field(..., description="The expected correct answer")
    max_points: float = Field(..., description="Maximum points for correct answer", ge=0)
    case_sensitive: bool = Field(default=False, description="Whether comparison is case-sensitive")
    trim_whitespace: bool = Field(
        default=True, description="Trim leading/trailing whitespace before comparison"
    )
    description: str | None = Field(None, description="Optional human-readable description")

    @field_validator("question_id")
    @classmethod
    def validate_question_id(cls, v: str) -> str:
        """Validate question_id format."""
        from ..utils import validate_question_id

        return validate_question_id(v)
