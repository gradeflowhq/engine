"""AssumptionSet rule model definition."""

from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, field_validator

from gradeflow_engine.types import QuestionType

if TYPE_CHECKING:
    from gradeflow_engine.models import SingleQuestionRule
    from gradeflow_engine.schema import QuestionSchema


class Assumption(BaseModel):
    """A named assumption containing a list of rules.

    Fields:
      - name: str
      - rules: list[GradingRule]
    """

    name: str = Field(..., description="Name/label for this assumption")
    rules: list["SingleQuestionRule"] = Field(..., description="List of rules for this assumption")  # type: ignore[name-defined]


class AssumptionSetRule(BaseModel):
    """Assumption-based grading aggregation.

    The rule holds multiple `Assumption` entries. For each student, the engine
    evaluates every assumption and combines scores according to `mode`:
      - best: pick the assumption with the highest total
      - worst: pick the assumption with the lowest total
      - average: average across assumptions
    """

    type: Literal["ASSUMPTION_SET"] = "ASSUMPTION_SET"
    compatible_types: set[QuestionType] = {"CHOICE", "NUMERIC", "TEXT"}

    assumptions: list[Assumption] = Field(
        ..., description="List of named assumptions", min_length=1
    )
    mode: Literal["best", "worst", "average"] = Field(
        default="best",
        description="Aggregation mode for assumption evaluation: best|worst|average",
    )

    def validate_against_schema(
        self, question_id: str, schema: "QuestionSchema", rule_description: str
    ) -> list[str]:
        """Validate every rule in each assumption against the provided schema."""
        errors: list[str] = []

        for assumption in self.assumptions:
            for idx, rule in enumerate(assumption.rules):
                validate_method: Callable[[str, "QuestionSchema", str], list[str] | None] | None = (
                    getattr(rule, "validate_against_schema", None)
                )
                if validate_method is None:
                    continue

                rule_desc = (
                    f"{rule_description} > Assumption '{assumption.name}' > Rule {idx + 1} "
                    f"({getattr(rule, 'type', '<unknown>')})"
                )
                sub_errors = validate_method(question_id, schema, rule_desc)
                if sub_errors:
                    errors.extend(sub_errors)

        return errors

    @field_validator("assumptions", mode="after")
    @classmethod
    def validate_unique_assumption_names(cls, v: list[Assumption]) -> list[Assumption]:
        """Ensure assumption names are unique within the set."""
        names = [a.name for a in v]
        seen: set[str] = set()
        duplicates: list[str] = []
        for name in names:
            if name in seen:
                if name not in duplicates:
                    duplicates.append(name)
            else:
                seen.add(name)
        if duplicates:
            raise ValueError(
                f"Assumption names must be unique; duplicates: {', '.join(duplicates)}"
            )
        return v
