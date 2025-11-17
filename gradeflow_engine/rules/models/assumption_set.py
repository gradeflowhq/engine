from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from ...questions.models import Question
from ...questions.types import Answer, QuestionId, QuestionType
from ..result import QuestionResult
from ..types import RuleValidationError
from ..validators import validate_unique_target_questions_in_rules
from .base import BaseMultiQuestionRule

if TYPE_CHECKING:
    from . import SingleTargetQuestionRule


AssumptionSetMode = Literal["MAX", "MIN"]


class Assumption(BaseModel):
    name: str = Field(..., description="Name of the assumption")
    rules: list[SingleTargetQuestionRule] = Field(
        ..., description="List of rules that define the assumption"
    )


@dataclass(frozen=True)
class AssumptionResult:
    assumption: Assumption
    question_results: list[QuestionResult]


def evaluate_assumption(
    assumption: Assumption, answer_map: dict[QuestionId, Answer]
) -> AssumptionResult:
    question_results: list[QuestionResult] = []
    for rule in assumption.rules:
        result = rule.process_submission(answer_map)
        question_results.append(result)
    return AssumptionResult(assumption=assumption, question_results=question_results)


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


class AssumptionSetMultiQuestionRule(BaseMultiQuestionRule):
    type: Literal["ASSUMPTION_SET"] = "ASSUMPTION_SET"
    question_types: frozenset[QuestionType] = frozenset({"TEXT", "NUMERIC"})
    assumptions: list[Assumption] = Field(
        ..., description="List of assumptions in the assumption set"
    )
    mode: AssumptionSetMode = Field("MAX", description="Mode to select which assumption to use")

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
        return validate_unique_target_questions_in_rules(
            [rule for assumption in self.assumptions for rule in assumption.rules]
        )

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
