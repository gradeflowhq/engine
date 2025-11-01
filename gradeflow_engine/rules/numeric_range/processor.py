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
            correct_answer=f"[{rule.min_value}, {rule.max_value}]",
            points_awarded=0.0,
            max_points=rule.max_points,
            is_correct=False,
            feedback="✗ Invalid numeric value",
        )

    # Check if within acceptable range
    if rule.min_value <= student_value <= rule.max_value:
        return create_grade_detail(
            question_id=rule.question_id,
            student_answer=student_answer,
            correct_answer=f"[{rule.min_value}, {rule.max_value}]",
            points_awarded=rule.max_points,
            max_points=rule.max_points,
            is_correct=True,
            feedback=f"✓ Within acceptable range [{rule.min_value}, {rule.max_value}]",
        )

    # Check partial credit ranges
    if rule.partial_credit_ranges:
        for pc_range in rule.partial_credit_ranges:
            if pc_range["min"] <= student_value <= pc_range["max"]:
                points = pc_range["points"]
                return create_grade_detail(
                    question_id=rule.question_id,
                    student_answer=student_answer,
                    correct_answer=f"[{rule.min_value}, {rule.max_value}]",
                    points_awarded=points,
                    max_points=rule.max_points,
                    is_correct=False,
                    feedback=f"Partial credit: within range [{pc_range['min']}, {pc_range['max']}]",
                )

    # Outside all acceptable ranges
    if student_value < rule.min_value:
        difference = rule.min_value - student_value
        feedback = f"✗ Below minimum (difference: {difference:.2f})"
    else:
        difference = student_value - rule.max_value
        feedback = f"✗ Above maximum (difference: {difference:.2f})"

    return create_grade_detail(
        question_id=rule.question_id,
        student_answer=student_answer,
        correct_answer=f"[{rule.min_value}, {rule.max_value}]",
        points_awarded=0.0,
        max_points=rule.max_points,
        is_correct=False,
        feedback=feedback,
    )
