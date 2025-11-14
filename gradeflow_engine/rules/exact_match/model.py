"""
Exact match rule that awards points when a text answer equals the expected answer
after normalization.
"""

from typing import Literal

from pydantic import Field

from gradeflow_engine.types import QuestionType

from ..base import BaseSingleQuestionRule, TextRuleConfig


class ExactMatchRule(BaseSingleQuestionRule):
    """Exact match rule where the student's normalized text must equal the expected answer."""

    type: Literal["EXACT_MATCH"] = "EXACT_MATCH"

    compatible_types: frozenset[QuestionType] = frozenset({"TEXT"})

    answer: str = Field(..., description="Expected exact answer")
    config: TextRuleConfig = Field(
        default_factory=TextRuleConfig, description="Text normalization config"
    )
