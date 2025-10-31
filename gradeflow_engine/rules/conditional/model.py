"""Conditional rule model definition."""

from typing import Literal

from pydantic import BaseModel, Field


class ConditionalRule(BaseModel):
    """
    A conditional grading rule: if question X has answer Y, then question Z
    should have answer W.

    Example: "If Q1 answer is 'A', then Q2 correct answer is 'B'"
    """

    type: Literal["CONDITIONAL"] = "CONDITIONAL"
    if_question: str = Field(description="Question ID to check")
    if_answer: str = Field(description="Expected answer value for the condition")
    then_question: str = Field(description="Question ID to grade")
    then_correct_answer: str = Field(description="Correct answer if condition is met")
    max_points: float = Field(description="Points to award if correct", ge=0)
    description: str | None = Field(None, description="Human-readable description of the rule")
