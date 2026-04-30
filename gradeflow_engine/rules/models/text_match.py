from typing import Literal

from pydantic import Field, computed_field

from ...questions.types import Answer, QuestionType
from ..result import Result
from .base import (
    BaseRule,
    BaseSingleQuestionRule,
    rule_display_name_field,
    rule_question_types_field,
    rule_type_field,
)


class TextMatchRule(BaseRule):
    type: Literal["TEXT_MATCH"] = rule_type_field("TEXT_MATCH")
    display_name: Literal["Text Match"] = rule_display_name_field("Text Match")
    question_types: frozenset[QuestionType] = rule_question_types_field({"TEXT", "NUMERIC"})
    answers: list[str] = Field(..., min_length=1, description="List of acceptable exact answers")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def description(self) -> str:
        return f"Match one of these answers: {', '.join(self.answers)}."

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


class TextMatchQuestionRule(TextMatchRule, BaseSingleQuestionRule):
    pass
