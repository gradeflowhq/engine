from typing import Literal

from pydantic import Field

from ...questions.types import Answer, QuestionType
from ..result import Result
from .base import BaseRule, BaseSingleQuestionRule


class NumericRangeRule(BaseRule):
    type: Literal["NUMERIC_RANGE"] = "NUMERIC_RANGE"
    question_types: frozenset[QuestionType] = frozenset({"NUMERIC"})
    min_value: float | None = Field(default=None, description="Minimum acceptable value")
    max_value: float | None = Field(default=None, description="Maximum acceptable value")

    def _process_answer(self, answer: Answer) -> Result:
        assert isinstance(answer, (int, float)), "Answer must be numeric for NumericRangeRule."

        passed = True
        feedback = f"The answer is {answer}."
        if self.min_value is not None and float(answer) < self.min_value:
            passed = False
            feedback += f" It is less than the minimum value of {self.min_value}."
        if self.max_value is not None and float(answer) > self.max_value:
            passed = False
            feedback += f" It is greater than the maximum value of {self.max_value}."

        return Result(
            output=passed,
            passed=passed,
            feedback=feedback,
            rule=self.__class__.__name__,
        )


class NumericRangeQuestionRule(NumericRangeRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result) -> float:
        return self.max_points if result.passed else 0.0
