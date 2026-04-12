from typing import Literal

from pydantic import BaseModel, Field, computed_field

from ...questions.types import Answer, QuestionType
from ..result import Result
from .base import BaseRule, BaseSingleQuestionRule

NonEmptyNumeric = int | float


def is_equal_fn(
    answer: NonEmptyNumeric,
    correct_answers: list[NonEmptyNumeric],
    approximate: bool,
    tolerance: float,
) -> bool:
    for correct in correct_answers:
        if approximate:
            if abs(answer - correct) <= tolerance:
                return True
        else:
            if answer == correct:
                return True
    return False


def feedback_fn(
    answer: NonEmptyNumeric,
    correct_answers: list[NonEmptyNumeric],
    is_equal: bool,
    approximate: bool,
    tolerance: float,
) -> str:
    correct_str = ", ".join(str(c) for c in correct_answers)
    if is_equal:
        return (
            f"{answer} is {'approximately ' if approximate else ''}correct"
            + (f" (within tolerance of {tolerance})" if approximate else "")
            + "."
        )
    else:
        return (
            "Incorrect answer. "
            + f"The correct answers are{' approximately' if approximate else ''}: {correct_str}."
            + (f" (within a tolerance of {tolerance})" if approximate else "")
        )


class NumberEqualConfig(BaseModel):
    approximate: bool = Field(
        default=True, description="Whether to allow approximate matches within a tolerance"
    )
    tolerance: float = Field(
        default=1e-6,
        description="Tolerance for approximate equality checks (if approximate is True)",
    )


class NumberEqualRule(BaseRule):
    type: Literal["NUMBER_EQUAL"] = Field(
        default="NUMBER_EQUAL", frozen=True, json_schema_extra={"readOnly": True}
    )
    display_name: Literal["Number Equal"] = Field(
        default="Number Equal", frozen=True, json_schema_extra={"readOnly": True}
    )
    question_types: frozenset[QuestionType] = Field(
        default=frozenset({"NUMERIC"}), frozen=True, json_schema_extra={"readOnly": True}
    )
    answers: list[int | float] = Field(
        ..., min_length=1, description="List of acceptable numeric answers"
    )
    config: NumberEqualConfig = Field(
        default_factory=NumberEqualConfig,
        description="Configuration for numeric equality checks",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def description(self) -> str:
        if self.config.approximate:
            return (
                f"Approximately equal to: "
                f"{', '.join(str(ans) for ans in self.answers)} "
                f"within a tolerance of {self.config.tolerance}."
            )
        else:
            return f"Equal to: {', '.join(str(ans) for ans in self.answers)}."

    def _process_answer(self, answer: Answer) -> Result:
        assert isinstance(answer, NonEmptyNumeric), "Answer must be numeric"
        is_equal = is_equal_fn(
            answer=answer,
            correct_answers=self.answers,
            approximate=self.config.approximate,
            tolerance=self.config.tolerance,
        )
        feedback = feedback_fn(
            answer=answer,
            correct_answers=self.answers,
            is_equal=is_equal,
            approximate=self.config.approximate,
            tolerance=self.config.tolerance,
        )
        return Result(
            output=is_equal,
            passed=is_equal,
            feedback=feedback,
            rule=self.__class__.__name__,
        )


class NumberEqualQuestionRule(NumberEqualRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result, max_points: float) -> float:
        return max_points if result.passed else 0.0
