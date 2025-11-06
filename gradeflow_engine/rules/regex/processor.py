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
def _compile_regex(pattern: str, flags: int) -> Pattern[str]:
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


def _build_regex_flags_from_rule(rule: "RegexRule") -> int:
    """
    Build regex flags from the rule.config. Assumes the model guarantees
    the presence and types of the config fields (no legacy fallbacks).
    """
    cfg = rule.config
    flags = 0
    if cfg.ignore_case:
        flags |= re.IGNORECASE
    if cfg.multi_line:
        flags |= re.MULTILINE
    if cfg.dotall:
        flags |= re.DOTALL
    return flags


def _search_pattern(pattern: str, text: str, flags: int) -> bool:
    """Compile (cached) the pattern with flags and search the text."""
    compiled = _compile_regex(pattern, flags)
    return compiled.search(text) is not None


def process_regex(rule: "RegexRule", submission: "Submission") -> "GradeDetail | None":
    """
    Apply a single-pattern regex rule to a submission.

    Assumptions:
    - RegexRule.pattern and RegexRule.config are present and validated by the model.
    - Use submission.answers directly to avoid circular imports.
    """
    # Import factory here to avoid circular dependency at module import time
    from ..base import create_grade_detail

    # Safely get the student's answer for the question (default to empty string)
    student_answer = submission.answers.get(rule.question_id, "") or ""

    # Build flags from the rule config (model guarantees fields)
    flags = _build_regex_flags_from_rule(rule)

    # Try to compile/search; model validation should prevent errors but handle defensively
    try:
        matched = _search_pattern(rule.pattern, student_answer, flags)
    except re.error as e:
        return create_grade_detail(
            question_id=rule.question_id,
            student_answer=student_answer,
            correct_answer=None,
            points_awarded=0.0,
            max_points=rule.max_points,
            is_correct=False,
            feedback=f"✗ Invalid regex pattern '{rule.pattern}': {e}",
            rule_applied=rule.type,
        )

    points_awarded = float(rule.max_points) if matched else 0.0
    is_correct = bool(matched)
    feedback = "✓ Pattern matched" if matched else "✗ Pattern did not match"

    return create_grade_detail(
        question_id=rule.question_id,
        student_answer=student_answer,
        correct_answer=None,
        points_awarded=points_awarded,
        max_points=rule.max_points,
        is_correct=is_correct,
        feedback=feedback,
        rule_applied=rule.type,
    )
