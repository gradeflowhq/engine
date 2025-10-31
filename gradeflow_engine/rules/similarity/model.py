"""Similarity rule model definition."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SimilarityRule(BaseModel):
    """
    Fuzzy text matching using string similarity algorithms.

    Handles typos, paraphrasing, and variations without exact matching.
    """

    type: Literal["SIMILARITY"] = "SIMILARITY"
    question_id: str = Field(description="Question ID to grade")
    reference_answers: list[str] = Field(description="Reference answer(s) to compare against")
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

    @field_validator("reference_answers")
    @classmethod
    def validate_reference_answers(cls, v):
        if len(v) < 1:
            raise ValueError("At least one reference answer is required")
        return v
