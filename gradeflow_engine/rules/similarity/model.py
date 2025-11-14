"""Similarity rule model definition."""

from typing import Literal

from pydantic import Field

from gradeflow_engine.types import QuestionType

from ..base import BaseSingleQuestionRule, TextRuleConfig


class SimilarityRuleConfig(TextRuleConfig):
    algorithm: Literal["levenshtein", "jaro_winkler", "token_sort"] = Field(
        default="levenshtein", description="Similarity algorithm to use"
    )


class SimilarityRule(BaseSingleQuestionRule):
    """Fuzzy text matching using configured similarity algorithm."""

    type: Literal["SIMILARITY"] = "SIMILARITY"
    compatible_types: frozenset[QuestionType] = frozenset({"TEXT"})

    reference: str = Field(..., description="Reference text to compare against")
    threshold: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Similarity threshold (0.0-1.0)"
    )
    config: SimilarityRuleConfig = Field(default_factory=SimilarityRuleConfig)
