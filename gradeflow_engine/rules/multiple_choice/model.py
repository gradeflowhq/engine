"""Multiple choice grading rule."""

from typing import TYPE_CHECKING, Literal, cast

from pydantic import Field

from gradeflow_engine.types import QuestionType

from ..base import BaseSingleQuestionRule, QuestionConstraint, TextRuleConfig, preprocess_text

if TYPE_CHECKING:
    from gradeflow_engine.schema import QuestionSchema


class MultipleChoiceRuleConfig(TextRuleConfig):
    """Configuration for multiple-choice rules, including delimiter for splitting answers."""

    delimiter: str = Field(default=",", description="Delimiter used to split multiple answers")


class MultipleChoiceRule(BaseSingleQuestionRule):
    """Rule for grading choice questions using a list of allowed answers and a scoring mode."""

    type: Literal["MULTIPLE_CHOICE"] = "MULTIPLE_CHOICE"

    compatible_types: frozenset[QuestionType] = frozenset({"CHOICE"})
    constraints: frozenset[QuestionConstraint] = frozenset(
        {QuestionConstraint(type="CHOICE", source="options", target="answers")}
    )

    answers: list[str] = Field(
        ..., description="List of valid answer options (case-insensitive)", min_length=1
    )
    mode: Literal["all", "partial"] = Field(
        default="all",
        description="Scoring mode: 'all' (all-or-nothing) or 'partial' (proportional)",
    )

    config: "MultipleChoiceRuleConfig" = Field(default_factory=MultipleChoiceRuleConfig)

    def validate_against_question_schema(
        self, question_map: dict[str, "QuestionSchema"], rule_description: str
    ) -> list[str]:
        from gradeflow_engine.schema import ChoiceQuestionSchema

        errors = super().validate_against_question_schema(question_map, rule_description)

        if errors:
            return errors
        schema = cast(ChoiceQuestionSchema, question_map[self.question_id])
        options_norm = {preprocess_text(opt, self.config) for opt in schema.options}
        for ans in self.answers:
            norm_ans = preprocess_text(ans, self.config)
            if norm_ans not in options_norm:
                errors.append(
                    f"{rule_description}: Answer '{ans}' not in schema options: {schema.options}"
                )

        return errors
