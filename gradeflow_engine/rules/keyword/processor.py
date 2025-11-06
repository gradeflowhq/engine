"""Keyword rule grading processor."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models import GradeDetail, Submission
    from ..base import TextRuleConfig
    from .model import KeywordRule


def process_keyword(rule: "KeywordRule", submission: "Submission") -> "GradeDetail | None":
    """
    Apply a keyword-based grading rule to grade a submission.

    Args:
        rule: The Keyword rule to apply
        submission: The student's submission

    Returns:
        GradeDetail with max_points awarded and feedback
    """
    # Import here to avoid circular dependency
    from ..base import create_grade_detail

    # Extract student answer; rule.config.trim_whitespace is guaranteed to exist
    student_answer = submission.answers.get(rule.question_id, "")

    # Match keywords using centralized config handling
    found_keywords, missing_keywords = match_keywords(student_answer, rule.keywords, rule.config)

    points_awarded = compute_points(
        rule.mode, rule.max_points, len(rule.keywords), len(found_keywords)
    )

    # Determine correctness: for 'all' mode require all keywords, otherwise any positive points
    if rule.mode == "all":
        is_correct = len(found_keywords) == len(rule.keywords)
    else:
        is_correct = points_awarded >= float(rule.max_points)

    feedback = format_keyword_feedback(
        found_keywords=found_keywords, missing_keywords=missing_keywords, mode=rule.mode
    )

    return create_grade_detail(
        question_id=rule.question_id,
        student_answer=student_answer,
        correct_answer="Keywords: " + ", ".join(rule.keywords),
        points_awarded=points_awarded,
        max_points=rule.max_points,
        is_correct=is_correct,
        feedback=feedback,
        rule_applied=getattr(rule, "type", None),
    )


def match_keywords(
    answer: str, keywords: list[str], config: TextRuleConfig
) -> tuple[list[str], list[str]]:
    """
    Return (found, missing) lists of keywords for the given answer.

    Preserves original keyword strings in the returned lists for clearer feedback.
    """
    from ..base import preprocess_text

    norm_answer = preprocess_text(answer, config)
    found: list[str] = []
    missing: list[str] = []
    for kw in keywords:
        norm_kw = preprocess_text(kw, config)
        if norm_kw and norm_kw in norm_answer:
            found.append(kw)
        else:
            missing.append(kw)
    return found, missing


def compute_points(mode: str, max_points: float, total_keywords: int, found_count: int) -> float:
    """Compute awarded points based on mode ('all'|'partial')."""
    if total_keywords <= 0:
        return 0.0
    if mode == "all":
        return float(max_points) if found_count == total_keywords else 0.0
    if mode == "any":
        return float(max_points) if found_count >= 1 else 0.0
    # partial
    per_kw = float(max_points) / total_keywords
    return per_kw * found_count


def format_keyword_feedback(
    found_keywords: list[str], missing_keywords: list[str], mode: str = "all"
) -> str:
    """
    Format feedback for keyword-based grading.

    Args:
        found_keywords: List of required keywords found
        missing_keywords: List of required keywords missing

    Returns:
        Formatted feedback string
    """
    parts: list[str] = []

    if mode == "all":
        if missing_keywords:
            parts.append(f"✗ Missing keywords: {', '.join(missing_keywords)}")
        elif found_keywords:
            parts.append("✓ Found all keywords")
    elif mode == "partial":
        if found_keywords:
            parts.append(f"✓ Found keywords: {', '.join(found_keywords)}")
        if missing_keywords:
            parts.append(f"✗ Missing keywords: {', '.join(missing_keywords)}")
    elif mode == "any":
        if found_keywords:
            parts.append(f"✓ Found keyword(s): {', '.join(found_keywords)}")
        else:
            parts.append("✗ No required keywords found")

    return "; ".join(parts) if parts else "No keywords found"
