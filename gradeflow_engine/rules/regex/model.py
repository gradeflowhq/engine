"""Regex rule model definition."""

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, field_validator

from gradeflow_engine.types import QuestionType

if TYPE_CHECKING:
    from gradeflow_engine.schema import QuestionSchema


class RegexRule(BaseModel):
    """
    Regex-based grading: award points based on regex pattern matches.

    Can specify multiple patterns with different point values and matching modes.
    """

    type: Literal["REGEX"] = "REGEX"
    compatible_types: set[QuestionType] = {"TEXT"}
    question_id: str = Field(description="Question ID to grade")
    patterns: list[str] = Field(description="List of regex patterns to match", min_length=1)
    points_per_match: float | list[float] = Field(
        description="Points per pattern match (single value or list matching patterns)"
    )
    match_mode: Literal["all", "any", "count"] = Field(
        default="all",
        description=(
            "all: all patterns must match for full points; "
            "any: any pattern match awards points; "
            "count: award points based on number of matches"
        ),
    )
    case_sensitive: bool = Field(
        default=True, description="Whether regex matching is case-sensitive"
    )
    multiline: bool = Field(default=False, description="Enable multiline mode for regex")
    dotall: bool = Field(default=False, description="Enable dotall mode (. matches newlines)")
    partial_credit: bool = Field(
        default=True, description="Award partial credit for partial matches (match_mode='all')"
    )
    description: str | None = Field(None, description="Human-readable description of the rule")

    @field_validator("points_per_match")
    @classmethod
    def validate_points(cls, v, info):
        if isinstance(v, list):
            patterns = info.data.get("patterns", [])
            if len(v) != len(patterns):
                raise ValueError("points_per_match list must match patterns list length")
            if any(p < 0 for p in v):
                raise ValueError("All points must be >= 0")
        elif v < 0:
            raise ValueError("points_per_match must be >= 0")
        return v

    @property
    def max_points(self) -> float:
        """Calculate maximum possible points."""
        if isinstance(self.points_per_match, list):
            return sum(self.points_per_match)
        else:
            return self.points_per_match * len(self.patterns)

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
