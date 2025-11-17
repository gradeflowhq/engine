from typing import TYPE_CHECKING, Literal

from pydantic import Field

from ...questions.types import Answer, QuestionType
from ..aggregations.completeness import output_fn, passed_fn, points_fn
from ..result import Result
from ..types import CompletenessAggregation
from .base import BaseRule, BaseSingleQuestionRule

if TYPE_CHECKING:
    from . import SingleTargetRule


def feedback_fn(results: list[Result]) -> str:
    return "Results: " + "; ".join(
        f"[{i + 1}] {'✓' if result.passed else '✗'} {result.feedback}"
        for i, result in enumerate(results)
    )


class MultiValuedRule(BaseRule):
    type: Literal["MULTI_VALUED"] = "MULTI_VALUED"
    question_types: frozenset[QuestionType] = frozenset({"MULTI_VALUED"})
    rules: list[SingleTargetRule] = Field(
        ...,
        min_length=1,
        description="List of rules to apply to each value in the multi-valued answer",
    )
    aggregation: CompletenessAggregation = Field(
        default="ALL",
        description="Aggregation method",
    )

    def _process_answer(self, answer: Answer) -> Result:
        assert isinstance(answer, list), "Answer must be a list for MultiValuedRule."
        assert len(answer) == len(self.rules), (
            "Number of answers must match number of rules in MultiValuedRule."
        )
        results: list[Result] = [
            rule.process_answer(value) for value, rule in zip(answer, self.rules, strict=True)
        ]
        passed_list = [result.passed for result in results]
        output = output_fn(passed_list, mode=self.aggregation)
        passed = passed_fn(passed_list, mode=self.aggregation)
        feedback = feedback_fn(results)
        return Result(
            output=output,
            passed=passed,
            feedback=feedback,
            rule=self.__class__.__name__,
        )


class MultiValuedQuestionRule(MultiValuedRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result) -> float:
        return points_fn(result, mode=self.aggregation, max_points=self.max_points)
