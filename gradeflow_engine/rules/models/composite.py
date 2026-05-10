from types import GenericAlias
from typing import TYPE_CHECKING, Literal, cast

from pydantic import Field, computed_field
from pydantic.fields import FieldInfo

from ...questions.models import Question
from ...questions.types import Answer, QuestionId, QuestionType
from ..aggregations.completeness import output_fn, passed_fn, points_fn
from ..markdown import markdown_code
from ..result import Result
from ..schema import RULE_LIST_INPUT, gradeflow_schema_extra, rule_question_types, value_rule_union
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


class CompositeRule(BaseRule):
    type: Literal["COMPOSITE"] = rule_type_field("COMPOSITE")
    display_name: Literal["Composite"] = rule_display_name_field("Composite")
    question_types: frozenset[QuestionType] = rule_question_types_field({"TEXT", "NUMERIC"})
    rules: list["SingleTargetRule"] = Field(
        ..., min_length=1, description="List of rules to apply to the answer"
    )
    aggregation: CompletenessAggregation = Field(
        default="ALL",
        description="Aggregation method to combine rule results: 'ALL', 'ANY', or 'PARTIAL'",
    )

    @classmethod
    def field_overrides(
        cls,
        context: "RuleContext",
    ) -> dict[str, tuple[object, FieldInfo]]:
        overrides = super().field_overrides(context)
        if context.question_type is None:
            return overrides
        return {
            **overrides,
            "rules": (
                GenericAlias(list, value_rule_union(context.question_type)),
                cast(
                    FieldInfo,
                    Field(
                        ...,
                        min_length=1,
                        description="List of rules to apply to the answer",
                        json_schema_extra=gradeflow_schema_extra(RULE_LIST_INPUT),
                    ),
                ),
            ),
        }

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
            and context.question_type in rule_question_types(cls)
        ):
            return context.for_value_rules()
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def description(self) -> str:
        desc_aggregation = {
            "ALL": "All must be true",
            "ANY": "At least one must be true",
            "PARTIAL": "Partial credit based on how many are true",
        }
        return (
            f"**{desc_aggregation.get(self.aggregation, 'Unknown aggregation')}** "
            f"({markdown_code(self.aggregation)}):"
            + "\n"
            + "\n".join(rule.description for rule in self.rules)
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
            rule=self.display_name,
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

    def compute_points(self, result: Result, max_points: float) -> float:
        return points_fn(result, mode=self.aggregation, max_points=max_points)
