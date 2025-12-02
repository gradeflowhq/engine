from typing import TYPE_CHECKING, Literal

from pydantic import Field

from ...questions.models import Question
from ...questions.types import Answer, QuestionId, QuestionType
from ..aggregations.completeness import output_fn, passed_fn, points_fn
from ..result import Result
from ..types import CompletenessAggregation, RuleValidationError
from .base import BaseRule, BaseSingleQuestionRule

if TYPE_CHECKING:
    from . import SingleTargetRule


class CompositeRule(BaseRule):
    type: Literal["COMPOSITE"] = "COMPOSITE"
    question_types: frozenset[QuestionType] = frozenset({"TEXT", "NUMERIC"})
    rules: list["SingleTargetRule"] = Field(
        ..., min_length=1, description="List of rules to apply to the answer"
    )
    aggregation: CompletenessAggregation = Field(
        default="ALL",
        description="Aggregation method to combine rule results: 'ALL', 'ANY', or 'PARTIAL'",
    )

    def _process_answer(self, answer: Answer) -> Result:
        results = [rule.process_answer(answer) for rule in self.rules]
        passed_list = [res.passed for res in results]
        output = output_fn(passed_list, mode=self.aggregation)
        passed = passed_fn(passed_list, mode=self.aggregation)
        feedback = "\n".join(res.feedback for res in results)
        return Result(
            output=output,
            passed=passed,
            feedback=feedback,
            rule=self.__class__.__name__,
        )


class CompositeQuestionRule(CompositeRule, BaseSingleQuestionRule):
    def validate_compatibility(
        self, question_map: dict[QuestionId, Question]
    ) -> list[RuleValidationError]:
        errors = super().validate_compatibility(question_map)
        if self.question_id not in question_map:
            return errors  # Question existence is validated elsewhere
        for rule in self.rules:
            errors.extend(rule.validate_question_compatibility(question_map[self.question_id]))
        return errors

    def compute_points(self, result: Result) -> float:
        return points_fn(result, mode=self.aggregation, max_points=self.max_points)
