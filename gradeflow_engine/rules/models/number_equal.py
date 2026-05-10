from typing import TYPE_CHECKING, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, computed_field
from pydantic.fields import FieldInfo

from ...questions.types import Answer, QuestionType
from ..markdown import markdown_code, markdown_join
from ..result import Result
from ..schema import STRING_LIST_INPUT, gradeflow_schema_extra
from .base import (
    BaseRule,
    BaseSingleQuestionRule,
    rule_display_name_field,
    rule_question_types_field,
    rule_type_field,
)

if TYPE_CHECKING:
    from ..context import RuleContext

NumericValue = int | float


def is_equal_fn(
    answer: NumericValue,
    correct_answers: list[NumericValue],
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
    answer: NumericValue,
    correct_answers: list[NumericValue],
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
    model_config = ConfigDict(title="Number Equal Configuration")

    approximate: bool = Field(
        default=True, description="Whether to allow approximate matches within a tolerance"
    )
    tolerance: float = Field(
        default=1e-6,
        description="Tolerance for approximate equality checks (if approximate is True)",
    )


class NumberEqualRule(BaseRule):
    type: Literal["NUMBER_EQUAL"] = rule_type_field("NUMBER_EQUAL")
    display_name: Literal["Number Equal"] = rule_display_name_field("Number Equal")
    question_types: frozenset[QuestionType] = rule_question_types_field({"NUMERIC"})
    answers: list[int | float] = Field(
        ..., min_length=1, description="List of acceptable numeric answers"
    )
    config: NumberEqualConfig = Field(
        default_factory=NumberEqualConfig,
        description="Configuration for numeric equality checks",
    )

    @classmethod
    def field_overrides(
        cls,
        context: "RuleContext",
    ) -> dict[str, tuple[object, FieldInfo]]:
        overrides = super().field_overrides(context)
        return {
            **overrides,
            "answers": (
                list[str],
                cast(
                    FieldInfo,
                    Field(
                        ...,
                        min_length=1,
                        description="List of acceptable numeric answers",
                        json_schema_extra=gradeflow_schema_extra(
                            STRING_LIST_INPUT,
                            suggestions=context.answer_suggestions(),
                        ),
                    ),
                ),
            ),
        }

    @computed_field  # type: ignore[prop-decorator]
    @property
    def description(self) -> str:
        if self.config.approximate:
            return (
                f"Approximately equal to: "
                f"{markdown_join(self.answers, conjunction='or')} "
                f"within a tolerance of {markdown_code(self.config.tolerance)}."
            )
        else:
            return f"Equal to: {markdown_join(self.answers, conjunction='or')}."

    def _process_answer(self, answer: Answer) -> Result:
        if not isinstance(answer, (int, float)) or isinstance(answer, bool):
            raise TypeError("Answer must be numeric")
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
            rule=self.display_name,
        )


class NumberEqualQuestionRule(NumberEqualRule, BaseSingleQuestionRule):
    pass
