"""
Exact Match Rule processor.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models import GradeDetail, Submission
    from .model import ExactMatchRule

logger = logging.getLogger(__name__)


def process_exact_match(rule: "ExactMatchRule", submission: "Submission") -> "GradeDetail | None":
    """
    Apply an exact match rule to grade a submission.

    Args:
        rule: The ExactMatch rule to apply
        submission: The student's submission

    Returns:
        GradeDetail with points awarded and feedback
    """
    # Import here to avoid circular dependency
    from ..base import create_grade_detail, get_student_answer

    logger.debug(f"Processing exact_match for question {rule.question_id}")

    student_answer = get_student_answer(submission, rule.question_id, strip=rule.trim_whitespace)

    # Apply transformations to both answers
    correct = rule.correct_answer
    student = student_answer

    if rule.trim_whitespace:
        correct = correct.strip()
        # student already stripped by get_student_answer

    if not rule.case_sensitive:
        correct = correct.lower()
        student = student.lower()

    # Compare
    is_correct = student == correct
    points_awarded = rule.max_points if is_correct else 0.0

    logger.debug(
        f"Question {rule.question_id}: "
        f"{'MATCH' if is_correct else 'NO MATCH'} - "
        f"{points_awarded}/{rule.max_points} points"
    )

    feedback = "✓ Correct" if is_correct else f"✗ Expected: {rule.correct_answer}"

    return create_grade_detail(
        question_id=rule.question_id,
        student_answer=student_answer,
        correct_answer=rule.correct_answer,
        points_awarded=points_awarded,
        max_points=rule.max_points,
        is_correct=is_correct,
        feedback=feedback,
    )
