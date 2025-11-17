from typing import Literal

from pydantic import Field

from ...questions.types import Answer, QuestionType
from ..result import Result
from .base import BaseRule, BaseSingleQuestionRule


class ExactMatchRule(BaseRule):
    type: Literal["EXACT_MATCH"] = "EXACT_MATCH"
    question_types: frozenset[QuestionType] = frozenset({"TEXT", "NUMERIC"})
    answer: str = Field(..., description="Expected exact answer")

    def _process_answer(self, answer: Answer) -> Result:
        is_match = str(answer) == str(self.answer)

        return Result(
            output=is_match,
            passed=is_match,
            feedback=(
                f"The answer ({answer}) {'matches' if is_match else 'does not match'} "
                f"the correct answer ({self.answer})."
            ),
            rule=self.__class__.__name__,
        )


class ExactMatchQuestionRule(ExactMatchRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result) -> float:
        return self.max_points if result.passed else 0.0
