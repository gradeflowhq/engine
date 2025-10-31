"""Conditional rule grading processor."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models import GradeDetail, Submission
    from .model import ConditionalRule


def process_conditional(rule: "ConditionalRule", submission: "Submission") -> "GradeDetail | None":
    """
    Apply a conditional grading rule to grade a submission.

    Only applies if the condition is met (if_question has if_answer).

    Args:
        rule: The Conditional rule to apply
        submission: The student's submission

    Returns:
        GradeDetail if condition is met, None otherwise
    """
    # Import here to avoid circular dependency
    from ...models import GradeDetail

    # Check if condition is met
    if_answer = submission.answers.get(rule.if_question, "").strip()

    if if_answer != rule.if_answer.strip():
        # Condition not met, don't grade this question with this rule
        return None

    # Condition met, grade the then_question
    student_answer = submission.answers.get(rule.then_question, "").strip()
    correct_answer = rule.then_correct_answer.strip()

    is_correct = student_answer == correct_answer
    points_awarded = rule.max_points if is_correct else 0.0

    return GradeDetail(
        question_id=rule.then_question,
        student_answer=student_answer,
        correct_answer=correct_answer,
        points_awarded=points_awarded,
        max_points=rule.max_points,
        is_correct=is_correct,
        rule_applied=rule.type,
        feedback=rule.description if not is_correct else None,
    )
