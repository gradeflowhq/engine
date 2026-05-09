from typing import Literal

from pydantic import Field, computed_field

from ...questions.types import Answer, QuestionType
from ..result import Result
from .base import (
    BaseRule,
    BaseSingleQuestionRule,
    rule_display_name_field,
    rule_question_types_field,
    rule_type_field,
)


class NumericRangeRule(BaseRule):
    type: Literal["NUMERIC_RANGE"] = rule_type_field("NUMERIC_RANGE")
    display_name: Literal["Numeric Range"] = rule_display_name_field("Numeric Range")
    question_types: frozenset[QuestionType] = rule_question_types_field({"NUMERIC"})
    min_value: float | None = Field(default=None, description="Minimum acceptable value")
    max_value: float | None = Field(default=None, description="Maximum acceptable value")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def description(self) -> str:
        if self.min_value is not None and self.max_value is not None:
            return f"Between {self.min_value} and {self.max_value}."
        elif self.min_value is not None:
            return f"Greater than or equal to {self.min_value}."
        elif self.max_value is not None:
            return f"Less than or equal to {self.max_value}."
        else:
            return "No numeric range specified."

    def _process_answer(self, answer: Answer) -> Result:
        if not isinstance(answer, (int, float)) or isinstance(answer, bool):
            raise TypeError("Answer must be numeric for NumericRangeRule.")

        passed = True
        feedback = f"{answer}"
        if self.min_value is not None and float(answer) < self.min_value:
            passed = False
            feedback += f" is less than the minimum value of {self.min_value}."
        if self.max_value is not None and float(answer) > self.max_value:
            passed = False
            feedback += f" is greater than the maximum value of {self.max_value}."

        return Result(
            output=passed,
            passed=passed,
            feedback=feedback,
            rule=self.display_name,
        )


class NumericRangeQuestionRule(NumericRangeRule, BaseSingleQuestionRule):
    pass
