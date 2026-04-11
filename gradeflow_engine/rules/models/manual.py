from typing import Literal

from pydantic import Field, computed_field

from ...questions.types import Answer, QuestionType
from ..result import Result
from .base import BaseRule, BaseSingleQuestionRule


class ManualRule(BaseRule):
    type: Literal["MANUAL"] = Field(
        default="MANUAL", frozen=True, json_schema_extra={"readOnly": True}
    )
    name: Literal["Manual"] = Field(
        default="Manual", frozen=True, json_schema_extra={"readOnly": True}
    )
    question_types: frozenset[QuestionType] = Field(
        default=frozenset({"TEXT", "NUMERIC", "CHOICE", "MULTI_VALUED"}),
        frozen=True,
        json_schema_extra={"readOnly": True},
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def description(self) -> str:
        return "Manual grading required."

    def process_answer(self, answer: Answer) -> Result:  # override validated process_answer
        return Result(
            output=0,
            passed=False,
            feedback="Manual grading required.",
            rule=self.__class__.__name__,
            graded=False,
        )


class ManualQuestionRule(ManualRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result, max_points: float) -> float:
        return 0
