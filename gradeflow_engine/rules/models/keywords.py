from typing import Literal

from pydantic import Field, computed_field

from ...questions.types import Answer, QuestionType
from ..aggregations.completeness import output_fn, passed_fn, points_fn
from ..result import Result
from ..types import CompletenessAggregation
from .base import BaseRule, BaseSingleQuestionRule


class KeywordsRule(BaseRule):
    type: Literal["KEYWORDS"] = Field(
        default="KEYWORDS", frozen=True, json_schema_extra={"readOnly": True}
    )
    display_name: Literal["Keywords"] = Field(
        default="Keywords", frozen=True, json_schema_extra={"readOnly": True}
    )
    question_types: frozenset[QuestionType] = Field(
        default=frozenset({"TEXT"}), frozen=True, json_schema_extra={"readOnly": True}
    )
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

    @computed_field  # type: ignore[prop-decorator]
    @property
    def description(self) -> str:
        if self.mode == "ALL":
            return f"Contain all of the these keywords: {', '.join(self.keywords)}."
        elif self.mode == "ANY":
            return f"Contain at least one of these keywords: {', '.join(self.keywords)}."
        elif self.mode == "PARTIAL":
            return f"Partial credit for keywords: {', '.join(self.keywords)}."
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
            rule=self.__class__.__name__,
        )


class KeywordsQuestionRule(KeywordsRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result, max_points: float) -> float:
        return points_fn(result, mode=self.mode, max_points=max_points)
