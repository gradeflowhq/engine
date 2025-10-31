"""Keyword rule grading processor."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models import GradeDetail, Submission
    from .model import KeywordRule


def process_keyword(rule: "KeywordRule", submission: "Submission") -> "GradeDetail | None":
    """
    Apply a keyword-based grading rule to grade a submission.

    Args:
        rule: The Keyword rule to apply
        submission: The student's submission

    Returns:
        GradeDetail with points awarded and feedback
    """
    # Import here to avoid circular dependency
    from ..base import create_grade_detail, get_student_answer

    student_answer = get_student_answer(submission, rule.question_id, strip=True)

    # Prepare answer for matching
    answer_to_check = student_answer if rule.case_sensitive else student_answer.lower()

    # Check required keywords
    found_required: list[str] = []
    missing_required: list[str] = []
    for keyword in rule.required_keywords:
        keyword_to_check = keyword if rule.case_sensitive else keyword.lower()
        if keyword_to_check in answer_to_check:
            found_required.append(keyword)
        else:
            missing_required.append(keyword)

    # Check optional keywords
    found_optional: list[str] = []
    for keyword in rule.optional_keywords:
        keyword_to_check = keyword if rule.case_sensitive else keyword.lower()
        if keyword_to_check in answer_to_check:
            found_optional.append(keyword)

    # Calculate points
    required_points = len(found_required) * rule.points_per_required
    optional_points = len(found_optional) * rule.points_per_optional

    # Apply max optional points limit
    if rule.max_optional_points is not None:
        optional_points = min(optional_points, rule.max_optional_points)

    points_awarded = required_points + optional_points

    # Determine if partial credit applies
    if not rule.partial_credit and missing_required:
        points_awarded = optional_points  # Only award optional points if required keywords missing

    max_points = rule.max_points
    is_correct = len(missing_required) == 0

    # Build improved feedback
    feedback_parts: list[str] = []
    if missing_required:
        feedback_parts.append(f"✗ Missing required: {', '.join(missing_required)}")
    elif found_required:
        feedback_parts.append("✓ Found all required keywords")

    if found_optional:
        feedback_parts.append(f"+ Bonus: {', '.join(found_optional)}")

    feedback = "; ".join(feedback_parts) if feedback_parts else "No keywords found"

    return create_grade_detail(
        question_id=rule.question_id,
        student_answer=student_answer,
        correct_answer=None,
        points_awarded=points_awarded,
        max_points=max_points,
        is_correct=is_correct,
        feedback=feedback,
    )
