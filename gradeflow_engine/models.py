"""
Pydantic models for the grading engine.

These models define the structure of rubrics, grading rules, submissions,
and grading results. All models use Pydantic v2 for validation and serialization.
"""

from typing import Annotated, Any

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

# ============================================================================
# Single-Question Rules
# ============================================================================
# Rules that evaluate a single question independently

# Basic single-question rules (non-composite)
BasicSingleQuestionRule = (
    ExactMatchRule
    | NumericRangeRule
    | MultipleChoiceRule
    | LengthRule
    | SimilarityRule
    | KeywordRule
    | RegexRule
    | ProgrammableRule
)

# All single-question rules (including composite)
SingleQuestionRule = Annotated[
    ExactMatchRule
    | NumericRangeRule
    | MultipleChoiceRule
    | LengthRule
    | SimilarityRule
    | KeywordRule
    | RegexRule
    | ProgrammableRule
    | CompositeRule,
    Discriminator("type"),
]

# Rules that can be composed (single-question evaluation rules only)
# Alias for backwards compatibility
ComposableRule = SingleQuestionRule

# ============================================================================
# Multiple-Question Rules
# ============================================================================
# Rules that evaluate relationships across multiple questions

MultipleQuestionRule = Annotated[
    ConditionalRule | AssumptionSetRule,
    Discriminator("type"),
]

# ============================================================================
# All Grading Rules
# ============================================================================

# Discriminated union of all rule types for faster validation and better error messages
GradingRule = Annotated[
    # Single-question rules
    ExactMatchRule
    | NumericRangeRule
    | MultipleChoiceRule
    | LengthRule
    | SimilarityRule
    | KeywordRule
    | RegexRule
    | ProgrammableRule
    | CompositeRule
    # Multiple-question rules
    | ConditionalRule
    | AssumptionSetRule,
    Discriminator("type"),  # Use 'type' field for discrimination
]

# Update model references to properly reference SingleQuestionRule
CompositeRule.model_rebuild()
ConditionalRule.model_rebuild()
AnswerSet.model_rebuild()
AssumptionSetRule.model_rebuild()


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
    "BasicSingleQuestionRule",
    "ComposableRule",
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
    "MultipleQuestionRule",
    "NumericRangeRule",
    "ProgrammableRule",
    "RegexRule",
    "Rubric",
    "SimilarityRule",
    "SingleQuestionRule",
    "StudentResult",
    "Submission",
]
