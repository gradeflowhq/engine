"""Composite rule model definition."""

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from gradeflow_engine.models import SingleQuestionRule
    # Forward references to avoid circular imports
    # SingleQuestionRule will be defined in models.py


class CompositeRule(BaseModel):
    """
    Composite rule that combines multiple rules with AND/OR logic.

    Evaluates multiple grading criteria for a single question and combines
    their results based on the specified mode (AND/OR/WEIGHTED).
    Can recursively contain other composite rules for complex grading scenarios.

    Note: Only single-question evaluation rules can be composed. ConditionalRule
    and AssumptionSetRule are excluded as they operate on multiple questions.
    """

    type: Literal["COMPOSITE"] = "COMPOSITE"
    question_id: str = Field(description="Question ID to grade")
    mode: Literal["AND", "OR", "WEIGHTED"] = Field(
        description=(
            "AND: all rules must pass; "
            "OR: at least one rule must pass; "
            "WEIGHTED: weighted average of all rules"
        )
    )
    rules: list["SingleQuestionRule"] = Field(  # type: ignore[name-defined]
        description=(
            "List of single-question rules to combine "
            "(excludes ConditionalRule and AssumptionSetRule)"
        )
    )
    weights: list[float] | None = Field(
        None, description="Weights for each rule (required for WEIGHTED mode)"
    )
    min_passing: int | None = Field(
        None, description="Minimum number of passing rules (for OR mode)"
    )
    correctness_threshold: float = Field(
        default=0.95,
        description="Threshold for considering weighted result correct (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    description: str | None = Field(None, description="Human-readable description of the rule")

    @field_validator("rules")
    @classmethod
    def validate_rules(cls, v):
        if len(v) < 1:
            raise ValueError("At least one rule is required")
        return v

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, v, info):
        mode = info.data.get("mode")

        # WEIGHTED mode requires weights
        if mode == "WEIGHTED" and v is None:
            raise ValueError("weights are required when mode is WEIGHTED")

        if v is not None:
            rules = info.data.get("rules", [])
            if len(v) != len(rules):
                raise ValueError("weights list must match rules list length")
            if any(w < 0 for w in v):
                raise ValueError("All weights must be >= 0")

            # Weights must sum to 1.0 for WEIGHTED mode
            total = sum(v)
            if mode == "WEIGHTED":
                if abs(total - 1.0) > 1e-6:  # Use small epsilon for floating point comparison
                    raise ValueError(f"For WEIGHTED mode, weights must sum to 1.0 (got {total})")
            elif total == 0:
                raise ValueError("Sum of weights must be > 0")

        return v
