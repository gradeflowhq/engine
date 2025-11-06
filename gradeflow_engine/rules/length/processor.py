"""Length rule grading processor."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models import GradeDetail, Submission
    from .model import LengthRule


# Module-level helpers (moved out of the function for reuse/testing)
def count_answer(answer: str, mode: str) -> int:
    """Return token count based on mode ('words'|'characters')."""
    if mode == "words":
        # split on whitespace, ignore empty tokens
        return len([t for t in answer.split() if t])
    # default to characters
    return len(answer)


def violations_for(count: int, min_len: int | None, max_len: int | None) -> list[str]:
    """Return a list of human-readable violation messages for the given count."""
    v: list[str] = []
    if min_len is not None and count < min_len:
        v.append(f"Too short ({count} < {min_len})")
    if max_len is not None and count > max_len:
        v.append(f"Too long ({count} > {max_len})")
    return v


def process_length(rule: "LengthRule", submission: "Submission") -> "GradeDetail | None":
    """
    Apply a length constraint rule to grade a submission.

    Args:
        rule: The Length rule to apply
        submission: The student's submission

    Returns:
        GradeDetail with max_points awarded and feedback
    """
    # Import inside function to avoid circular imports at module import time
    from ..base import create_grade_detail
    from ..utils import format_feedback

    student_answer = submission.answers.get(rule.question_id, "")
    # compute count using module-level helper
    mode = rule.mode
    count = count_answer(student_answer, mode)
    violations = violations_for(count, rule.min_length, rule.max_length)
    correct_answer = f"Length within {rule.min_length or '-'}..{rule.max_length or '-'} {mode}"

    if violations:
        points_awarded = 0.0
        feedback = format_feedback(
            is_correct=False,
            expected=f"{rule.min_length or '-'}..{rule.max_length or '-'} {mode}",
            details=f"Length constraints violated: {'; '.join(violations)} (actual: {count})",
        )
        return create_grade_detail(
            question_id=rule.question_id,
            student_answer=student_answer,
            correct_answer=correct_answer,
            points_awarded=points_awarded,
            max_points=rule.max_points,
            is_correct=False,
            feedback=feedback,
            rule_applied=getattr(rule, "type", None),
        )

    feedback = format_feedback(
        is_correct=True,
        details=f"Length constraints met (actual: {count}, "
        "expected: {rule.min_length or '-'}..{rule.max_length or '-'} {mode})",
    )
    return create_grade_detail(
        question_id=rule.question_id,
        student_answer=student_answer,
        correct_answer=correct_answer,
        points_awarded=rule.max_points,
        max_points=rule.max_points,
        is_correct=True,
        feedback=feedback,
        rule_applied=getattr(rule, "type", None),
    )
