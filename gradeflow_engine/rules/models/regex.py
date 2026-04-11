import re
from functools import lru_cache
from re import Pattern
from typing import Literal

from pydantic import BaseModel, Field, computed_field

from ...questions.types import Answer, QuestionType
from ..result import Result
from .base import BaseRule, BaseSingleQuestionRule


@lru_cache(maxsize=256)
def _compile_regex(pattern: str, flags: int) -> Pattern[str]:
    return re.compile(pattern, flags)


def _build_regex_flags(ignore_case: bool, multi_line: bool, dotall: bool) -> int:
    flags = 0
    if ignore_case:
        flags |= re.IGNORECASE
    if multi_line:
        flags |= re.MULTILINE
    if dotall:
        flags |= re.DOTALL
    return flags


class RegexConfig(BaseModel):
    ignore_case: bool = Field(default=False, description="Ignore case when matching")
    multi_line: bool = Field(default=False, description="Multi-line matching")
    dotall: bool = Field(default=False, description="Dot matches all characters including newlines")


class RegexRule(BaseRule):
    type: Literal["REGEX"] = Field(
        default="REGEX", frozen=True, json_schema_extra={"readOnly": True}
    )
    name: Literal["Regex"] = Field(
        default="Regex", frozen=True, json_schema_extra={"readOnly": True}
    )
    question_types: frozenset[QuestionType] = Field(
        default=frozenset({"TEXT"}), frozen=True, json_schema_extra={"readOnly": True}
    )
    pattern: str = Field(..., description="Regular expression pattern to match against the answer")
    config: RegexConfig = Field(
        default_factory=RegexConfig,
        description="Configuration for regex matching behavior",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def description(self) -> str:
        config_desc: list[str] = []
        if self.config.ignore_case:
            config_desc.append("ignoring case")
        if self.config.multi_line:
            config_desc.append("multi-line mode")
        if self.config.dotall:
            config_desc.append("dot matches newlines")
        config_str = ", ".join(config_desc) if config_desc else "default regex behavior"
        return f"Match the regex pattern: {self.pattern} ({config_str})."

    def _process_answer(self, answer: Answer) -> Result:
        flags = _build_regex_flags(
            ignore_case=self.config.ignore_case,
            multi_line=self.config.multi_line,
            dotall=self.config.dotall,
        )
        compiled_pattern = _compile_regex(self.pattern, flags)
        is_match = compiled_pattern.search(str(answer)) is not None

        return Result(
            output=is_match,
            passed=is_match,
            feedback=(
                f'"{answer}" {"matches" if is_match else "does not match"} '
                f"the pattern: {self.pattern}."
            ),
            rule=self.__class__.__name__,
        )


class RegexQuestionRule(RegexRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result, max_points: float) -> float:
        return max_points if result.passed else 0.0
