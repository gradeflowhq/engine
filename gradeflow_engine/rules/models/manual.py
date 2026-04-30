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


class ManualRule(BaseRule):
    type: Literal["MANUAL"] = rule_type_field("MANUAL")
    display_name: Literal["Manual"] = rule_display_name_field("Manual")
    question_types: frozenset[QuestionType] = rule_question_types_field(
        {"TEXT", "NUMERIC", "CHOICE", "MULTI_VALUED"}
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def description(self) -> str:
        return "Manual grading required."

    def _process_answer(self, answer: Answer) -> Result:
        return Result(
            output=0,
            passed=False,
            feedback="Manual grading required.",
            rule=self.__class__.__name__,
            graded=False,
        )

    def process_answer(self, answer: Answer) -> Result:  # override validated process_answer
        return self._process_answer(answer)


class ManualQuestionRule(ManualRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result, max_points: float) -> float:
        return 0
