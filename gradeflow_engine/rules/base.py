"""Base utilities and base rule models for rule processors to reduce code duplication.

This module contains small helper functions used by rule processors as well as
shared base Pydantic models used by rule implementations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from ..types import QuestionType

if TYPE_CHECKING:
    from ..models import GradeDetail


__all__ = [
    "create_grade_detail",
    "QuestionConstraint",
    "TextRuleConfig",
    "BaseRule",
    "BaseSingleQuestionRule",
]


@dataclass(frozen=True)
class QuestionConstraint:
    """Immutable metadata describing a rule <-> question field relationship.

    Use simple dataclass to keep these lightweight, hashable, and easy to
    construct at import time for use as class-level metadata.
    """

    type: "QuestionType"
    source: str
    target: str


class TextRuleConfig(BaseModel):
    """Configuration options for text-based rules.

    - ignore_case: whether matching should be case-insensitive
    - trim_whitespace: whether to strip leading/trailing whitespace before matching
    """

    ignore_case: bool = Field(
        default=True, description="Ignore case when comparing text (default: True)"
    )
    trim_whitespace: bool = Field(
        default=True, description="Trim leading/trailing whitespace before matching"
    )


class BaseRule(BaseModel):
    """Base class for all rules."""

    # Constant describing which question types the rule supports.
    # Use an immutable set to enforce the 'constant' intent.
    compatible_types: frozenset["QuestionType"] = frozenset()

    # Schema constraints the rule relies on to function correctly.
    constraints: frozenset["QuestionConstraint"] = frozenset()


class BaseSingleQuestionRule(BaseRule):
    """Common fields for single-question rules."""

    question_id: str = Field(..., description="Target question id")
    max_points: float = Field(default=1.0, description="Maximum points for the question")


def create_grade_detail(
    question_id: str,
    student_answer: str | None,
    correct_answer: str | None,
    points_awarded: float,
    max_points: float,
    is_correct: bool,
    feedback: str | None = None,
    rule_applied: str | None = None,
) -> "GradeDetail":
    """
    Factory function for creating GradeDetail objects.

    Handles the import to avoid circular dependencies and provides
    a consistent interface for creating grade details.

    Args:
        question_id: Question identifier
        student_answer: Student's answer
        correct_answer: Expected correct answer (if applicable)
        points_awarded: Points awarded for this question
        max_points: Maximum max_points possible
        is_correct: Whether the answer is correct
        feedback: Optional feedback message
        rule_applied: Optional rule identifier

    Returns:
        GradeDetail instance
    """
    from ..models import GradeDetail

    return GradeDetail(
        question_id=question_id,
        student_answer=student_answer,
        correct_answer=correct_answer,
        points_awarded=points_awarded,
        max_points=max_points,
        is_correct=is_correct,
        feedback=feedback,
        rule_applied=rule_applied,
    )


def preprocess_text(text: str, config: TextRuleConfig) -> str:
    """
    Preprocess text according to the given TextRuleConfig.

    Args:
        text: The text to preprocess
        config: TextRuleConfig with preprocessing options

    Returns:
        Preprocessed text
    """
    if config.trim_whitespace:
        text = text.strip()
    if config.ignore_case:
        text = text.lower()
    return text
