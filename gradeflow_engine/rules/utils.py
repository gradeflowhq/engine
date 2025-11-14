"""
Shared utilities for rule processors.

Provides common functions for sanitization, validation, and feedback formatting.
"""

from collections.abc import Collection
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gradeflow_engine.schema import QuestionSchema
    from gradeflow_engine.types import QuestionType


def validate_type_compatibility(
    schema: "QuestionSchema",
    compatible_types: Collection["QuestionType"],
    rule_description: str,
    rule_name: str,
) -> list[str]:
    """
    Validate that a question schema is compatible with a rule's supported types.

    This is a common validation pattern used across multiple rules to check
    type compatibility and generate consistent error messages.

    Args:
        schema: The question schema to validate against
        compatible_types: Set of question types this rule supports
        rule_description: Description of the rule instance (e.g., "Rule 1 (EXACT_MATCH)")
        rule_name: Name of the rule type (e.g., "ExactMatchRule")

    Returns:
        List of validation error messages (empty if compatible)

    Example:
        >>> errors = validate_type_compatibility(
        ...     schema=some_schema,
        ...     compatible_types={"TEXT", "CHOICE"},
        ...     rule_description="Rule 1 (EXACT_MATCH)",
        ...     rule_name="ExactMatchRule"
        ... )
    """
    errors: list[str] = []

    if schema.type not in compatible_types:
        errors.append(
            f"{rule_description}: {rule_name} is only compatible with "
            f"{', '.join(compatible_types)} questions, but schema has type {schema.type}"
        )

    return errors


def validate_question_id(question_id: str) -> str:
    """
    Validate and normalize question ID.

    Args:
        question_id: Question ID to validate

    Returns:
        Normalized question ID

    Raises:
        ValueError: If question ID is invalid
    """
    if not question_id or not question_id.strip():
        raise ValueError("question_id cannot be empty or whitespace")

    question_id = question_id.strip()

    # Optionally enforce format (commented out - may be too strict)
    # if not re.match(r'^[a-zA-Z0-9_-]+$', question_id):
    #     raise ValueError(
    #         f"question_id '{question_id}' must be alphanumeric with _ or - only"
    #     )

    return question_id


def format_feedback(
    is_correct: bool, expected: str | None = None, details: str | None = None
) -> str:
    """
    Format consistent feedback messages.

    Args:
        is_correct: Whether the answer is correct
        expected: Expected answer (if applicable)
        details: Additional details

    Returns:
        Formatted feedback string
    """
    if is_correct:
        prefix = "✓ Correct"
        if details:
            return f"{prefix}: {details}"
        return prefix
    else:
        prefix = "✗ Incorrect"
        parts = [prefix]
        if expected:
            parts.append(f"Expected: {expected}")
        if details:
            parts.append(details)
        return " - ".join(parts)
