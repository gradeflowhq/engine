from typing import Literal

from ...questions.types import Answer, QuestionType
from ..result import Result
from .base import BaseRule, BaseSingleQuestionRule


class BonusRule(BaseRule):
    type: Literal["BONUS"] = "BONUS"
    question_types: frozenset[QuestionType] = frozenset(
        {"TEXT", "NUMERIC", "CHOICE", "MULTI_VALUED"}
    )

    def process_answer(self, answer: Answer) -> Result:  # override validated process_answer
        return Result(
            output=1,
            passed=True,
            feedback="Bonus points awarded.",
            rule=self.__class__.__name__,
        )


class BonusQuestionRule(BonusRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result) -> float:
        return self.max_points
