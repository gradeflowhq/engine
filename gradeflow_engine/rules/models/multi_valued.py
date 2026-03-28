from typing import TYPE_CHECKING, Literal

from pydantic import Field

from ...questions.models import MultiValuedQuestion, NumericQuestion, Question, TextQuestion
from ...questions.types import Answer, QuestionType
from ..aggregations.completeness import output_fn, passed_fn, points_fn
from ..result import Result
from ..types import CompletenessAggregation, RuleValidationError
from .base import BaseRule, BaseSingleQuestionRule

if TYPE_CHECKING:
    from . import SingleTargetRule


def feedback_fn(results: list[Result]) -> str:
    return "\n".join(
        f"[{i + 1}] {'Correct' if result.passed else 'Incorrect'}\n{result.feedback}"
        for i, result in enumerate(results)
    )


class MultiValuedRule(BaseRule):
    type: Literal["MULTI_VALUED"] = "MULTI_VALUED"
    question_types: frozenset[QuestionType] = frozenset({"MULTI_VALUED"})
    rules: list["SingleTargetRule"] = Field(
        ...,
        min_length=1,
        description="List of rules to apply to each value in the multi-valued answer",
    )
    aggregation: CompletenessAggregation = Field(
        default="ALL",
        description="Aggregation method",
    )

    def validate_question_compatibility(self, question: Question) -> list[RuleValidationError]:
        errors: list[RuleValidationError] = []
        if not isinstance(question, MultiValuedQuestion):
            errors.append(
                f"Rule of type {self.type} is not compatible with question type {question.type}."
            )
            return errors
        if len(self.rules) != len(question.value_types):
            errors.append(
                f"Number of rules ({len(self.rules)}) does not match "
                f"number of values ({len(question.value_types)}) in the multi-valued question."
            )
            return errors
        for i, (rule, value_type) in enumerate(zip(self.rules, question.value_types, strict=True)):
            sub_question = TextQuestion() if value_type == "TEXT" else NumericQuestion()
            rule_errors = rule.validate_question_compatibility(sub_question)
            for err in rule_errors:
                errors.append(f"Value {i}: {err}")
        return errors

    def _process_answer(self, answer: Answer) -> Result:
        assert isinstance(answer, list), f"Answer must be a list for {self.type}."
        assert len(answer) == len(self.rules), (
            f"Number of answers must match number of rules in {self.type}."
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
            rule=(
                f"{self.__class__.__name__}"
                f"[{', '.join(rule.__class__.__name__ for rule in self.rules)}]"
            ),
        )


class MultiValuedQuestionRule(MultiValuedRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result, max_points: float) -> float:
        return points_fn(result, mode=self.aggregation, max_points=max_points)
