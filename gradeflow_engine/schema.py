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
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class TextQuestionSchema(BaseModel):
    """Schema for free-text answer questions."""

    type: Literal["TEXT"] = "TEXT"
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


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
            schema = ChoiceQuestionSchema(options=options, allow_multiple=allow_multiple)
        elif q_type == "NUMERIC":
            schema = NumericQuestionSchema()
        elif q_type == "TEXT":
            schema = TextQuestionSchema()
        else:
            raise ValueError(f"Unsupported question type inferred: {q_type}")

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

    # Check that each rule target unique questions in schema
    question_id_rules: dict[str, list[GradingRule]] = {}
    for rule in rubric.rules:
        for qid in rule.get_target_question_ids():
            question_id_rules.setdefault(qid, []).append(rule)

    if duplicates := [qid for qid, rules in question_id_rules.items() if len(rules) > 1]:
        for qid in duplicates:
            rule_types = ", ".join(f"{r.type}" for r in question_id_rules[qid])
            errors.append(
                f"Question '{qid}' is targeted by multiple rules: {rule_types}. "
                "Each question can only be targeted by one rule."
            )

    # Check each rule
    for i, rule in enumerate(rubric.rules):
        rule_desc = f"Rule {i + 1} ({rule.type})"
        rule_errors = rule.validate_against_question_schema(schema.questions, rule_desc)
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
    "infer_schema_from_submissions",
    # Validation functions
    "validate_rubric_against_schema",
    "validate_rubric_against_schema_strict",
]
