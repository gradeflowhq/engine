"""Conditional rule model definition."""

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from gradeflow_engine.types import QuestionType

if TYPE_CHECKING:
    from gradeflow_engine.models import SingleQuestionRule
    from gradeflow_engine.schema import QuestionSchema


class ConditionalRule(BaseModel):
    """Conditional grading rule.

    Example: If Q1 match rule R1 and Q2 match rule R2, apply rule R3 for Q3.

    Notes on semantics:
    - `if_rules` is a list of single-question rules. At grading time each
      if-rule will produce a numeric score; the condition interprets strictly
      correct answer as a passed/True condition.
    - `if_mode` controls how multiple if-conditions are combined:
      * and: all if-rule are correct
      * or: at least one if-rule is correct
    - `then_rules` are applied when the condition is satisfied. There is no
      restriction on which question ids the then-rules may target (they may
      target the same questions used in if_rules or different ones).
    """

    type: Literal["CONDITIONAL"] = "CONDITIONAL"
    compatible_types: frozenset[QuestionType] = frozenset({"CHOICE", "NUMERIC", "TEXT"})

    if_rules: list["SingleQuestionRule"] = Field(
        ...,  # required
        min_length=1,
        description="List of single-question rules that form the if-condition",
    )  # type: ignore[name-defined]

    if_mode: Literal["and", "or"] = Field(
        default="and",
        description=(
            "How to combine multiple if-conditions: 'and' requires all to pass; "
            "'or' requires at least one to pass (a rule is considered passing when its score > 0)."
        ),
    )

    then_rules: list["SingleQuestionRule"] = Field(
        ...,  # required
        min_length=1,
        description="List of single-question rules to apply when the condition matches",
    )  # type: ignore[name-defined]

    def validate_against_schema(
        self, question_id: str, schema: "QuestionSchema", rule_description: str
    ) -> list[str]:
        """Validate this conditional rule and all nested single-question rules.

        The provided `schema` is expected to be the global assessment/question
        schema; nested rules are validated against the schema entry for their
        own `question_id` by calling their `validate_against_schema` methods.
        """
        errors: list[str] = []

        # Validate all if_rules
        for rule in self.if_rules:
            validate_method = rule.validate_against_schema
            if validate_method is not None and callable(validate_method):
                rule_desc = (
                    f"{rule_description} > If-condition for Q{rule.question_id} ({rule.type})"
                )
                sub_errors: list[str] = validate_method(rule.question_id, schema, rule_desc)
                errors.extend(sub_errors)

        # Validate all then_rules
        for rule in self.then_rules:
            validate_method = rule.validate_against_schema
            if validate_method is not None and callable(validate_method):
                rule_desc = (
                    f"{rule_description} > Then-condition for Q{rule.question_id} ({rule.type})"
                )
                sub_errors: list[str] = validate_method(rule.question_id, schema, rule_desc)
                errors.extend(sub_errors)

        return errors
