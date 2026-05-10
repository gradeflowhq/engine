import re
from functools import lru_cache
from re import Pattern
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

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
    model_config = ConfigDict(title="Regex Configuration")

    ignore_case: bool = Field(default=False, description="Ignore case when matching")
    multi_line: bool = Field(default=False, description="Multi-line matching")
    dotall: bool = Field(default=False, description="Dot matches all characters including newlines")


class RegexRule(BaseRule):
    type: Literal["REGEX"] = rule_type_field("REGEX")
    display_name: Literal["Regex"] = rule_display_name_field("Regex")
    question_types: frozenset[QuestionType] = rule_question_types_field({"TEXT"})
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
        return f"Match the regex pattern: {markdown_code(self.pattern)} ({config_str})."

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
            rule=self.display_name,
        )


class RegexQuestionRule(RegexRule, BaseSingleQuestionRule):
    pass
