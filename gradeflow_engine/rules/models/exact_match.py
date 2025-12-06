from typing import Literal

from pydantic import Field

from ...questions.types import Answer, QuestionType
from ..result import Result
from .base import BaseRule, BaseSingleQuestionRule


class ExactMatchRule(BaseRule):
    type: Literal["EXACT_MATCH"] = "EXACT_MATCH"
    question_types: frozenset[QuestionType] = frozenset({"TEXT", "NUMERIC"})
    answers: list[str] = Field(..., min_length=1, description="List of acceptable exact answers")

    def _process_answer(self, answer: Answer) -> Result:
        answer_str = str(answer)
        is_match = any(answer_str == str(correct_answer) for correct_answer in self.answers)
        feedback = (
            f"{answer_str} "
            + ("matches one" if is_match else "does not match any")
            + f" of the correct answers: {', '.join(self.answers)}."
        )
        return Result(
            output=is_match,
            passed=is_match,
            feedback=feedback,
            rule=self.__class__.__name__,
        )


class ExactMatchQuestionRule(ExactMatchRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result) -> float:
        return self.max_points if result.passed else 0.0
