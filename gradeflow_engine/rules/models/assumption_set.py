from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field, TypeAdapter, computed_field

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


def evaluate_assumption(
    question_assumption: MultiQuestionAssumption,
    answer_map: dict[QuestionId, Answer],
    max_points_map: dict[QuestionId, float],
) -> AssumptionResult:
    question_results: list[QuestionResult] = []
    assumption_marker = (
        f"[Assumption: {question_assumption.name}] " if question_assumption.name else ""
    )
    for rule in question_assumption.rules:
        result = rule.process_submission(answer_map, max_points_map)[rule.question_id]
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
    question_types: frozenset[QuestionType] = Field(
        default=frozenset({"TEXT", "CHOICE", "NUMERIC", "MULTI_VALUED"}),
        frozen=True,
        json_schema_extra={"readOnly": True},
    )
    mode: AssumptionSetMode = Field("MAX", description="Mode to select which assumption to use")


class AssumptionSetQuestionRule(AssumptionSetBaseRule, BaseSingleQuestionRule):
    type: Literal["ASSUMPTION_SET"] = Field(
        default="ASSUMPTION_SET", frozen=True, json_schema_extra={"readOnly": True}
    )
    name: Literal["Assumption Set"] = Field(
        default="Assumption Set", frozen=True, json_schema_extra={"readOnly": True}
    )
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


class AssumptionSetMultiQuestionRule(AssumptionSetBaseRule, BaseMultiQuestionRule):
    type: Literal["ASSUMPTION_SET_MULTI"] = Field(
        default="ASSUMPTION_SET_MULTI", frozen=True, json_schema_extra={"readOnly": True}
    )
    name: Literal["Assumption Set"] = Field(
        default="Assumption Set", frozen=True, json_schema_extra={"readOnly": True}
    )
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
