"""Regex rule model definition.

This rule matches a single regex pattern against a text answer. The
`RegexRuleConfig` controls regex flags used during matching.
"""

import re
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from pydantic import BaseModel, Field, field_validator

from gradeflow_engine.types import QuestionType

from ..base import BaseSingleQuestionRule


class RegexRuleConfig(BaseModel):
    dotall: bool = Field(default=False, description="Let '.' match newlines")
    ignore_case: bool = Field(default=False, description="Ignore case when matching")
    multi_line: bool = Field(default=False, description="'^' and '$' match at line boundaries")


if TYPE_CHECKING:
    from gradeflow_engine.schema import QuestionSchema


class RegexRule(BaseSingleQuestionRule):
    """Regex-based grading for text answers using a single pattern."""

    type: Literal["REGEX"] = "REGEX"
    compatible_types: ClassVar[frozenset[QuestionType]] = frozenset({"TEXT"})

    pattern: str = Field(..., description="Regex pattern to match against the student's answer")
    config: RegexRuleConfig = Field(default_factory=RegexRuleConfig)

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v: str, info: Any) -> str:
        """Validate the regex compiles with the configured flags."""
        cfg: RegexRuleConfig | dict[str, object] = info.data.get("config", {})
        # cfg might be a dict during validation; normalize
        if isinstance(cfg, dict):
            cfg = RegexRuleConfig.model_validate(cfg)

        flags = 0
        if cfg.ignore_case:
            flags |= re.IGNORECASE
        if cfg.multi_line:
            flags |= re.MULTILINE
        if cfg.dotall:
            flags |= re.DOTALL

        try:
            re.compile(v, flags=flags)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}") from e
        return v

    def validate_against_schema(
        self, question_id: str, schema: "QuestionSchema", rule_description: str
    ) -> list[str]:
        """Validate this rule against a question schema."""
        from gradeflow_engine.rules.utils import validate_type_compatibility

        return validate_type_compatibility(
            schema=schema,
            compatible_types=self.compatible_types,
            rule_description=rule_description,
            rule_name="RegexRule",
        )
