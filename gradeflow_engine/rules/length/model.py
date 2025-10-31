"""Length rule model definition."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LengthRule(BaseModel):
    """
    Grade based on answer length constraints (words or characters).

    Example: Essay length requirements, short answer format checking.
    """

    type: Literal["LENGTH"] = "LENGTH"
    question_id: str = Field(description="Question ID to grade")
    min_words: int | None = Field(None, description="Minimum word count", ge=0)
    max_words: int | None = Field(None, description="Maximum word count", ge=0)
    min_chars: int | None = Field(None, description="Minimum character count", ge=0)
    max_chars: int | None = Field(None, description="Maximum character count", ge=0)
    max_points: float = Field(description="Maximum points available", ge=0)
    deduct_per_violation: float = Field(
        default=0.0, description="Points deducted for each constraint violation", ge=0
    )
    strict: bool = Field(
        default=False, description="If true, award 0 points if any constraint violated"
    )
    description: str | None = Field(None, description="Human-readable description of the rule")

    @field_validator("min_words", "max_words", "min_chars", "max_chars")
    @classmethod
    def validate_at_least_one_constraint(cls, v, info):
        # Check if at least one constraint is set
        values = info.data
        has_constraint = any(
            [
                values.get("min_words") is not None,
                values.get("max_words") is not None,
                values.get("min_chars") is not None,
                values.get("max_chars") is not None,
            ]
        )
        if not has_constraint and v is None:
            raise ValueError("At least one length constraint must be specified")
        return v
