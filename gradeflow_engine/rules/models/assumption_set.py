from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field, TypeAdapter

from ...questions.models import Question
from ...questions.types import Answer, QuestionId, QuestionType
from ..result import QuestionResult
from ..types import RuleValidationError
from ..validators import validate_unique_target_questions_in_rules
from .base import BaseMultiQuestionRule, BaseRule, BaseSingleQuestionRule

if TYPE_CHECKING:
    from . import SingleTargetQuestionRule, SingleTargetRule


AssumptionSetMode = Literal["MAX", "MIN"]


def _convert_rule_to_question_rule(
    rule: "SingleTargetRule", question_id: QuestionId, max_points: float
) -> "SingleTargetQuestionRule":
    """Convert a SingleTargetRule to its corresponding SingleTargetQuestionRule variant."""
    from . import SingleTargetQuestionRule

    # Get all the rule's fields and add the question_id
    rule_data = rule.model_dump()
    rule_data["question_id"] = question_id
    rule_data["max_points"] = max_points

    # Use Pydantic's discriminated union to parse into the correct QuestionRule type
    adapter: TypeAdapter[SingleTargetQuestionRule] = TypeAdapter(SingleTargetQuestionRule)
    return adapter.validate_python(rule_data)


class BaseAssumption(BaseModel):
    name: str | None = Field(default=None, description="Name of the assumption")
    weight: float = Field(default=1.0, le=1.0, ge=0.0, description="Weight of the assumption")


class Assumption(BaseAssumption):
    rule: "SingleTargetRule" = Field(..., description="Rule that defines the assumption")


class MultiQuestionAssumption(BaseAssumption):
    rules: list["SingleTargetQuestionRule"] = Field(
        ..., description="List of rules that define the assumption"
    )


@dataclass(frozen=True)
class AssumptionResult:
    assumption: MultiQuestionAssumption
    question_results: list[QuestionResult]


def evaluate_assumption(
    question_assumption: MultiQuestionAssumption, answer_map: dict[QuestionId, Answer]
) -> AssumptionResult:
    question_results: list[QuestionResult] = []
    assumption_marker = (
        f"[Assumption: {question_assumption.name}] " if question_assumption.name else ""
    )
    for rule in question_assumption.rules:
        result = rule.process_submission(answer_map)
        result.feedback = f"{assumption_marker}{result.feedback}"
        result.points *= question_assumption.weight
        question_results.append(result)
    return AssumptionResult(assumption=question_assumption, question_results=question_results)


def choose_assumption_result(
    assumption_results: list[AssumptionResult],
    mode: AssumptionSetMode,
) -> AssumptionResult:
    aggr_fn = max if mode == "MAX" else min
    assumption_result = aggr_fn(
        assumption_results,
        key=lambda assumption_result: sum(
            question_result.points for question_result in assumption_result.question_results
        ),
    )
    return assumption_result


class AssumptionSetBaseRule(BaseRule):
    question_types: frozenset[QuestionType] = frozenset(
        {"TEXT", "CHOICE", "NUMERIC", "MULTI_VALUED"}
    )
    mode: AssumptionSetMode = Field("MAX", description="Mode to select which assumption to use")


class AssumptionSetQuestionRule(AssumptionSetBaseRule, BaseSingleQuestionRule):
    type: Literal["ASSUMPTION_SET"] = "ASSUMPTION_SET"
    assumptions: list[Assumption] = Field(
        ..., description="List of assumptions in the assumption set"
    )

    def model_post_init(self, _context: Any) -> None:
        self._rule = AssumptionSetMultiQuestionRule(
            assumptions=[
                MultiQuestionAssumption(
                    name=assumption.name,
                    weight=assumption.weight,
                    rules=[
                        _convert_rule_to_question_rule(
                            assumption.rule, self.question_id, self.max_points
                        )
                    ],
                )
                for assumption in self.assumptions
            ],
            mode=self.mode,
        )

    def validate_compatibility(
        self, question_map: dict[QuestionId, Question]
    ) -> list[RuleValidationError]:
        return self._rule.validate_compatibility(question_map)

    def process_submission(self, answer_map: dict[QuestionId, Answer]) -> QuestionResult:
        multi_question_result = self._rule.process_submission(answer_map)
        # There should be only one question result since this is a single question rule
        return multi_question_result[0]


class AssumptionSetMultiQuestionRule(AssumptionSetBaseRule, BaseMultiQuestionRule):
    type: Literal["ASSUMPTION_SET_MULTI"] = "ASSUMPTION_SET_MULTI"
    assumptions: list[MultiQuestionAssumption] = Field(
        ..., description="List of assumptions in the assumption set"
    )

    def validate_compatibility(
        self, question_map: dict[QuestionId, Question]
    ) -> list[RuleValidationError]:
        return [
            error
            for assumption in self.assumptions
            for rule in assumption.rules
            for error in rule.validate_compatibility(question_map)
        ]

    def validate_questions_exist(self, question_ids: set[QuestionId]) -> list[RuleValidationError]:
        return [
            error
            for assumption in self.assumptions
            for rule in assumption.rules
            for error in rule.validate_questions_exist(question_ids)
        ]

    def validate_unique_target_questions(self) -> list[RuleValidationError]:
        errors: list[RuleValidationError] = []
        # Validate uniqueness within each assumption, but not across assumptions
        for assumption in self.assumptions:
            errors.extend(validate_unique_target_questions_in_rules(list(assumption.rules)))
        return errors

    def get_target_question_ids(self) -> set[QuestionId]:
        return {
            qid
            for assumption in self.assumptions
            for rule in assumption.rules
            for qid in rule.get_target_question_ids()
        }

    def process_submission(self, answer_map: dict[QuestionId, Answer]) -> list[QuestionResult]:
        results: list[AssumptionResult] = [
            evaluate_assumption(assumption, answer_map) for assumption in self.assumptions
        ]
        chosen_assumption_result = choose_assumption_result(results, self.mode)
        return chosen_assumption_result.question_results
