"""NumericRange rule model definition."""

from typing import TYPE_CHECKING, Any, Literal

from pydantic import Field, field_validator

from gradeflow_engine.types import QuestionType

from ..base import BaseSingleQuestionRule

if TYPE_CHECKING:
    from gradeflow_engine.schema import QuestionSchema


class NumericRangeRule(BaseSingleQuestionRule):
    """Numeric answer grading with inclusive [min_value, max_value]."""

    type: Literal["NUMERIC_RANGE"] = "NUMERIC_RANGE"
    compatible_types: frozenset[QuestionType] = frozenset({"NUMERIC"})

    min_value: float = Field(..., description="Minimum acceptable value for full credit")
    max_value: float = Field(..., description="Maximum acceptable value for full credit")

    @field_validator("max_value")
    @classmethod
    def validate_max_value(cls, v: float, info: Any) -> float:
        """Validate that max_value >= min_value."""
        min_value = info.data.get("min_value")
        if min_value is not None and v < min_value:
            raise ValueError(
                f"max_value ({v}) must be greater than or equal to min_value ({min_value})"
            )
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
            rule_name="NumericRangeRule",
        )
