"""NumericRange rule grading processor."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models import GradeDetail, Submission
    from .model import NumericRangeRule


def process_numeric_range(
    rule: "NumericRangeRule", submission: "Submission"
) -> "GradeDetail | None":
    """
    Apply a numeric range rule to grade a submission.

    Args:
        rule: The NumericRange rule to apply
        submission: The student's submission

    Returns:
        GradeDetail with points awarded and feedback
    """
    # Import here to avoid circular dependency
    from ..base import create_grade_detail, get_student_answer

    student_answer = get_student_answer(submission, rule.question_id, strip=True)

    try:
        student_value = float(student_answer)
    except ValueError:
        return create_grade_detail(
            question_id=rule.question_id,
            student_answer=student_answer,
            correct_answer=str(rule.correct_value),
            points_awarded=0.0,
            max_points=rule.max_points,
            is_correct=False,
            feedback="✗ Invalid numeric value",
        )

    # Check exact match with tolerance
    difference = abs(student_value - rule.correct_value)
    if difference <= rule.tolerance:
        return create_grade_detail(
            question_id=rule.question_id,
            student_answer=student_answer,
            correct_answer=str(rule.correct_value),
            points_awarded=rule.max_points,
            max_points=rule.max_points,
            is_correct=True,
            feedback=f"✓ Within tolerance (±{rule.tolerance})",
        )

    # Check partial credit ranges
    if rule.partial_credit_ranges:
        for pc_range in rule.partial_credit_ranges:
            if pc_range["min"] <= student_value <= pc_range["max"]:
                points = pc_range["points"]
                return create_grade_detail(
                    question_id=rule.question_id,
                    student_answer=student_answer,
                    correct_answer=str(rule.correct_value),
                    points_awarded=points,
                    max_points=rule.max_points,
                    is_correct=False,
                    feedback=f"Partial credit: within range [{pc_range['min']}, {pc_range['max']}]",
                )

    return create_grade_detail(
        question_id=rule.question_id,
        student_answer=student_answer,
        correct_answer=str(rule.correct_value),
        points_awarded=0.0,
        max_points=rule.max_points,
        is_correct=False,
        feedback=f"✗ Outside acceptable range (difference: {difference:.2f})",
    )
