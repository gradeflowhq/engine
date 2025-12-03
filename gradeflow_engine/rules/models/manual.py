from typing import Literal

from ...questions.types import Answer, QuestionType
from ..result import Result
from .base import BaseRule, BaseSingleQuestionRule


class ManualRule(BaseRule):
    type: Literal["MANUAL"] = "MANUAL"
    question_types: frozenset[QuestionType] = frozenset(
        {"TEXT", "NUMERIC", "CHOICE", "MULTI_VALUED"}
    )

    def process_answer(self, answer: Answer) -> Result:  # override validated process_answer
        return Result(
            output=0,
            passed=False,
            feedback="Manual grading required.",
            rule=self.__class__.__name__,
            graded=False,
        )


class ManualQuestionRule(ManualRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result) -> float:
        return 0
