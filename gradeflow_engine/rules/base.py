"""Base utilities and shared Pydantic models used by rule implementations and processors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from ..types import QuestionType

if TYPE_CHECKING:
    from ..models import GradeDetail
    from ..schema import QuestionSchema


__all__ = [
    "create_grade_detail",
    "QuestionConstraint",
    "TextRuleConfig",
    "BaseRule",
    "BaseSingleQuestionRule",
]


@dataclass(frozen=True)
class QuestionConstraint:
    """Immutable metadata describing a rule-to-question field relationship."""

    type: "QuestionType"
    source: str
    target: str


class TextRuleConfig(BaseModel):
    """Configuration options for text rules such as case folding and trimming."""

    ignore_case: bool = Field(
        default=True, description="Ignore case when comparing text (default: True)"
    )
    trim_whitespace: bool = Field(
        default=True, description="Trim leading/trailing whitespace before matching"
    )


class BaseRule(BaseModel):
    """Common base class for all rule models."""

    # Constant describing which question types the rule supports.
    # Use an immutable set to enforce the 'constant' intent.
    compatible_types: frozenset["QuestionType"] = frozenset()

    # Schema constraints the rule relies on to function correctly.
    constraints: frozenset["QuestionConstraint"] = frozenset()

    def get_question_ids(self) -> set[str]:
        """Return the set of question IDs this rule applies to."""
        raise NotImplementedError("Subclasses must implement get_question_ids method")

    def get_target_question_ids(self) -> set[str]:
        """Return the set of target question IDs this rule applies to."""
        raise NotImplementedError("Subclasses must implement get_target_question_ids method")


class BaseSingleQuestionRule(BaseRule):
    """Common fields and helpers for rules that target a single question."""

    question_id: str = Field(..., description="Target question id")
    max_points: float = Field(default=1.0, description="Maximum points for the question")

    def validate_against_question_schema(
        self, question_map: dict[str, "QuestionSchema"], rule_description: str
    ) -> list[str]:
        from gradeflow_engine.rules.utils import validate_type_compatibility

        if self.question_id not in question_map:
            return [f"{rule_description}: Question ID '{self.question_id}' not found in schema"]

        return validate_type_compatibility(
            schema=question_map[self.question_id],
            compatible_types=self.compatible_types,
            rule_description=rule_description,
            rule_name=self.__class__.__name__,
        )

    def get_question_ids(self) -> set[str]:
        """Return the single question id targeted by this rule as a set."""
        return {self.question_id}

    def get_target_question_ids(self) -> set[str]:
        """Return the single target question id as a set."""
        return {self.question_id}


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
    """Create a GradeDetail instance with the given question and scoring information."""
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
    """Preprocess text according to the provided TextRuleConfig (trim and case-fold)."""
    if config.trim_whitespace:
        text = text.strip()
    if config.ignore_case:
        text = text.lower()
    return text
