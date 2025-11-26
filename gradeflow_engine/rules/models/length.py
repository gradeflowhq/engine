from typing import Literal

from pydantic import Field

from ...questions.types import Answer, QuestionType
from ..result import Result
from .base import BaseRule, BaseSingleQuestionRule


class LengthRule(BaseRule):
    type: Literal["LENGTH"] = "LENGTH"
    question_types: frozenset[QuestionType] = frozenset({"TEXT"})
    min_length: int | None = Field(default=None, description="Minimum length of the answer")
    max_length: int | None = Field(default=None, description="Maximum length of the answer")
    mode: Literal["words", "characters"] = Field(
        default="characters", description="Mode of length measurement"
    )

    def _process_answer(self, answer: Answer) -> Result:
        answer_length = len(str(answer).split(" ")) if self.mode == "words" else len(str(answer))
        passed = True
        feedback = f"The answer length is {answer_length} {self.mode}."
        if self.min_length is not None and answer_length < self.min_length:
            passed = False
            feedback += f" It is shorter than the minimum length of {self.min_length} {self.mode}."
        if self.max_length is not None and answer_length > self.max_length:
            passed = False
            feedback += f" It is longer than the maximum length of {self.max_length} {self.mode}."

        return Result(
            output=passed,
            passed=passed,
            feedback=feedback,
            rule=self.__class__.__name__,
        )


class LengthQuestionRule(LengthRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result) -> float:
        return self.max_points if result.passed else 0.0
