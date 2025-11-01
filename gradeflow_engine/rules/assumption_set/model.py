"""AssumptionSet rule model definition."""

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field, field_validator

from gradeflow_engine.types import QuestionType

if TYPE_CHECKING:
    from gradeflow_engine.models import SingleQuestionRule
    from gradeflow_engine.schema import QuestionSchema


class AnswerSet(BaseModel):
    """
    A named set of grading rules for a group of questions.

    Each question in the answer set is evaluated using its own grading rule,
    allowing for complex grading logic within assumption sets.
    """

    name: str = Field(description="Name/label for this answer set")
    answers: dict[str, "SingleQuestionRule"] = Field(  # type: ignore[name-defined]
        description="Map of question_id -> grading rule to apply"
    )


class AssumptionSetRule(BaseModel):
    """
    Assumption-based grading: define multiple valid answer sets and apply
    the most favorable one to each student.

    Each answer set contains grading rules for questions, allowing complex
    evaluation scenarios (e.g., different interpretations of a problem that
    lead to different correct answers with different validation logic).

    Example: A physics problem that can be solved with different assumptions
    about friction, where each assumption leads to different numeric ranges
    for the final answer.
    """

    type: Literal["ASSUMPTION_SET"] = "ASSUMPTION_SET"
    compatible_types: set[QuestionType] = {"CHOICE", "NUMERIC", "TEXT"}  # Works across questions
    question_ids: list[str] = Field(description="List of question IDs in this group")
    answer_sets: list[AnswerSet] = Field(description="List of valid answer sets")
    mode: Literal["favor_best", "first_match"] = Field(
        default="favor_best",
        description="favor_best: pick set with highest score; first_match: use first matching set",
    )
    description: str | None = Field(None, description="Human-readable description of the rule")

    @field_validator("answer_sets")
    @classmethod
    def validate_answer_sets(cls, v):
        if len(v) < 1:
            raise ValueError("At least one answer set is required")
        return v

    def validate_against_schema(
        self, question_id: str, schema: "QuestionSchema", rule_description: str
    ) -> list[str]:
        """Validate this rule against a question schema."""
        errors: list[str] = []

        # Validate all answer sets
        for answer_set in self.answer_sets:
            for q_id, rule in answer_set.answers.items():
                validate_method = getattr(rule, "validate_against_schema", None)
                if validate_method is not None and callable(validate_method):
                    rule_desc = (
                        f"{rule_description} > Answer set '{answer_set.name}' > "
                        f"Q{q_id} ({rule.type})"
                    )
                    sub_errors: Any = validate_method(q_id, schema, rule_desc)
                    if isinstance(sub_errors, list):
                        errors.extend(sub_errors)

        return errors
