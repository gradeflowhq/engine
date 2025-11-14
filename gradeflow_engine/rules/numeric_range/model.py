"""NumericRange rule model definition."""

from typing import Any, Literal

from pydantic import Field, field_validator

from gradeflow_engine.types import QuestionType

from ..base import BaseSingleQuestionRule


class NumericRangeRule(BaseSingleQuestionRule):
    """Grade numeric answers based on an inclusive [min_value, max_value] range."""

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
