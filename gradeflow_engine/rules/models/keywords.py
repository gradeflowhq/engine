from typing import Literal

from pydantic import Field

from ...questions.types import Answer, QuestionType
from ..aggregations.completeness import output_fn, passed_fn, points_fn
from ..result import Result
from ..types import CompletenessAggregation
from .base import BaseRule, BaseSingleQuestionRule


class KeywordsRule(BaseRule):
    type: Literal["KEYWORDS"] = "KEYWORDS"
    question_types: frozenset[QuestionType] = frozenset({"TEXT"})
    keywords: list[str] = Field(
        ...,
        min_length=1,
        description="List of keywords that must be present in the answer",
    )
    mode: CompletenessAggregation = Field(
        default="ALL",
        description=(
            "Mode of keyword matching: "
            "'ALL' requires all keywords to be present, "
            "'ANY' requires at least one."
        ),
    )

    def _process_answer(self, answer: Answer) -> Result:
        matches = [keyword in str(answer) for keyword in self.keywords]
        output = output_fn(matches, mode=self.mode)
        passed = passed_fn(matches, mode=self.mode)
        feedback = f"The answer ({answer}) " + (
            f"contains all keywords: {', '.join(self.keywords)}."
            if passed
            else f"does not contain the required keywords: {', '.join(self.keywords)}."
        )
        return Result(
            output=output,
            passed=passed,
            feedback=feedback,
            rule=self.__class__.__name__,
        )


class KeywordsQuestionRule(KeywordsRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result) -> float:
        return points_fn(result, mode=self.mode, max_points=self.max_points)
