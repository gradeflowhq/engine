"""
Composite rule that combines multiple single-question rules
and aggregates their scores using a chosen function.
"""

from typing import TYPE_CHECKING, Literal

from pydantic import Field

from gradeflow_engine.types import QuestionType

from ..base import BaseSingleQuestionRule

if TYPE_CHECKING:
    from gradeflow_engine.models import SingleQuestionRule
    from gradeflow_engine.schema import QuestionSchema


class CompositeRule(BaseSingleQuestionRule):
    """
    Compose several single-question rules and aggregate their scores
    with the configured mode (max, min, sum, average, multiply).
    """

    type: Literal["COMPOSITE"] = "COMPOSITE"
    compatible_types: frozenset[QuestionType] = frozenset({"CHOICE", "NUMERIC", "TEXT"})

    rules: list["SingleQuestionRule"] = Field(
        ..., description="List of single-question rules to combine", min_length=1
    )
    mode: Literal["max", "min", "sum", "average", "multiply"] = Field(
        default="sum", description="Aggregation function to apply to sub-rule scores"
    )

    def validate_against_question_schema(
        self, question_map: dict[str, "QuestionSchema"], rule_description: str
    ) -> list[str]:
        """Delegate schema validation to each sub-rule."""
        errors: list[str] = []
        for i, sub_rule in enumerate(self.rules):
            sub_rule_desc = (
                f"{rule_description} > Sub-rule {i + 1}"
                f" ({sub_rule.type}) for {sub_rule.question_id}"
            )
            sub_errors = sub_rule.validate_against_question_schema(question_map, sub_rule_desc)
            if sub_errors:
                # sub_errors is expected to be a list[str]
                errors.extend(sub_errors)
        return errors

    def get_question_ids(self) -> set[str]:
        """Collect question ids from all sub-rules."""
        questions: set[str] = set()
        for sub_rule in self.rules:
            questions.update(sub_rule.get_question_ids())
        return questions

    def get_target_question_ids(self) -> set[str]:
        """Return the set of target question ids affected by this composite rule."""
        return {self.question_id}
