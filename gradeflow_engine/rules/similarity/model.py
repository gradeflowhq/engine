"""Similarity rule model definition."""

from typing import TYPE_CHECKING, Literal

from pydantic import Field

from gradeflow_engine.types import QuestionType

from ..base import BaseSingleQuestionRule, TextRuleConfig


class SimilarityRuleConfig(TextRuleConfig):
    algorithm: Literal["levenshtein", "jaro_winkler", "token_sort"] = Field(
        default="levenshtein", description="Similarity algorithm to use"
    )


if TYPE_CHECKING:
    from gradeflow_engine.schema import QuestionSchema


class SimilarityRule(BaseSingleQuestionRule):
    """Fuzzy text matching using configured similarity algorithm."""

    type: Literal["SIMILARITY"] = "SIMILARITY"
    compatible_types: frozenset[QuestionType] = frozenset({"TEXT"})

    reference: str = Field(..., description="Reference text to compare against")
    threshold: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Similarity threshold (0.0-1.0)"
    )
    config: SimilarityRuleConfig = Field(default_factory=SimilarityRuleConfig)

    def validate_against_schema(
        self, question_id: str, schema: "QuestionSchema", rule_description: str
    ) -> list[str]:
        from gradeflow_engine.rules.utils import validate_type_compatibility

        return validate_type_compatibility(
            schema=schema,
            compatible_types=self.compatible_types,
            rule_description=rule_description,
            rule_name="SimilarityRule",
        )
