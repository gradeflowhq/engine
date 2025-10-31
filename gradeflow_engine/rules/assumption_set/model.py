"""AssumptionSet rule model definition."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AnswerSet(BaseModel):
    """A named set of correct answers for a group of questions."""

    name: str = Field(description="Name/label for this answer set")
    answers: dict[str, str] = Field(description="Map of question_id -> correct_answer")


class AssumptionSetRule(BaseModel):
    """
    Assumption-based grading: define multiple valid answer sets and apply
    the most favorable one to each student.

    Example: Different valid interpretations of a problem that lead to
    different answer keys.
    """

    type: Literal["ASSUMPTION_SET"] = "ASSUMPTION_SET"
    question_ids: list[str] = Field(description="List of question IDs in this group")
    answer_sets: list[AnswerSet] = Field(description="List of valid answer sets")
    mode: Literal["favor_best", "first_match"] = Field(
        default="favor_best",
        description="favor_best: pick set with highest score; first_match: use first matching set",
    )
    points_per_question: dict[str, float] | None = Field(
        None,
        description=(
            "Points for each question (if None, uses points from individual rules or defaults to 1)"
        ),
    )
    description: str | None = Field(None, description="Human-readable description of the rule")

    @field_validator("answer_sets")
    @classmethod
    def validate_answer_sets(cls, v):
        if len(v) < 1:
            raise ValueError("At least one answer set is required")
        return v
