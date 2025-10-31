"""Keyword rule model definition."""

from typing import Literal

from pydantic import BaseModel, Field


class KeywordRule(BaseModel):
    """
    Keyword-based grading: award points based on presence of keywords.

    Can specify required keywords (must be present) and optional keywords
    (bonus points). Case sensitivity is configurable.
    """

    type: Literal["KEYWORD"] = "KEYWORD"
    question_id: str = Field(description="Question ID to grade")
    required_keywords: list[str] = Field(
        default_factory=list, description="Keywords that must be present (points per keyword)"
    )
    optional_keywords: list[str] = Field(
        default_factory=list, description="Optional keywords for bonus points"
    )
    points_per_required: float = Field(
        default=1.0, description="Points awarded for each required keyword found", ge=0
    )
    points_per_optional: float = Field(
        default=0.5, description="Points awarded for each optional keyword found", ge=0
    )
    max_optional_points: float | None = Field(
        None, description="Maximum points from optional keywords (None = no limit)"
    )
    case_sensitive: bool = Field(
        default=False, description="Whether keyword matching is case-sensitive"
    )
    partial_credit: bool = Field(
        default=True, description="Award partial credit for some required keywords"
    )
    description: str | None = Field(None, description="Human-readable description of the rule")

    @property
    def max_points(self) -> float:
        """Calculate maximum possible points."""
        required_points = len(self.required_keywords) * self.points_per_required
        if self.max_optional_points is not None:
            optional_points = self.max_optional_points
        else:
            optional_points = len(self.optional_keywords) * self.points_per_optional
        return required_points + optional_points
