"""Assumption set rule model for aggregating named assumptions into a single score."""

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, field_validator

from gradeflow_engine.types import QuestionType

if TYPE_CHECKING:
    from gradeflow_engine.models import SingleQuestionRule
    from gradeflow_engine.schema import QuestionSchema


class Assumption(BaseModel):
    """A named assumption containing a list of rules."""

    name: str = Field(..., description="Name/label for this assumption")
    rules: list["SingleQuestionRule"] = Field(..., description="List of rules for this assumption")  # type: ignore[name-defined]


class AssumptionSetRule(BaseModel):
    """
    Aggregate multiple named assumptions by evaluating each and combining their scores
    using the configured mode (best, worst, or average).
    """

    type: Literal["ASSUMPTION_SET"] = "ASSUMPTION_SET"
    compatible_types: frozenset[QuestionType] = frozenset({"CHOICE", "NUMERIC", "TEXT"})

    assumptions: list[Assumption] = Field(
        ..., description="List of named assumptions", min_length=1
    )
    mode: Literal["best", "worst", "average"] = Field(
        default="best",
        description="Aggregation mode for assumption evaluation: best|worst|average",
    )

    def validate_against_question_schema(
        self, question_map: dict[str, "QuestionSchema"], rule_description: str
    ) -> list[str]:
        """Validate every rule in each assumption against the provided schema."""
        errors: list[str] = []

        for assumption in self.assumptions:
            for idx, rule in enumerate(assumption.rules):
                rule_desc = (
                    f"{rule_description} > Assumption '{assumption.name}' > Rule {idx + 1} "
                    f"({getattr(rule, 'type', '<unknown>')})"
                    f"{' for ' + rule.question_id}"
                )
                sub_errors = rule.validate_against_question_schema(question_map, rule_desc)
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

    def get_question_ids(self) -> set[str]:
        """Collect all question ids referenced by rules inside each assumption."""
        questions: set[str] = set()
        for assumption in self.assumptions:
            for rule in assumption.rules:
                questions.update(rule.get_question_ids())
        return questions

    def get_target_question_ids(self) -> set[str]:
        """Return the set of target question ids affected by this assumption set rule."""
        return self.get_question_ids()
