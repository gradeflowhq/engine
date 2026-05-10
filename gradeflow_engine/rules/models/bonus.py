from typing import Literal

from pydantic import computed_field

from ...questions.types import Answer, QuestionType
from ..result import Result
from .base import (
    BaseRule,
    BaseSingleQuestionRule,
    rule_display_name_field,
    rule_question_types_field,
    rule_type_field,
)


class BonusRule(BaseRule):
    type: Literal["BONUS"] = rule_type_field("BONUS")
    display_name: Literal["Bonus"] = rule_display_name_field("Bonus")
    question_types: frozenset[QuestionType] = rule_question_types_field(
        {"TEXT", "NUMERIC", "CHOICE", "MULTI_VALUED"}
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def description(self) -> str:
        return "**Bonus:** anything is correct."

    def _process_answer(self, answer: Answer) -> Result:
        return Result(
            output=1,
            passed=True,
            feedback="Bonus points awarded.",
            rule=self.display_name,
        )

    def process_answer(self, answer: Answer) -> Result:  # override validated process_answer
        return self._process_answer(answer)


class BonusQuestionRule(BonusRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result, max_points: float) -> float:
        return max_points
