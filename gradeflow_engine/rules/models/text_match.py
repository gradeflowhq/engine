from typing import TYPE_CHECKING, Literal, cast

from pydantic import Field, computed_field
from pydantic.fields import FieldInfo

from ...questions.types import Answer, QuestionType
from ..markdown import markdown_join
from ..result import Result
from ..schema import STRING_LIST_INPUT, gradeflow_schema_extra
from .base import (
    BaseRule,
    BaseSingleQuestionRule,
    rule_display_name_field,
    rule_question_types_field,
    rule_type_field,
)

if TYPE_CHECKING:
    from ..context import RuleContext


class TextMatchRule(BaseRule):
    type: Literal["TEXT_MATCH"] = rule_type_field("TEXT_MATCH")
    display_name: Literal["Text Match"] = rule_display_name_field("Text Match")
    question_types: frozenset[QuestionType] = rule_question_types_field({"TEXT", "NUMERIC"})
    answers: list[str] = Field(..., min_length=1, description="List of acceptable exact answers")

    @classmethod
    def field_overrides(
        cls,
        context: "RuleContext",
    ) -> dict[str, tuple[object, FieldInfo]]:
        overrides = super().field_overrides(context)
        return {
            **overrides,
            "answers": (
                list[str],
                cast(
                    FieldInfo,
                    Field(
                        ...,
                        min_length=1,
                        description="List of acceptable exact answers",
                        json_schema_extra=gradeflow_schema_extra(
                            STRING_LIST_INPUT,
                            suggestions=context.answer_suggestions(),
                        ),
                    ),
                ),
            ),
        }

    @computed_field  # type: ignore[prop-decorator]
    @property
    def description(self) -> str:
        return f"Match one of these answers: {markdown_join(self.answers, conjunction='or')}."

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
            rule=self.display_name,
        )


class TextMatchQuestionRule(TextMatchRule, BaseSingleQuestionRule):
    pass
