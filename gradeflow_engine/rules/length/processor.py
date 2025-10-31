"""Length rule grading processor."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models import GradeDetail, Submission
    from .model import LengthRule


def process_length(rule: "LengthRule", submission: "Submission") -> "GradeDetail | None":
    """
    Apply a length constraint rule to grade a submission.

    Args:
        rule: The Length rule to apply
        submission: The student's submission

    Returns:
        GradeDetail with points awarded and feedback
    """
    from ..base import create_grade_detail, get_student_answer

    student_answer = get_student_answer(submission, rule.question_id)

    word_count = len(student_answer.split())
    char_count = len(student_answer)

    violations = []

    if rule.min_words is not None and word_count < rule.min_words:
        violations.append(f"Too few words ({word_count} < {rule.min_words})")
    if rule.max_words is not None and word_count > rule.max_words:
        violations.append(f"Too many words ({word_count} > {rule.max_words})")
    if rule.min_chars is not None and char_count < rule.min_chars:
        violations.append(f"Too few characters ({char_count} < {rule.min_chars})")
    if rule.max_chars is not None and char_count > rule.max_chars:
        violations.append(f"Too many characters ({char_count} > {rule.max_chars})")

    if violations:
        # Deduct points for violations
        if rule.strict:
            points_awarded = 0.0
        elif rule.deduct_per_violation:
            deduction = min(len(violations) * rule.deduct_per_violation, rule.max_points)
            points_awarded = rule.max_points - deduction
        else:
            points_awarded = 0.0

        return create_grade_detail(
            question_id=rule.question_id,
            student_answer=student_answer,
            correct_answer=None,
            points_awarded=points_awarded,
            max_points=rule.max_points,
            is_correct=False,
            feedback=f"Length constraints violated: {'; '.join(violations)}",
        )
    else:
        return create_grade_detail(
            question_id=rule.question_id,
            student_answer=student_answer,
            correct_answer=None,
            points_awarded=rule.max_points,
            max_points=rule.max_points,
            is_correct=True,
            feedback=f"Length constraints met (words: {word_count}, chars: {char_count})",
        )
