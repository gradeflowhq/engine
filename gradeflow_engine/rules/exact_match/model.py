"""
Exact Match Rule model definition.
"""

from typing import TYPE_CHECKING, Literal

from pydantic import Field

from gradeflow_engine.types import QuestionType

from ..base import BaseSingleQuestionRule, QuestionConstraint, TextRuleConfig

if TYPE_CHECKING:
    from gradeflow_engine.schema import QuestionSchema


class ExactMatchRule(BaseSingleQuestionRule):
    """Exact match rule: student answer must equal `answer`"""

    type: Literal["EXACT_MATCH"] = "EXACT_MATCH"

    compatible_types: frozenset[QuestionType] = frozenset({"TEXT"})
    constraints: frozenset[QuestionConstraint] = frozenset(
        {QuestionConstraint(type="TEXT", source="metadata", target="answer")}
    )

    answer: str = Field(..., description="Expected exact answer")
    config: TextRuleConfig = Field(
        default_factory=TextRuleConfig, description="Text normalization config"
    )

    def validate_against_schema(
        self, question_id: str, schema: "QuestionSchema", rule_description: str
    ) -> list[str]:
        """Validate this rule against an assessment question schema (type compatibility check)."""
        from gradeflow_engine.rules.utils import validate_type_compatibility

        return validate_type_compatibility(
            schema=schema,
            compatible_types=self.compatible_types,
            rule_description=rule_description,
            rule_name="ExactMatchRule",
        )
