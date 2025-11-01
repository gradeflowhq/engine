"""
Assessment schema validation and inference.

Provides models and utilities for defining assessment schemas (question types,
options, constraints) and validating rubrics against them.
"""

import logging
from collections import Counter
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Discriminator, Field, field_validator

from .models import GradingRule, Rubric, Submission
from .types import QuestionType

logger = logging.getLogger(__name__)


# ============================================================================
# Question Type Definitions (Discriminated Union Pattern)
# ============================================================================


class ChoiceQuestionSchema(BaseModel):
    """Schema for choice-based questions (MCQ, MRQ, True/False)."""

    type: Literal["CHOICE"] = "CHOICE"
    question_id: str = Field(description="Unique question identifier")
    options: list[str] = Field(description="Valid answer options")
    allow_multiple: bool = Field(
        default=False, description="Whether multiple selections are allowed (MRQ vs MCQ)"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: list[str]) -> list[str]:
        """Validate that options list is not empty."""
        if len(v) == 0:
            raise ValueError("Options list cannot be empty")
        return v


class NumericQuestionSchema(BaseModel):
    """Schema for numeric answer questions."""

    type: Literal["NUMERIC"] = "NUMERIC"
    question_id: str = Field(description="Unique question identifier")
    numeric_range: tuple[float, float] | None = Field(
        default=None, description="Expected numeric range [min, max]"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class TextQuestionSchema(BaseModel):
    """Schema for free-text answer questions."""

    type: Literal["TEXT"] = "TEXT"
    question_id: str = Field(description="Unique question identifier")
    max_length: int | None = Field(default=None, description="Maximum answer length")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("max_length")
    @classmethod
    def validate_max_length(cls, v: int | None) -> int | None:
        """Validate that max_length is positive."""
        if v is not None and v <= 0:
            raise ValueError("max_length must be positive")
        return v


# Discriminated union of all question schema types
QuestionSchema = Annotated[
    ChoiceQuestionSchema | NumericQuestionSchema | TextQuestionSchema,
    Discriminator("type"),
]


# ============================================================================
# Assessment Schema Model
# ============================================================================


class AssessmentSchema(BaseModel):
    """
    Complete schema for an assessment.

    Defines all questions, their types, and constraints.
    """

    name: str = Field(description="Assessment name")
    questions: dict[str, QuestionSchema] = Field(
        description="Map of question_id -> question schema"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("questions")
    @classmethod
    def validate_questions_not_empty(
        cls, v: dict[str, QuestionSchema]
    ) -> dict[str, QuestionSchema]:
        """Validate that at least one question is defined."""
        if len(v) == 0:
            raise ValueError("Assessment must have at least one question")
        return v

    @field_validator("questions")
    @classmethod
    def validate_question_ids_match(cls, v: dict[str, QuestionSchema]) -> dict[str, QuestionSchema]:
        """Validate that dict keys match question_id in values."""
        for key, schema in v.items():
            if key != schema.question_id:
                raise ValueError(
                    f"Question ID mismatch: key '{key}' != "
                    f"schema.question_id '{schema.question_id}'"
                )
        return v


# ============================================================================
# Schema Validation Errors
# ============================================================================


class SchemaValidationError(Exception):
    """Raised when rubric validation against schema fails."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(
            f"Schema validation failed with {len(errors)} error(s):\n"
            + "\n".join(f"  - {e}" for e in errors)
        )


# ============================================================================
# Schema Inference
# ============================================================================


def _infer_question_type_from_answers(answers: list[str]) -> tuple[QuestionType, bool]:
    """
    Infer question type and whether multiple selections are allowed.

    Args:
        answers: List of student answers for a question

    Returns:
        Tuple of (question_type, allow_multiple)
    """
    if not answers:
        return ("TEXT", False)

    # Filter out empty answers for analysis
    non_empty = [a.strip() for a in answers if a.strip()]
    if not non_empty:
        return ("TEXT", False)

    # Check for numeric patterns
    numeric_count = 0
    for ans in non_empty:
        try:
            float(ans)
            numeric_count += 1
        except ValueError:
            pass

    if numeric_count / len(non_empty) > 0.8:  # 80% numeric threshold
        return ("NUMERIC", False)

    # Check if answers look like multiple selections (comma/semicolon separated)
    multi_select_count = sum(1 for ans in non_empty if "," in ans or ";" in ans)
    has_multi_select = multi_select_count / len(non_empty) > 0.1  # 10% have multiple selections

    # For multi-select, check individual option lengths
    if has_multi_select:
        all_options = []
        for ans in non_empty:
            if "," in ans:
                all_options.extend([opt.strip() for opt in ans.split(",")])
            elif ";" in ans:
                all_options.extend([opt.strip() for opt in ans.split(";")])
            else:
                all_options.append(ans.strip())
        avg_length = sum(len(opt) for opt in all_options) / len(all_options) if all_options else 0
        unique_count = len(set(all_options))
    else:
        avg_length = sum(len(ans) for ans in non_empty) / len(non_empty)
        unique_count = len(set(non_empty))

    # If few unique values and very short answers (max 2 chars), likely CHOICE
    if unique_count <= 10 and avg_length <= 2:
        return ("CHOICE", has_multi_select)

    # Default to TEXT
    return ("TEXT", False)


def infer_mcq_options(answers: list[str], min_frequency: float = 0.05) -> list[str]:
    """
    Infer valid options for MCQ/MRQ from answer distribution.

    Args:
        answers: List of student answers
        min_frequency: Minimum frequency (0-1) for an option to be included

    Returns:
        List of inferred valid options
    """
    non_empty = [a.strip() for a in answers if a.strip()]
    if not non_empty:
        return []

    # For multiple response, split by common separators
    all_selections: list[str] = []
    for ans in non_empty:
        if "," in ans or ";" in ans:
            # Split and clean
            parts = ans.replace(";", ",").split(",")
            all_selections.extend(p.strip() for p in parts if p.strip())
        else:
            all_selections.append(ans)

    # Count frequencies
    counter: Counter[str] = Counter(all_selections)
    total = len(non_empty)
    threshold = max(1, int(total * min_frequency))

    # Return options that appear at least threshold times, sorted by frequency
    options = [opt for opt, count in counter.most_common() if count >= threshold]
    return options


def infer_numeric_range(answers: list[str]) -> tuple[float, float] | None:
    """
    Infer numeric range from numeric answers.

    Args:
        answers: List of student answers

    Returns:
        Tuple of (min, max) or None if not numeric
    """
    numeric_values: list[float] = []
    for ans in answers:
        if not ans.strip():
            continue
        try:
            numeric_values.append(float(ans.strip()))
        except ValueError:
            pass

    if not numeric_values:
        return None

    return (min(numeric_values), max(numeric_values))


def infer_schema_from_submissions(
    submissions: list[Submission], name: str = "Inferred Assessment"
) -> AssessmentSchema:
    """
    Infer assessment schema from submission data.

    Args:
        submissions: List of student submissions
        name: Name for the inferred schema

    Returns:
        AssessmentSchema inferred from submissions

    Raises:
        ValueError: If no submissions provided or no questions found
    """
    if not submissions:
        raise ValueError("Cannot infer schema from empty submissions list")

    # Collect all question IDs and their answers
    question_answers: dict[str, list[str]] = {}
    for submission in submissions:
        for question_id, answer in submission.answers.items():
            if question_id not in question_answers:
                question_answers[question_id] = []
            question_answers[question_id].append(answer)

    if not question_answers:
        raise ValueError("No questions found in submissions")

    # Infer schema for each question
    questions: dict[str, QuestionSchema] = {}
    for question_id, answers in question_answers.items():
        q_type, allow_multiple = _infer_question_type_from_answers(answers)

        # Build question schema based on type
        schema: QuestionSchema
        if q_type == "CHOICE":
            options = infer_mcq_options(answers)
            schema = ChoiceQuestionSchema(
                question_id=question_id, options=options, allow_multiple=allow_multiple
            )
        elif q_type == "NUMERIC":
            numeric_range = infer_numeric_range(answers)
            schema = NumericQuestionSchema(question_id=question_id, numeric_range=numeric_range)
        else:  # TEXT
            non_empty = [a for a in answers if a.strip()]
            max_len = max(len(a) for a in non_empty) if non_empty else None
            schema = TextQuestionSchema(question_id=question_id, max_length=max_len)

        questions[question_id] = schema

    return AssessmentSchema(name=name, questions=questions)


# ============================================================================
# Rubric Validation Against Schema
# ============================================================================


def validate_rubric_against_schema(rubric: Rubric, schema: AssessmentSchema) -> list[str]:
    """
    Validate a rubric against an assessment schema.

    Delegates validation to individual rules that implement the SchemaValidatable protocol.
    Also checks that all questions referenced by rules exist in the schema.

    Args:
        rubric: The rubric to validate
        schema: The assessment schema to validate against

    Returns:
        List of validation error messages (empty if valid)
    """
    errors: list[str] = []

    # Extract question IDs from rules
    def get_question_ids(rule: GradingRule) -> list[str]:
        """Extract all question IDs referenced by a rule."""
        from .rules import (
            AssumptionSetRule,
            CompositeRule,
            ConditionalRule,
        )

        # Type-specific extraction
        if hasattr(rule, "question_id"):
            return [rule.question_id]  # type: ignore[union-attr]
        elif isinstance(rule, ConditionalRule):
            # Collect from both if_rules and then_rules
            questions: set[str] = set()
            questions.update(rule.if_rules.keys())
            questions.update(rule.then_rules.keys())
            return list(questions)
        elif isinstance(rule, AssumptionSetRule):
            # Collect all questions from all answer sets
            questions = set()
            for answer_set in rule.answer_sets:
                questions.update(answer_set.answers.keys())
            return list(questions)
        elif isinstance(rule, CompositeRule):
            # Recursively collect from sub-rules
            questions = set()
            for sub_rule in rule.rules:
                questions.update(get_question_ids(sub_rule))
            return list(questions)
        return []

    # Check each rule
    for i, rule in enumerate(rubric.rules):
        rule_desc = f"Rule {i + 1} ({rule.type})"

        question_ids = get_question_ids(rule)

        for question_id in question_ids:
            # Check question exists in schema
            if question_id not in schema.questions:
                errors.append(f"{rule_desc}: Question '{question_id}' not found in schema")
                continue

            q_schema = schema.questions[question_id]

            # If rule implements SchemaValidatable, let it validate itself
            validate_method = getattr(rule, "validate_against_schema", None)
            if validate_method is not None and callable(validate_method):
                rule_errors: Any = validate_method(question_id, q_schema, rule_desc)
                if isinstance(rule_errors, list):
                    errors.extend(rule_errors)

    return errors


def validate_rubric_against_schema_strict(rubric: Rubric, schema: AssessmentSchema) -> None:
    """
    Validate rubric against schema, raising exception if invalid.

    Args:
        rubric: The rubric to validate
        schema: The assessment schema to validate against

    Raises:
        SchemaValidationError: If validation fails
    """
    errors = validate_rubric_against_schema(rubric, schema)
    if errors:
        raise SchemaValidationError(errors)


__all__ = [
    # Type alias
    "QuestionType",
    # Schema models
    "ChoiceQuestionSchema",
    "NumericQuestionSchema",
    "TextQuestionSchema",
    "QuestionSchema",
    "AssessmentSchema",
    # Errors
    "SchemaValidationError",
    # Inference functions
    "infer_mcq_options",
    "infer_numeric_range",
    "infer_schema_from_submissions",
    # Validation functions
    "validate_rubric_against_schema",
    "validate_rubric_against_schema_strict",
]
