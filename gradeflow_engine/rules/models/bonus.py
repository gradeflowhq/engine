from typing import Literal

from pydantic import Field, computed_field

from ...questions.types import Answer, QuestionType
from ..result import Result
from .base import BaseRule, BaseSingleQuestionRule


class BonusRule(BaseRule):
    type: Literal["BONUS"] = Field(
        default="BONUS", frozen=True, json_schema_extra={"readOnly": True}
    )
    display_name: Literal["Bonus"] = Field(
        default="Bonus", frozen=True, json_schema_extra={"readOnly": True}
    )
    question_types: frozenset[QuestionType] = Field(
        default=frozenset({"TEXT", "NUMERIC", "CHOICE", "MULTI_VALUED"}),
        frozen=True,
        json_schema_extra={"readOnly": True},
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def description(self) -> str:
        return "Bonus (anything is correct)."

    def process_answer(self, answer: Answer) -> Result:  # override validated process_answer
        return Result(
            output=1,
            passed=True,
            feedback="Bonus points awarded.",
            rule=self.__class__.__name__,
        )


class BonusQuestionRule(BonusRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result, max_points: float) -> float:
        return max_points
