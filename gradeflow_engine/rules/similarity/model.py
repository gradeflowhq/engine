"""Similarity rule model definition."""

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from gradeflow_engine.types import QuestionType

if TYPE_CHECKING:
    from gradeflow_engine.schema import QuestionSchema


class SimilarityRule(BaseModel):
    """
    Fuzzy text matching using string similarity algorithms.

    Handles typos, paraphrasing, and variations without exact matching.
    """

    type: Literal["SIMILARITY"] = "SIMILARITY"
    compatible_types: set[QuestionType] = {"TEXT"}
    question_id: str = Field(description="Question ID to grade")
    reference_answers: list[str] = Field(
        description="Reference answer(s) to compare against", min_length=1
    )
    algorithm: Literal["levenshtein", "jaro_winkler", "token_sort"] = Field(
        default="levenshtein", description="Similarity algorithm to use"
    )
    threshold: float = Field(
        default=0.8, description="Similarity threshold (0.0-1.0) for full credit", ge=0.0, le=1.0
    )
    max_points: float = Field(description="Maximum points available", ge=0)
    partial_credit: bool = Field(
        default=True, description="Award partial credit proportional to similarity score"
    )
    partial_credit_min: float = Field(
        default=0.5,
        description="Minimum percentage of points to award when above threshold (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    case_sensitive: bool = Field(default=False, description="Whether comparison is case-sensitive")
    description: str | None = Field(None, description="Human-readable description of the rule")

    def validate_against_schema(
        self, question_id: str, schema: "QuestionSchema", rule_description: str
    ) -> list[str]:
        """Validate this rule against a question schema."""
        from gradeflow_engine.rules.utils import validate_type_compatibility

        return validate_type_compatibility(
            schema=schema,
            compatible_types=self.compatible_types,
            rule_description=rule_description,
            rule_name="SimilarityRule",
        )
