"""Composite rule model definition."""

from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

from pydantic import Field

from gradeflow_engine.types import QuestionType

from ..base import BaseSingleQuestionRule

if TYPE_CHECKING:
    from gradeflow_engine.models import SingleQuestionRule
    from gradeflow_engine.schema import QuestionSchema


class CompositeRule(BaseSingleQuestionRule):
    """CompositeRule composes multiple single-question rules and aggregates their results.

    Fields:
      - rules: list[SingleQuestionRule]
      - mode: one of [max, min, sum, average, multiply]
    """

    type: Literal["COMPOSITE"] = "COMPOSITE"
    compatible_types: frozenset[QuestionType] =  frozenset({"CHOICE", "NUMERIC", "TEXT"})

    rules: list["SingleQuestionRule"] = Field(
        ..., description="List of single-question rules to combine", min_length=1
    )
    mode: Literal["max", "min", "sum", "average", "multiply"] = Field(
        default="sum", description="Aggregation function to apply to sub-rule scores"
    )

    def validate_against_schema(
        self, question_id: str, schema: "QuestionSchema", rule_description: str
    ) -> list[str]:
        """Delegate schema validation to each sub-rule."""
        errors: list[str] = []
        for i, sub_rule in enumerate(self.rules):
            # Type the validator if present: Callable[[question_id, schema, desc], list[str] | None]
            validate_method: Callable[[str, "QuestionSchema", str], list[str] | None] | None = (
                getattr(sub_rule, "validate_against_schema", None)
            )
            if validate_method is None:
                continue

            # model fields are guaranteed, access directly
            sub_rule_desc = f"{rule_description} > Sub-rule {i + 1} ({sub_rule.type})"
            sub_errors = validate_method(question_id, schema, sub_rule_desc)
            if sub_errors:
                # sub_errors is expected to be a list[str]
                errors.extend(sub_errors)
        return errors
