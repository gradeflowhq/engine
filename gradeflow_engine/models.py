"""
Pydantic models for the grading engine.

These models define the structure of rubrics, grading rules, submissions,
and grading results. All models use Pydantic v2 for validation and serialization.
"""

from typing import Annotated, Any, Union

from pydantic import BaseModel, Discriminator, Field

# Import all rule models from the rules/ directory (auto-discovered)
from .rules import (
    AnswerSet,
    AssumptionSetRule,
    CompositeRule,
    ConditionalRule,
    ExactMatchRule,
    KeywordRule,
    LengthRule,
    MultipleChoiceRule,
    NumericRangeRule,
    ProgrammableRule,
    RegexRule,
    SimilarityRule,
)

# Type alias for metadata fields (JSON-serializable values)
# Use Any instead of recursive types to avoid Pydantic recursion issues
Metadata = dict[str, Any]


# ============================================================================
# Grading Rule Models (Discriminated Union)
# ============================================================================

# All rule model classes are now imported from rules/ directory
# Each rule is defined in its own module: rules/<rule_name>/model.py

# Discriminated union of all rule types for faster validation and better error messages
GradingRule = Annotated[
    ExactMatchRule
    | NumericRangeRule
    | MultipleChoiceRule
    | LengthRule
    | SimilarityRule
    | ConditionalRule
    | AssumptionSetRule
    | ProgrammableRule
    | KeywordRule
    | RegexRule
    | CompositeRule,
    Discriminator("type"),  # Use 'type' field for discrimination
]

# Rules that can be composed (single-question evaluation rules only)
ComposableRule = Union[
    ExactMatchRule,
    NumericRangeRule,
    MultipleChoiceRule,
    LengthRule,
    SimilarityRule,
    KeywordRule,
    RegexRule,
    ProgrammableRule,
    "CompositeRule",  # Allow recursive composition
]

# Update CompositeRule to properly reference GradingRule
CompositeRule.model_rebuild()


# ============================================================================
# Rubric Model
# ============================================================================


class Rubric(BaseModel):
    """
    Complete grading rubric for an assessment.

    Contains all grading rules.
    """

    name: str = Field(description="Human-readable name")
    rules: list[GradingRule] = Field(default_factory=list, description="List of grading rules")
    metadata: Metadata = Field(default_factory=dict, description="Additional metadata")


# ============================================================================
# Submission and Answer Models
# ============================================================================


class Submission(BaseModel):
    """A student's submission with answers to questions."""

    student_id: str = Field(description="Unique student identifier")
    answers: dict[str, str] = Field(description="Map of question_id -> student_answer")
    metadata: Metadata = Field(
        default_factory=dict, description="Additional metadata (e.g., timestamp)"
    )


# ============================================================================
# Grading Result Models
# ============================================================================


class GradeDetail(BaseModel):
    """Detailed grading information for a single question."""

    question_id: str = Field(description="Question identifier")
    student_answer: str | None = Field(None, description="Student's answer")
    correct_answer: str | None = Field(None, description="Expected correct answer")
    points_awarded: float = Field(description="Points awarded for this question")
    max_points: float = Field(description="Maximum points possible")
    is_correct: bool = Field(description="Whether the answer is correct")
    rule_applied: str | None = Field(None, description="ID of the rule that was applied")
    feedback: str | None = Field(None, description="Feedback or comments")


class StudentResult(BaseModel):
    """Complete grading results for a single student."""

    student_id: str = Field(description="Student identifier")
    total_points: float = Field(description="Total points awarded")
    max_points: float = Field(description="Maximum points possible")
    percentage: float = Field(description="Percentage score (0-100)")
    grade_details: list[GradeDetail] = Field(description="Detailed grading for each question")
    metadata: Metadata = Field(default_factory=dict, description="Additional metadata")


class GradeOutput(BaseModel):
    """
    Complete output from the grading engine.

    Contains results for all students.
    """

    results: list[StudentResult] = Field(description="Results for all students")
    metadata: Metadata = Field(default_factory=dict, description="Additional metadata")


__all__ = [
    "AnswerSet",
    "AssumptionSetRule",
    "CompositeRule",
    "ConditionalRule",
    "ExactMatchRule",
    "GradeDetail",
    "GradeOutput",
    "GradingRule",
    "KeywordRule",
    "LengthRule",
    "Metadata",
    "MultipleChoiceRule",
    "NumericRangeRule",
    "ProgrammableRule",
    "RegexRule",
    "Rubric",
    "SimilarityRule",
    "StudentResult",
    "Submission",
    "ComposableRule",
]
