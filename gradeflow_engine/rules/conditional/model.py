"""Conditional rule model definition."""

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from gradeflow_engine.models import SingleQuestionRule


class ConditionalRule(BaseModel):
    """
    A conditional grading rule: if question(s) satisfy certain rules, then other
    question(s) should satisfy their rules.

    Supports both simple and complex conditional logic:
    - Simple: if Q1 matches rule R1, then Q2 should match rule R2
    - Complex: if multiple questions match their rules (with AND/OR logic),
      then multiple questions should match their rules

    Example: "If Q1 answer is 'recursion', then Q2 implementation should contain 'base case'"
    """

    type: Literal["CONDITIONAL"] = "CONDITIONAL"
    if_rules: dict[str, "SingleQuestionRule"] = Field(  # type: ignore[name-defined]
        description="Map of question_id -> rule for the if-condition(s)"
    )
    if_aggregation: Literal["AND", "OR"] = Field(
        default="AND",
        description=(
            "How to combine multiple if-conditions: "
            "AND requires all conditions to pass, "
            "OR requires at least one to pass"
        ),
    )
    then_rules: dict[str, "SingleQuestionRule"] = Field(  # type: ignore[name-defined]
        description="Map of question_id -> rule to apply when if-conditions are met"
    )
    description: str | None = Field(None, description="Human-readable description of the rule")

    @field_validator("if_rules")
    @classmethod
    def validate_if_rules(cls, v):
        """Ensure at least one if-condition is provided."""
        if len(v) < 1:
            raise ValueError("At least one if-condition is required")
        return v

    @field_validator("then_rules")
    @classmethod
    def validate_then_rules(cls, v, info):
        """Ensure then_rules don't overlap with if_rules."""
        if len(v) < 1:
            raise ValueError("At least one then-condition is required")
        
        if_rules = info.data.get("if_rules", {})
        overlap = set(v.keys()) & set(if_rules.keys())
        if overlap:
            raise ValueError(
                f"then_rules cannot overlap with if_rules (creates circular dependency): {overlap}"
            )
        return v
