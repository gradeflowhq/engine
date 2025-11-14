"""Conditional rule model definition."""

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from gradeflow_engine.types import QuestionType

if TYPE_CHECKING:
    from gradeflow_engine.models import SingleQuestionRule
    from gradeflow_engine.schema import QuestionSchema


class ConditionalRule(BaseModel):
    """Apply 'then' single-question rules when a set of 'if' single-question
    rules matches. 'if_rules' defines the conditions, 'if_mode' ('and' or
    'or') controls how they are combined, and 'then_rules' are applied when
    the condition is satisfied.
    """

    type: Literal["CONDITIONAL"] = "CONDITIONAL"
    compatible_types: frozenset[QuestionType] = frozenset({"CHOICE", "NUMERIC", "TEXT"})

    if_rules: list["SingleQuestionRule"] = Field(
        ...,  # required
        min_length=1,
        description="List of single-question rules that form the if-condition",
    )

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
    )

    def validate_against_question_schema(
        self, question_map: dict[str, "QuestionSchema"], rule_description: str
    ) -> list[str]:
        """Validate this conditional rule and all nested single-question rules.

        The provided `schema` is expected to be the global assessment/question
        schema; nested rules are validated against the schema entry for their
        own `question_id` by calling their `validate_against_question_schema` methods.
        """
        errors: list[str] = []

        # Validate all if_rules
        for rule in self.if_rules:
            rule_desc = f"{rule_description} > If-condition for {rule.question_id} ({rule.type})"
            sub_errors = rule.validate_against_question_schema(question_map, rule_desc)
            errors.extend(sub_errors)

        # Validate all then_rules
        for rule in self.then_rules:
            rule_desc = f"{rule_description} > Then-condition for {rule.question_id} ({rule.type})"
            sub_errors = rule.validate_against_question_schema(question_map, rule_desc)
            errors.extend(sub_errors)

        return errors

    def get_question_ids(self) -> set[str]:
        """Return the set of question ids referenced by this conditional rule."""
        questions: set[str] = set()
        for rule in self.if_rules + self.then_rules:
            questions.update(rule.get_question_ids())
        return questions

    def get_target_question_ids(self) -> set[str]:
        """Return the set of target question ids affected by this conditional rule."""
        questions: set[str] = set()
        for rule in self.then_rules:
            questions.update(rule.get_question_ids())
        return questions
