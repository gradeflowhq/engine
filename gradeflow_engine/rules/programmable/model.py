"""Programmable rule model definition."""

from typing import Literal

from pydantic import BaseModel, Field


class ProgrammableRule(BaseModel):
    """
    Programmable grading: execute custom Python script to evaluate answers.

    The script has access to:
    - student_answers: Dict[str, str] - all student's answers
    - question_id: str - the current question being graded
    - answer: str - the student's answer to this question

    The script must set:
    - points_awarded: float - points to award (0 to max points)
    - feedback: str (optional) - feedback message
    """

    type: Literal["PROGRAMMABLE"] = "PROGRAMMABLE"
    question_id: str = Field(description="Question ID to grade")
    script: str = Field(description="Python script to execute for grading")
    max_points: float = Field(description="Maximum points available", ge=0)
    timeout_ms: int = Field(
        default=5000, description="Script execution timeout in milliseconds", ge=100, le=30000
    )
    memory_mb: int = Field(default=50, description="Memory limit in MB", ge=10, le=500)
    description: str | None = Field(None, description="Human-readable description of the rule")
