from typing import TYPE_CHECKING, Literal

from pydantic import Field

from ...questions.models import Question
from ...questions.types import Answer, QuestionId, QuestionType
from ..result import QuestionResult
from ..types import BooleanAggregation, RuleValidationError
from ..validators import validate_unique_target_questions_in_rules
from .base import BaseMultiQuestionRule

if TYPE_CHECKING:
    from . import SingleTargetQuestionRule


def check_condition(results: list[QuestionResult], aggregation: BooleanAggregation) -> bool:
    passed_list: list[bool] = [result.passed for result in results]
    if aggregation == "AND":
        return all(passed_list)
    elif aggregation == "OR":
        return any(passed_list)
    else:
        raise ValueError(f"Unknown aggregation: {aggregation}")


class ConditionalMultiQuestionRule(BaseMultiQuestionRule):
    type: Literal["CONDITIONAL"] = "CONDITIONAL"
    question_types: frozenset[QuestionType] = frozenset(
        {"TEXT", "CHOICE", "NUMERIC", "MULTI_VALUED"}
    )
    if_rules: list["SingleTargetQuestionRule"] = Field(
        ..., min_length=1, description="List of rules to evaluate the 'if' condition"
    )
    if_aggregation: BooleanAggregation = Field(
        default="AND",
        description=(
            "Aggregation mode for 'if' rules: "
            "'AND' requires all to be true, "
            "'OR' requires at least one to be true"
        ),
    )
    then_rules: list["SingleTargetQuestionRule"] = Field(
        ...,
        min_length=1,
        description="List of rules to evaluate if 'if' condition is met",
    )
    else_rules: list["SingleTargetQuestionRule"] = Field(
        ..., description="List of rules to evaluate if 'if' condition is not met"
    )

    def validate_compatibility(
        self, question_map: dict[QuestionId, Question]
    ) -> list[RuleValidationError]:
        return [
            error
            for rule in self.if_rules + self.then_rules + self.else_rules
            for error in rule.validate_compatibility(question_map)
        ]

    def validate_questions_exist(self, question_ids: set[QuestionId]) -> list[RuleValidationError]:
        return [
            error
            for rule in self.if_rules + self.then_rules + self.else_rules
            for error in rule.validate_questions_exist(question_ids)
        ]

    def validate_unique_target_questions(self) -> list[RuleValidationError]:
        errors: list[RuleValidationError] = []
        # Validate uniqueness within each set of rules, but not across sets
        for rules in [self.then_rules, self.else_rules]:
            errors.extend(validate_unique_target_questions_in_rules(list(rules)))
        return errors

    def get_target_question_ids(self) -> set[QuestionId]:
        return {
            qid
            for rule in self.then_rules
            + self.else_rules  # if rules do not target questions for grading
            for qid in rule.get_target_question_ids()
        }

    def process_submission(
        self, answer_map: dict[QuestionId, Answer], max_points_map: dict[QuestionId, float]
    ) -> dict[QuestionId, QuestionResult]:
        if_results = [
            rule.process_submission(answer_map, max_points_map)[rule.question_id]
            for rule in self.if_rules
        ]
        condition_met = check_condition(if_results, self.if_aggregation)
        active_rules = self.then_rules if condition_met else self.else_rules
        if_question_ids = {rule.question_id for rule in self.if_rules}
        results: dict[QuestionId, QuestionResult] = {}
        for rule in active_rules:
            qid = rule.question_id
            result = rule.process_submission(answer_map, max_points_map)[qid]
            result.feedback = (
                f"[Condition {', '.join(sorted(if_question_ids))}: {condition_met}]"
                f" {result.feedback}"
            )
            results[qid] = result
        return results
