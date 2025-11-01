"""NumericRange rule model definition."""

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, field_validator

from gradeflow_engine.types import QuestionType

if TYPE_CHECKING:
    from gradeflow_engine.schema import QuestionSchema


class NumericRangeRule(BaseModel):
    """
    Numeric answer grading with min/max range and partial credit ranges.

    Accepts answers within the specified range [min_value, max_value].
    Optionally supports partial credit for values outside the main range.

    Example: Physics calculations, math problems with acceptable ranges.
    """

    type: Literal["NUMERIC_RANGE"] = "NUMERIC_RANGE"
    compatible_types: set[QuestionType] = {"NUMERIC"}
    question_id: str = Field(description="Question ID to grade")
    min_value: float = Field(description="Minimum acceptable value for full credit")
    max_value: float = Field(description="Maximum acceptable value for full credit")
    max_points: float = Field(description="Maximum points available", ge=0)
    unit: str | None = Field(None, description="Expected unit (e.g., 'meters', 'kg')")
    partial_credit_ranges: list[dict[str, float]] | None = Field(
        None, description="List of {min: float, max: float, points: float} for partial credit"
    )
    description: str | None = Field(None, description="Human-readable description of the rule")

    @field_validator("max_value")
    @classmethod
    def validate_max_value(cls, v: float, info) -> float:
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
        from gradeflow_engine.schema import NumericQuestionSchema

        # Check type compatibility first
        errors = validate_type_compatibility(
            schema=schema,
            compatible_types=self.compatible_types,
            rule_description=rule_description,
            rule_name="NumericRangeRule",
        )
        if errors:
            return errors

        # Type-specific validation for NUMERIC questions
        if not isinstance(schema, NumericQuestionSchema):
            return errors

        if schema.numeric_range is None:
            return errors  # No range defined in schema, skip validation

        schema_min, schema_max = schema.numeric_range

        # Check if rule's acceptable range is within schema range
        if not (schema_min <= self.min_value and self.max_value <= schema_max):
            errors.append(
                f"{rule_description}: Rule range [{self.min_value}, {self.max_value}] "
                f"outside schema range [{schema_min}, {schema_max}]"
            )

        return errors

    @field_validator("partial_credit_ranges")
    @classmethod
    def validate_partial_credit_ranges(cls, v, info):
        """Validate partial credit ranges."""
        if v is None:
            return v

        max_points = info.data.get("max_points", 0)

        for i, range_dict in enumerate(v):
            # Check required keys
            if not all(k in range_dict for k in ["min", "max", "points"]):
                raise ValueError(
                    f"Partial credit range {i} must have 'min', 'max', and 'points' keys"
                )

            min_val = range_dict["min"]
            max_val = range_dict["max"]
            points = range_dict["points"]

            # Validate min < max
            if min_val >= max_val:
                raise ValueError(
                    f"Partial credit range {i}: min ({min_val}) must be < max ({max_val})"
                )

            # Validate points <= max_points
            if points > max_points:
                raise ValueError(
                    f"Partial credit range {i}: points ({points}) "
                    f"cannot exceed max_points ({max_points})"
                )

            # Validate points >= 0
            if points < 0:
                raise ValueError(f"Partial credit range {i}: points ({points}) must be >= 0")

        # Check for overlaps - raise error to prevent ambiguous grading
        for i in range(len(v)):
            for j in range(i + 1, len(v)):
                r1 = v[i]
                r2 = v[j]
                # Check if ranges overlap
                if not (r1["max"] <= r2["min"] or r2["max"] <= r1["min"]):
                    raise ValueError(
                        f"Partial credit ranges {i} and {j} overlap: "
                        f"[{r1['min']}, {r1['max']}] and [{r2['min']}, {r2['max']}]. "
                        f"Ranges must not overlap to avoid ambiguous grading."
                    )

        return v
