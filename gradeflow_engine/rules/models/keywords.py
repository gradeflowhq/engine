import re
from collections import Counter
from collections.abc import Iterable
from typing import TYPE_CHECKING, Literal, cast

from pydantic import Field, computed_field
from pydantic.fields import FieldInfo

from ...questions.types import Answer, QuestionType
from ..aggregations.completeness import output_fn, passed_fn, points_fn
from ..markdown import markdown_join
from ..result import Result
from ..schema import STRING_LIST_INPUT, gradeflow_schema_extra
from ..types import CompletenessAggregation
from .base import (
    BaseRule,
    BaseSingleQuestionRule,
    rule_display_name_field,
    rule_question_types_field,
    rule_type_field,
)

if TYPE_CHECKING:
    from ..context import RuleContext


def _keyword_suggestions(answers: Iterable[str]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for answer in answers:
        counts.update(set(re.findall(r"\w+", answer)))
    return dict(counts)


class KeywordsRule(BaseRule):
    type: Literal["KEYWORDS"] = rule_type_field("KEYWORDS")
    display_name: Literal["Keywords"] = rule_display_name_field("Keywords")
    question_types: frozenset[QuestionType] = rule_question_types_field({"TEXT"})
    keywords: list[str] = Field(
        ...,
        min_length=1,
        description="List of keywords that must be present in the answer",
    )
    mode: CompletenessAggregation = Field(
        default="ALL",
        description=(
            "Mode of keyword matching: "
            "'ALL' requires all keywords to be present, "
            "'ANY' requires at least one."
            "'PARTIAL' gives credit for each keyword present."
        ),
    )

    @classmethod
    def field_overrides(
        cls,
        context: "RuleContext",
    ) -> dict[str, tuple[object, FieldInfo]]:
        overrides = super().field_overrides(context)
        return {
            **overrides,
            "keywords": (
                list[str],
                cast(
                    FieldInfo,
                    Field(
                        ...,
                        min_length=1,
                        description="List of keywords that must be present in the answer",
                        json_schema_extra=gradeflow_schema_extra(
                            STRING_LIST_INPUT,
                            suggestions=_keyword_suggestions(context.answer_values()),
                        ),
                    ),
                ),
            ),
        }

    @computed_field  # type: ignore[prop-decorator]
    @property
    def description(self) -> str:
        if self.mode == "ALL":
            return (
                f"Contain all of these keywords: {markdown_join(self.keywords, conjunction='and')}."
            )
        elif self.mode == "ANY":
            return (
                "Contain at least one of these keywords: "
                f"{markdown_join(self.keywords, conjunction='or')}."
            )
        elif self.mode == "PARTIAL":
            return (
                f"Partial credit for keywords: {markdown_join(self.keywords, conjunction='and')}."
            )
        else:
            raise ValueError(f"Unknown mode: {self.mode}")

    def _process_answer(self, answer: Answer) -> Result:
        matches = [keyword in str(answer) for keyword in self.keywords]
        output = output_fn(matches, mode=self.mode)
        passed = passed_fn(matches, mode=self.mode)
        feedback = f'"{answer}" ' + (
            f"contains all keywords: {', '.join(self.keywords)}."
            if passed
            else f"does not contain {self.mode.lower()} keywords: {', '.join(self.keywords)}."
        )
        return Result(
            output=output,
            passed=passed,
            feedback=feedback,
            rule=self.display_name,
        )


class KeywordsQuestionRule(KeywordsRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result, max_points: float) -> float:
        return points_fn(result, mode=self.mode, max_points=max_points)
