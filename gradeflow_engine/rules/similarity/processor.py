"""Similarity rule grading processor."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler, Levenshtein

if TYPE_CHECKING:
    from ...models import GradeDetail, Submission
    from .model import SimilarityRule

logger = logging.getLogger(__name__)


def process_similarity(rule: "SimilarityRule", submission: "Submission") -> "GradeDetail | None":
    """
    Apply a fuzzy similarity rule to grade a submission.

    Uses rapidfuzz library for high-performance string similarity calculations.

    Args:
        rule: The Similarity rule to apply
        submission: The student's submission

    Returns:
        GradeDetail with points awarded and feedback
    """
    # Import here to avoid circular dependency
    from ..base import create_grade_detail, get_student_answer

    logger.debug(f"Processing similarity for question {rule.question_id} using {rule.algorithm}")

    student_answer = get_student_answer(submission, rule.question_id, strip=True)

    # Apply case sensitivity
    if not rule.case_sensitive:
        student_answer_check = student_answer.lower()
        reference_answers = [ref.lower() for ref in rule.reference_answers]
    else:
        student_answer_check = student_answer
        reference_answers = rule.reference_answers

    # Calculate maximum similarity against all reference answers
    max_similarity = 0.0
    best_reference = reference_answers[0] if reference_answers else ""

    for ref_answer in reference_answers:
        ref_answer = ref_answer.strip()

        if rule.algorithm == "levenshtein":
            similarity = Levenshtein.normalized_similarity(student_answer_check, ref_answer)
        elif rule.algorithm == "jaro_winkler":
            similarity = JaroWinkler.normalized_similarity(student_answer_check, ref_answer)
        elif rule.algorithm == "token_sort":
            similarity = fuzz.token_sort_ratio(student_answer_check, ref_answer) / 100.0
        else:
            # Default to Levenshtein
            similarity = Levenshtein.normalized_similarity(student_answer_check, ref_answer)

        if similarity > max_similarity:
            max_similarity = similarity
            best_reference = ref_answer

    logger.debug(f"Best similarity: {max_similarity:.2%} (threshold: {rule.threshold:.0%})")

    # Award points based on similarity threshold
    if max_similarity >= rule.threshold:
        if rule.partial_credit:
            # Linear interpolation between threshold and 1.0
            if max_similarity >= 1.0:
                points_awarded = rule.max_points
            else:
                # Scale points based on how close to perfect match
                # Range: [threshold, 1.0] -> [partial_credit_min * max_points, max_points]
                points_awarded = rule.max_points * (
                    rule.partial_credit_min
                    + (1.0 - rule.partial_credit_min)
                    * ((max_similarity - rule.threshold) / (1.0 - rule.threshold))
                )
        else:
            points_awarded = rule.max_points

        is_correct = max_similarity >= 0.95
        feedback = f"✓ Match: {max_similarity:.0%} (threshold: {rule.threshold:.0%})"
        logger.debug(
            f"Question {rule.question_id}: PASS - {points_awarded}/{rule.max_points} points"
        )
    else:
        points_awarded = 0.0
        is_correct = False
        feedback = f"✗ Insufficient similarity: {max_similarity:.0%} < {rule.threshold:.0%}"
        logger.debug(f"Question {rule.question_id}: FAIL - below threshold")

    return create_grade_detail(
        question_id=rule.question_id,
        student_answer=student_answer,
        correct_answer=best_reference,
        points_awarded=points_awarded,
        max_points=rule.max_points,
        is_correct=is_correct,
        feedback=feedback,
    )
