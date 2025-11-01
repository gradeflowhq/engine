"""Length rule model definition."""

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, field_validator

from gradeflow_engine.types import QuestionType

if TYPE_CHECKING:
    from gradeflow_engine.schema import QuestionSchema


class LengthRule(BaseModel):
    """
    Grade based on answer length constraints (words or characters).

    Example: Essay length requirements, short answer format checking.
    """

    type: Literal["LENGTH"] = "LENGTH"
    compatible_types: set[QuestionType] = {"TEXT"}
    question_id: str = Field(description="Question ID to grade")
    min_words: int | None = Field(None, description="Minimum word count", ge=0)
    max_words: int | None = Field(None, description="Maximum word count", ge=0)
    min_chars: int | None = Field(None, description="Minimum character count", ge=0)
    max_chars: int | None = Field(None, description="Maximum character count", ge=0)
    max_points: float = Field(description="Maximum points available", ge=0)
    deduct_per_violation: float = Field(
        default=0.0, description="Points deducted for each constraint violation", ge=0
    )
    strict: bool = Field(
        default=False, description="If true, award 0 points if any constraint violated"
    )
    description: str | None = Field(None, description="Human-readable description of the rule")

    @field_validator("min_words", "max_words", "min_chars", "max_chars")
    @classmethod
    def validate_at_least_one_constraint(cls, v, info):
        # Check if at least one constraint is set
        values = info.data
        has_constraint = any(
            [
                values.get("min_words") is not None,
                values.get("max_words") is not None,
                values.get("min_chars") is not None,
                values.get("max_chars") is not None,
            ]
        )
        if not has_constraint and v is None:
            raise ValueError("At least one length constraint must be specified")
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
            rule_name="LengthRule",
        )
