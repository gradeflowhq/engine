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

    Returns GradeDetail with max_points awarded and feedback.
    """
    # Import here to avoid circular dependency
    from ..base import create_grade_detail, preprocess_text

    logger.debug("Processing exact_match for question %s", rule.question_id)

    student_answer_raw = submission.answers.get(rule.question_id, "")

    # normalize both answers consistently
    correct_normalized = preprocess_text(rule.answer, rule.config)
    student_normalized = preprocess_text(student_answer_raw, rule.config)

    is_correct = student_normalized == correct_normalized
    points_awarded = rule.max_points if is_correct else 0.0

    logger.debug(
        "Question %s: %s - %s/%s max_points",
        rule.question_id,
        "MATCH" if is_correct else "NO MATCH",
        points_awarded,
        rule.max_points,
    )

    feedback = "✓ Correct" if is_correct else f"✗ Expected: {rule.answer}"

    return create_grade_detail(
        question_id=rule.question_id,
        student_answer=student_answer_raw,
        correct_answer=rule.answer,
        points_awarded=points_awarded,
        max_points=rule.max_points,
        is_correct=is_correct,
        feedback=feedback,
    )
