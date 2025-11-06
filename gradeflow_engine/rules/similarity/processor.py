"""Similarity rule grading processor."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler, Levenshtein

if TYPE_CHECKING:
    from ...models import GradeDetail, Submission
    from .model import SimilarityRule

logger = logging.getLogger(__name__)


def format_similarity_feedback(similarity: float, threshold: float) -> str:
    """
    Format feedback for similarity-based grading.

    Args:
        similarity: Similarity score (0-1)
        threshold: Threshold for passing

    Returns:
        Formatted feedback string
    """
    if similarity >= threshold:
        return f"✓ Match: {similarity:.0%} (threshold: {threshold:.0%})"
    return f"✗ Insufficient similarity: {similarity:.0%} < {threshold:.0%}"


def _select_similarity_func(algorithm: str) -> Callable[[str, str], float]:
    """
    Return a function that computes a normalized similarity in [0.0, 1.0]
    for the given algorithm name.
    """
    alg = (algorithm or "levenshtein").lower()

    if alg == "levenshtein":
        return lambda a, b: Levenshtein.normalized_similarity(a, b)
    if alg == "jaro_winkler":
        return lambda a, b: JaroWinkler.normalized_similarity(a, b)
    if alg == "token_sort":
        return lambda a, b: fuzz.token_sort_ratio(a, b) / 100.0

    # default fallback
    return lambda a, b: Levenshtein.normalized_similarity(a, b)


def _compute_similarity(a: str, b: str, algorithm: str) -> float:
    """Compute similarity between two pre-normalized strings using algorithm."""
    func = _select_similarity_func(algorithm)
    try:
        return float(func(a, b))
    except Exception:
        logger.exception("Error computing similarity using %s", algorithm)
        return 0.0


def process_similarity(rule: "SimilarityRule", submission: "Submission") -> "GradeDetail | None":
    """
    Apply a fuzzy similarity rule to grade a submission.

    Uses rapidfuzz library for high-performance string similarity calculations.

    Args:
        rule: The Similarity rule to apply
        submission: The student's submission

    Returns:
        GradeDetail with max_points awarded and feedback
    """
    # Import here to avoid circular dependency
    from ..base import create_grade_detail, preprocess_text

    logger.debug(
        f"Processing similarity for question {rule.question_id} using {rule.config.algorithm}"
    )

    # Get raw student answer (keep existing get_student_answer usage / semantics)
    student_answer_raw = submission.answers.get(rule.question_id, "")

    # Normalize both student answer and reference using rule.config
    student_answer_norm = preprocess_text(student_answer_raw, rule.config)
    reference_norm = preprocess_text(rule.reference, rule.config)

    # If both are empty, treat as exact match
    if not student_answer_norm and not reference_norm:
        similarity = 1.0
    else:
        similarity = _compute_similarity(student_answer_norm, reference_norm, rule.config.algorithm)

    logger.debug("Computed similarity: %.2f (threshold: %.2f)", similarity, rule.threshold)

    if similarity >= rule.threshold:
        points_awarded = rule.max_points
        is_correct = similarity >= 0.95
        feedback = format_similarity_feedback(similarity, rule.threshold)
        logger.debug(
            "Question %s: PASS - %s/%s max_points",
            rule.question_id,
            points_awarded,
            rule.max_points,
        )
    else:
        points_awarded = 0.0
        is_correct = False
        feedback = format_similarity_feedback(similarity, rule.threshold)
        logger.debug("Question %s: FAIL - below threshold", rule.question_id)

    return create_grade_detail(
        question_id=rule.question_id,
        student_answer=student_answer_raw,
        correct_answer=rule.reference,
        points_awarded=points_awarded,
        max_points=rule.max_points,
        is_correct=is_correct,
        feedback=feedback,
        rule_applied=getattr(rule, "type", None),
    )
