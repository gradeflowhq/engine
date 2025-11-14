"""Keyword rule that matches configured keywords against a text answer using a chosen mode."""

from typing import Literal

from pydantic import Field

from gradeflow_engine.types import QuestionType

from ..base import BaseSingleQuestionRule, TextRuleConfig


class KeywordRule(BaseSingleQuestionRule):
    """Match configured keywords in a text answer using the specified mode."""

    type: Literal["KEYWORD"] = "KEYWORD"
    compatible_types: frozenset[QuestionType] = frozenset({"TEXT"})

    keywords: list[str] = Field(..., min_length=1, description="Keywords to look for")
    mode: Literal["all", "partial", "any"] = Field(
        default="all",
        description=(
            "Matching mode: 'all' requires every keyword to be present to receive max points; "
            "'partial' awards points per keyword found (points is divided evenly across keywords); "
            "'any' awards full points if at least one keyword is present"
        ),
    )
    config: TextRuleConfig = Field(default_factory=TextRuleConfig)
