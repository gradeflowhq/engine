"""MultipleChoice rule model definition."""

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from gradeflow_engine.types import QuestionType

if TYPE_CHECKING:
    from gradeflow_engine.schema import QuestionSchema


class MultipleChoiceRule(BaseModel):
    """
    Multiple choice question grading with various scoring modes.

    Supports MCQ (single answer) and MRQ (multiple answers).
    """

    type: Literal["MULTIPLE_CHOICE"] = "MULTIPLE_CHOICE"
    compatible_types: set[QuestionType] = {"CHOICE"}

    question_id: str = Field(description="Question ID to grade")
    correct_answers: list[str] = Field(description="List of correct answer(s)", min_length=1)
    max_points: float = Field(description="Maximum points available", ge=0)
    scoring_mode: Literal["all_or_nothing", "partial", "negative"] = Field(
        default="all_or_nothing",
        description=(
            "all_or_nothing: full points only if all correct; "
            "partial: proportional to correct selections; "
            "negative: deduct points for wrong selections"
        ),
    )
    penalty_per_wrong: float = Field(
        default=0.0, description="Points deducted per wrong selection (for negative scoring)", ge=0
    )
    case_sensitive: bool = Field(default=False, description="Whether matching is case-sensitive")
    description: str | None = Field(None, description="Human-readable description of the rule")

    def validate_against_schema(
        self, question_id: str, schema: "QuestionSchema", rule_description: str
    ) -> list[str]:
        """Validate this rule against a question schema."""
        from gradeflow_engine.rules.utils import validate_type_compatibility
        from gradeflow_engine.schema import ChoiceQuestionSchema

        # Check type compatibility first
        errors = validate_type_compatibility(
            schema=schema,
            compatible_types=self.compatible_types,
            rule_description=rule_description,
            rule_name="MultipleChoiceRule",
        )
        if errors:
            return errors

        # Type-specific validation for CHOICE questions
        if not isinstance(schema, ChoiceQuestionSchema):
            return errors

        # Check that all correct answers are valid options
        for answer in self.correct_answers:
            # Handle case sensitivity
            if self.case_sensitive:
                if answer not in schema.options:
                    errors.append(
                        f"{rule_description}: Correct answer '{answer}' "
                        f"not in schema options: {schema.options}"
                    )
            else:
                options_lower = [opt.lower() for opt in schema.options]
                if answer.lower() not in options_lower:
                    errors.append(
                        f"{rule_description}: Correct answer '{answer}' "
                        f"not in schema options: {schema.options} "
                        "(case-insensitive comparison)"
                    )

        return errors
