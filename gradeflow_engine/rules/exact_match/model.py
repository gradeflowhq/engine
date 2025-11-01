"""
Exact Match Rule model definition.
"""

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from gradeflow_engine.types import QuestionType

if TYPE_CHECKING:
    from gradeflow_engine.schema import QuestionSchema


class ExactMatchRule(BaseModel):
    """
    Simple exact match grading: student answer must match the correct answer.

    Supports case-insensitive comparison and whitespace trimming for flexibility.
    Best for factual questions with single correct answers.
    """

    type: Literal["EXACT_MATCH"] = "EXACT_MATCH"
    compatible_types: set[QuestionType] = {"CHOICE", "TEXT"}
    question_id: str = Field(..., description="Question identifier to grade", min_length=1)
    correct_answer: str = Field(..., description="The expected correct answer")
    max_points: float = Field(..., description="Maximum points for correct answer", ge=0)
    case_sensitive: bool = Field(default=False, description="Whether comparison is case-sensitive")
    trim_whitespace: bool = Field(
        default=True, description="Trim leading/trailing whitespace before comparison"
    )
    description: str | None = Field(None, description="Optional human-readable description")

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
            rule_name="ExactMatchRule",
        )
        if errors:
            return errors

        # Type-specific validation for CHOICE questions
        if isinstance(schema, ChoiceQuestionSchema):
            # Check that correct answer is in valid options
            if self.case_sensitive:
                if self.correct_answer not in schema.options:
                    errors.append(
                        f"{rule_description}: Correct answer '{self.correct_answer}' "
                        f"not in schema options: {schema.options}"
                    )
            else:
                options_lower = [opt.lower() for opt in schema.options]
                if self.correct_answer.lower() not in options_lower:
                    errors.append(
                        f"{rule_description}: Correct answer '{self.correct_answer}' "
                        f"not in schema options: {schema.options} "
                        "(case-insensitive comparison)"
                    )

        return errors
