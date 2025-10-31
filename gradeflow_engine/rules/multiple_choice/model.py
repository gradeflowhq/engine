"""MultipleChoice rule model definition."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class MultipleChoiceRule(BaseModel):
    """
    Multiple choice question grading with various scoring modes.

    Supports MCQ (single answer) and MRQ (multiple answers).
    """

    type: Literal["MULTIPLE_CHOICE"] = "MULTIPLE_CHOICE"
    question_id: str = Field(description="Question ID to grade")
    correct_answers: list[str] = Field(description="List of correct answer(s)")
    max_points: float = Field(description="Maximum points available", ge=0)
    scoring_mode: Literal["all_or_nothing", "partial", "negative"] = Field(
        default="all_or_nothing",
        description=(
            "all_or_nothing: full points only if all correct; "
            "partial: proportional to correct selections; "
            "negative: deduct points for wrong selections"
        ),
    )
    penalty_per_wrong: float = Field(
        default=0.0, description="Points deducted per wrong selection (for negative scoring)", ge=0
    )
    case_sensitive: bool = Field(default=False, description="Whether matching is case-sensitive")
    description: str | None = Field(None, description="Human-readable description of the rule")

    @field_validator("correct_answers")
    @classmethod
    def validate_correct_answers(cls, v):
        if len(v) < 1:
            raise ValueError("At least one correct answer is required")
        return v
