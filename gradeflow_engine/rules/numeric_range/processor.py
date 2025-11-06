"""NumericRange rule grading processor."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models import GradeDetail, Submission
    from .model import NumericRangeRule


def _normalize_answer(raw: str | None) -> str | None:
    """Normalize student answer: strip and return None for empty values."""
    if raw is None:
        return None
    s = raw.strip()
    return s if s != "" else None


def _try_parse_float(s: str) -> float | None:
    """
    Attempt to parse a float from the string.

    Handles common formatting like thousands separators (commas).
    Returns None if parsing fails.
    """
    # Remove common thousands separators
    s_clean = s.replace(",", "")
    try:
        return float(s_clean)
    except (ValueError, TypeError):
        return None


def _format_range(rule: "NumericRangeRule") -> str:
    """Return canonical string representation of the acceptable range."""
    return f"[{rule.min_value}, {rule.max_value}]"


def _feedback_within(rule: "NumericRangeRule") -> str:
    return f"✓ Within acceptable range {_format_range(rule)}"


def _feedback_invalid() -> str:
    return "✗ Invalid numeric value"


def _feedback_no_answer() -> str:
    return "✗ No answer provided"


def _feedback_outside(student_value: float, rule: "NumericRangeRule") -> str:
    if student_value < rule.min_value:
        diff = rule.min_value - student_value
        return f"✗ Below minimum (difference: {diff:.2f})"
    diff = student_value - rule.max_value
    return f"✗ Above maximum (difference: {diff:.2f})"


def process_numeric_range(
    rule: "NumericRangeRule", submission: "Submission"
) -> "GradeDetail | None":
    """
    Apply a numeric range rule to grade a submission.

    Args:
        rule: The NumericRange rule to apply
        submission: The student's submission

    Returns:
        GradeDetail with max_points awarded and feedback
    """
    # Import here to avoid circular dependency
    from ..base import create_grade_detail

    raw_answer = submission.answers.get(rule.question_id, "")
    student_answer = _normalize_answer(raw_answer)

    # No answer provided
    if student_answer is None:
        return create_grade_detail(
            question_id=rule.question_id,
            student_answer=raw_answer,
            correct_answer=_format_range(rule),
            points_awarded=0.0,
            max_points=rule.max_points,
            is_correct=False,
            feedback=_feedback_no_answer(),
        )

    # Parse numeric value
    student_value = _try_parse_float(student_answer)
    if student_value is None or not (student_value == student_value):  # catch NaN
        return create_grade_detail(
            question_id=rule.question_id,
            student_answer=student_answer,
            correct_answer=_format_range(rule),
            points_awarded=0.0,
            max_points=rule.max_points,
            is_correct=False,
            feedback=_feedback_invalid(),
        )

    # In-range (inclusive)
    if rule.min_value <= student_value <= rule.max_value:
        return create_grade_detail(
            question_id=rule.question_id,
            student_answer=student_answer,
            correct_answer=_format_range(rule),
            points_awarded=rule.max_points,
            max_points=rule.max_points,
            is_correct=True,
            feedback=_feedback_within(rule),
        )

    # Outside acceptable range
    return create_grade_detail(
        question_id=rule.question_id,
        student_answer=student_answer,
        correct_answer=_format_range(rule),
        points_awarded=0.0,
        max_points=rule.max_points,
        is_correct=False,
        feedback=_feedback_outside(student_value, rule),
    )
