from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field, TypeAdapter, computed_field
from rapidfuzz.distance import JaroWinkler

from ...questions.models import Question
from ...questions.types import Answer, QuestionId, QuestionType
from ..result import QuestionResult, Result
from ..types import RuleValidationError
from ..validators import validate_unique_target_questions_in_rules
from .base import (
    BaseMultiQuestionRule,
    BaseRule,
    BaseSingleQuestionRule,
    rule_display_name_field,
    rule_question_types_field,
    rule_type_field,
)

if TYPE_CHECKING:
    from . import SingleTargetQuestionRule, SingleTargetRule


AssumptionSetMode = Literal["MAX", "MIN"]


def _convert_rule_to_question_rule(
    rule: "SingleTargetRule", question_id: QuestionId
) -> "SingleTargetQuestionRule":
    """Convert a SingleTargetRule to its corresponding SingleTargetQuestionRule variant."""
    from . import SingleTargetQuestionRule

    # Get all the rule's fields and add the question_id
    rule_data = rule.model_dump()
    rule_data["question_id"] = question_id

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
    answer_similarity: float = 0


def text_similarity(a: str, b: str) -> float:
    return JaroWinkler.similarity(a, b)


def evaluate_assumption(
    question_assumption: MultiQuestionAssumption,
    answer_map: dict[QuestionId, Answer],
    max_points_map: dict[QuestionId, float],
) -> AssumptionResult:
    question_results: list[QuestionResult] = []
    answer_similarity: float = 0.0
    assumption_marker = (
        f"[Assumption: {question_assumption.name}] " if question_assumption.name else ""
    )
    for rule in question_assumption.rules:
        result = rule.process_submission(answer_map, max_points_map)[rule.question_id]
        result.feedback = f"{assumption_marker}{result.feedback}"
        result.points *= question_assumption.weight
        answer_similarity += text_similarity(rule.description, str(answer_map[rule.question_id]))
        question_results.append(result)
    return AssumptionResult(
        assumption=question_assumption,
        question_results=question_results,
        answer_similarity=answer_similarity,
    )


def choose_assumption_result(
    assumption_results: list[AssumptionResult],
    mode: AssumptionSetMode,
) -> AssumptionResult:
    def key(assumption_result: AssumptionResult) -> tuple[float, float]:
        total_points = sum(
            question_result.points for question_result in assumption_result.question_results
        )
        if mode == "MAX":
            return total_points, assumption_result.answer_similarity
        return total_points, -assumption_result.answer_similarity

    aggr_fn = max if mode == "MAX" else min
    assumption_result = aggr_fn(assumption_results, key=key)
    return assumption_result


class AssumptionSetBaseRule(BaseRule):
    question_types: frozenset[QuestionType] = rule_question_types_field(
        {"TEXT", "CHOICE", "NUMERIC", "MULTI_VALUED"}
    )
    mode: AssumptionSetMode = Field("MAX", description="Mode to select which assumption to use")


class AssumptionSetQuestionRule(AssumptionSetBaseRule, BaseSingleQuestionRule):
    type: Literal["ASSUMPTION_SET"] = rule_type_field("ASSUMPTION_SET")
    display_name: Literal["Assumption Set"] = rule_display_name_field("Assumption Set")
    assumptions: list[Assumption] = Field(
        ..., description="List of assumptions in the assumption set"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def description(self) -> str:
        return "\n\n".join(
            f"Assumption {i + 1} ({assumption.name or 'Unnamed'}):\n{assumption.rule.description}"
            for i, assumption in enumerate(self.assumptions)
        )

    def model_post_init(self, _context: Any) -> None:
        self._rule = AssumptionSetMultiQuestionRule(
            assumptions=[
                MultiQuestionAssumption(
                    name=assumption.name,
                    weight=assumption.weight,
                    rules=[_convert_rule_to_question_rule(assumption.rule, self.question_id)],
                )
                for assumption in self.assumptions
            ],
            mode=self.mode,
        )

    def validate_compatibility(
        self, question_map: dict[QuestionId, Question]
    ) -> list[RuleValidationError]:
        return self._rule.validate_compatibility(question_map)

    def process_submission(
        self, answer_map: dict[QuestionId, Answer], max_points_map: dict[QuestionId, float]
    ) -> dict[QuestionId, QuestionResult]:
        return self._rule.process_submission(answer_map, max_points_map)

    def _process_answer(self, answer: Answer) -> Result:
        raise NotImplementedError("Assumption-set question rules must process full submissions.")

    def compute_points(self, result: Result, max_points: float) -> float:
        raise NotImplementedError("Assumption-set question rules compute points per assumption.")


class AssumptionSetMultiQuestionRule(AssumptionSetBaseRule, BaseMultiQuestionRule):
    type: Literal["ASSUMPTION_SET_MULTI"] = rule_type_field("ASSUMPTION_SET_MULTI")
    display_name: Literal["Assumption Set"] = rule_display_name_field("Assumption Set")
    assumptions: list[MultiQuestionAssumption] = Field(
        ..., description="List of assumptions in the assumption set"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def description(self) -> str:
        return "\n\n".join(
            f"Assumption {i + 1} ({assumption.name or 'Unnamed'}):\n"
            + "\n".join(f"[{rule.question_id}]:\n{rule.description}" for rule in assumption.rules)
            for i, assumption in enumerate(self.assumptions)
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

    def process_submission(
        self, answer_map: dict[QuestionId, Answer], max_points_map: dict[QuestionId, float]
    ) -> dict[QuestionId, QuestionResult]:
        results: list[AssumptionResult] = [
            evaluate_assumption(assumption, answer_map, max_points_map)
            for assumption in self.assumptions
        ]
        chosen_assumption_result = choose_assumption_result(results, self.mode)
        return {
            rule.question_id: result
            for rule, result in zip(
                chosen_assumption_result.assumption.rules,
                chosen_assumption_result.question_results,
                strict=True,
            )
        }
