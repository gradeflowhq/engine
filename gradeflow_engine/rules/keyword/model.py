"""Keyword rule model definition."""

from typing import TYPE_CHECKING, Literal

from pydantic import Field

from gradeflow_engine.types import QuestionType

from ..base import BaseSingleQuestionRule, TextRuleConfig

if TYPE_CHECKING:
    from gradeflow_engine.schema import QuestionSchema


class KeywordRule(BaseSingleQuestionRule):
    """Keyword rule matching"""

    type: Literal["KEYWORD"] = "KEYWORD"
    compatible_types: frozenset[QuestionType] = frozenset({"TEXT"})

    keywords: list[str] = Field(..., min_length=1, description="Keywords to look for")
    mode: Literal["all", "partial", "any"] = Field(
        default="all",
        description=(
            "Matching mode: 'all' requires every keyword to be present to receive max points; "
            "'partial' awards points per keyword found (points is divided evenly across keywords); "
            "'any' awards full points if at least one keyword is present"
        ),
    )
    config: TextRuleConfig = Field(default_factory=TextRuleConfig)

    def validate_against_schema(
        self, question_id: str, schema: "QuestionSchema", rule_description: str
    ) -> list[str]:
        from gradeflow_engine.rules.utils import validate_type_compatibility

        return validate_type_compatibility(
            schema=schema,
            compatible_types=self.compatible_types,
            rule_description=rule_description,
            rule_name="KeywordRule",
        )
