from typing import Literal

from pydantic import Field, computed_field

from ...questions.types import Answer, QuestionType
from ..markdown import markdown_code
from ..result import Result
from .base import (
    BaseRule,
    BaseSingleQuestionRule,
    rule_display_name_field,
    rule_question_types_field,
    rule_type_field,
)


class LengthRule(BaseRule):
    type: Literal["LENGTH"] = rule_type_field("LENGTH")
    display_name: Literal["Length"] = rule_display_name_field("Length")
    question_types: frozenset[QuestionType] = rule_question_types_field({"TEXT"})
    min_length: int | None = Field(default=None, description="Minimum length of the answer")
    max_length: int | None = Field(default=None, description="Maximum length of the answer")
    mode: Literal["words", "characters"] = Field(
        default="characters", description="Mode of length measurement"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def description(self) -> str:
        length_desc = "characters" if self.mode == "characters" else "words"
        if self.min_length is not None and self.max_length is not None:
            return (
                f"Between {markdown_code(self.min_length)} and "
                f"{markdown_code(self.max_length)} {length_desc}."
            )
        elif self.min_length is not None:
            return f"At least {markdown_code(self.min_length)} {length_desc}."
        elif self.max_length is not None:
            return f"At most {markdown_code(self.max_length)} {length_desc}."
        else:
            return "No length constraints."

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
            rule=self.display_name,
        )


class LengthQuestionRule(LengthRule, BaseSingleQuestionRule):
    pass
