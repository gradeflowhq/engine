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
    compatible_types: set[QuestionType] = {"TEXT"}
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

        # Check type compatibility first
        return validate_type_compatibility(
            schema=schema,
            compatible_types=self.compatible_types,
            rule_description=rule_description,
            rule_name="ExactMatchRule",
        )
