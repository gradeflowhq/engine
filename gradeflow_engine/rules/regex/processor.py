"""Regex rule grading processor with compiled pattern caching."""

from __future__ import annotations

import re
from functools import lru_cache
from re import Pattern
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models import GradeDetail, Submission
    from .model import RegexRule


@lru_cache(maxsize=256)
def _compile_regex(pattern: str, flags: int) -> Pattern:
    """
    Compile and cache regex patterns for performance.

    Caching prevents recompiling the same patterns when grading multiple submissions.
    With maxsize=256, we can cache up to 256 unique pattern+flags combinations.

    Args:
        pattern: Regex pattern string
        flags: Regex flags (IGNORECASE, MULTILINE, DOTALL, etc.)

    Returns:
        Compiled regex pattern

    Raises:
        re.error: If pattern is invalid
    """
    return re.compile(pattern, flags)


def process_regex(rule: "RegexRule", submission: "Submission") -> "GradeDetail | None":
    """
    Apply a regex-based grading rule to grade a submission.

    Uses LRU cache for compiled patterns to improve performance when
    grading multiple submissions with the same rubric.

    Args:
        rule: The Regex rule to apply
        submission: The student's submission

    Returns:
        GradeDetail with points awarded and feedback
    """
    # Import here to avoid circular dependency
    from ..base import create_grade_detail, get_student_answer

    student_answer = get_student_answer(submission, rule.question_id, strip=False)

    # Build regex flags
    flags = 0
    if not rule.case_sensitive:
        flags |= re.IGNORECASE
    if rule.multiline:
        flags |= re.MULTILINE
    if rule.dotall:
        flags |= re.DOTALL

    # Check each pattern (using cached compiled patterns)
    matches = []
    matched_patterns = []
    for _i, pattern in enumerate(rule.patterns):
        try:
            compiled_pattern = _compile_regex(pattern, flags)
            match = compiled_pattern.search(student_answer)
            matches.append(match is not None)
            if match:
                matched_patterns.append(pattern)
        except re.error as e:
            # Invalid regex pattern
            return create_grade_detail(
                question_id=rule.question_id,
                student_answer=student_answer,
                correct_answer=None,
                points_awarded=0.0,
                max_points=rule.max_points,
                is_correct=False,
                feedback=f"✗ Invalid regex pattern '{pattern}': {str(e)}",
            )

    # Calculate points based on match mode
    points_awarded = 0.0
    is_correct = False

    if rule.match_mode == "all":
        # All patterns must match
        if all(matches):
            points_awarded = rule.max_points
            is_correct = True
        elif rule.partial_credit:
            # Award partial credit
            if isinstance(rule.points_per_match, list):
                points_awarded = sum(
                    rule.points_per_match[i] for i, matched in enumerate(matches) if matched
                )
            else:
                points_awarded = sum(matches) * rule.points_per_match

    elif rule.match_mode == "any":
        # Any pattern match awards points
        if any(matches):
            if isinstance(rule.points_per_match, list):
                points_awarded = max(
                    rule.points_per_match[i] for i, matched in enumerate(matches) if matched
                )
            else:
                points_awarded = rule.points_per_match
            is_correct = True

    elif rule.match_mode == "count":
        # Award points for each match
        if isinstance(rule.points_per_match, list):
            points_awarded = sum(
                rule.points_per_match[i] for i, matched in enumerate(matches) if matched
            )
        else:
            points_awarded = sum(matches) * rule.points_per_match
        is_correct = sum(matches) == len(rule.patterns)

    # Build improved feedback
    match_count = sum(matches)
    total_patterns = len(rule.patterns)

    if match_count == total_patterns:
        feedback = f"✓ Matched all {total_patterns} pattern(s)"
    elif match_count > 0:
        feedback = f"Partial: matched {match_count}/{total_patterns} pattern(s)"
    else:
        feedback = "✗ No patterns matched"

    return create_grade_detail(
        question_id=rule.question_id,
        student_answer=student_answer,
        correct_answer=None,
        points_awarded=points_awarded,
        max_points=rule.max_points,
        is_correct=is_correct,
        feedback=feedback,
    )
