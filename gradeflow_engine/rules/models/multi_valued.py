from types import GenericAlias
from typing import TYPE_CHECKING, Any, Literal, cast

from pydantic import Field, computed_field
from pydantic.fields import FieldInfo

from ...questions.models import MultiValuedQuestion, NumericQuestion, Question, TextQuestion
from ...questions.types import Answer, QuestionType
from ..aggregations.completeness import output_fn, passed_fn, points_fn
from ..result import Result
from ..schema import RULE_LIST_INPUT, gradeflow_schema_extra, value_rule_union_for_question_types
from ..types import CompletenessAggregation, RuleValidationError
from .base import (
    BaseRule,
    BaseSingleQuestionRule,
    rule_display_name_field,
    rule_question_types_field,
    rule_type_field,
)

if TYPE_CHECKING:
    from ..context import RuleContext, RulePath
    from . import SingleTargetRule


def feedback_fn(results: list[Result]) -> str:
    return "\n".join(
        f"[{i + 1}] {'Correct' if result.passed else 'Incorrect'}\n{result.feedback}"
        for i, result in enumerate(results)
    )


class MultiValuedRule(BaseRule):
    type: Literal["MULTI_VALUED"] = rule_type_field("MULTI_VALUED")
    display_name: Literal["Multi Valued"] = rule_display_name_field("Multi Valued")
    question_types: frozenset[QuestionType] = rule_question_types_field({"MULTI_VALUED"})
    rules: list["SingleTargetRule"] = Field(
        ...,
        min_length=1,
        description="List of rules to apply to each value in the multi-valued answer",
    )
    aggregation: CompletenessAggregation = Field(
        default="ALL",
        description="Aggregation method",
    )

    @classmethod
    def field_overrides(
        cls,
        context: "RuleContext",
    ) -> dict[str, tuple[object, FieldInfo]]:
        overrides = super().field_overrides(context)
        if not isinstance(context.question, MultiValuedQuestion):
            return overrides
        value_types = [
            cast(QuestionType, value_type) for value_type in context.question.value_types
        ]
        return {
            **overrides,
            "rules": (
                GenericAlias(list, value_rule_union_for_question_types(value_types)),
                cast(
                    FieldInfo,
                    Field(
                        ...,
                        min_length=len(value_types),
                        max_length=len(value_types),
                        description=(
                            "One rule per parsed value, fixed by the multi-valued question."
                        ),
                        json_schema_extra=gradeflow_schema_extra(RULE_LIST_INPUT),
                    ),
                ),
            ),
        }

    @classmethod
    def initial_value_overrides(
        cls,
        context: "RuleContext",
    ) -> dict[str, Any]:
        if isinstance(context.question, MultiValuedQuestion):
            return {"rules": [{} for _ in context.question.value_types]}
        return {}

    @classmethod
    def nested_context(
        cls,
        context: "RuleContext",
        path: "RulePath",
    ) -> "RuleContext | None":
        if (
            len(path) == 2
            and path[0] == "rules"
            and isinstance(path[1], int)
            and isinstance(context.question, MultiValuedQuestion)
        ):
            return context.for_value_slot(path[1])
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def description(self) -> str:
        return "\n\n".join(
            f"**Value {i + 1}:**\n{rule.description}" for i, rule in enumerate(self.rules)
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
        if not isinstance(answer, list):
            raise TypeError(f"Answer must be a list for {self.type}.")
        if len(answer) != len(self.rules):
            raise ValueError(f"Number of answers must match number of rules in {self.type}.")

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
            rule=self.display_name,
        )


class MultiValuedQuestionRule(MultiValuedRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result, max_points: float) -> float:
        return points_fn(result, mode=self.aggregation, max_points=max_points)
