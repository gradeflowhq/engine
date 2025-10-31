"""Base utilities for rule processors to reduce code duplication."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .utils import sanitize_text

if TYPE_CHECKING:
    from ..models import GradeDetail, Submission


__all__ = ["sanitize_text", "get_student_answer", "create_grade_detail"]


def get_student_answer(
    submission: "Submission", question_id: str, default: str = "", strip: bool = True
) -> str:
    """
    Safely extract student answer from submission.

    Args:
        submission: The student's submission
        question_id: Question ID to retrieve
        default: Default value if question not found
        strip: Whether to strip whitespace from answer

    Returns:
        Student's answer as a string
    """
    answer = submission.answers.get(question_id, default)
    if strip:
        return answer.strip()
    return answer


def create_grade_detail(
    question_id: str,
    student_answer: str | None,
    correct_answer: str | None,
    points_awarded: float,
    max_points: float,
    is_correct: bool,
    feedback: str | None = None,
    rule_applied: str | None = None,
) -> "GradeDetail":
    """
    Factory function for creating GradeDetail objects.

    Handles the import to avoid circular dependencies and provides
    a consistent interface for creating grade details.

    Args:
        question_id: Question identifier
        student_answer: Student's answer
        correct_answer: Expected correct answer (if applicable)
        points_awarded: Points awarded for this question
        max_points: Maximum points possible
        is_correct: Whether the answer is correct
        feedback: Optional feedback message
        rule_applied: Optional rule identifier

    Returns:
        GradeDetail instance
    """
    from ..models import GradeDetail

    return GradeDetail(
        question_id=question_id,
        student_answer=student_answer,
        correct_answer=correct_answer,
        points_awarded=points_awarded,
        max_points=max_points,
        is_correct=is_correct,
        feedback=feedback,
        rule_applied=rule_applied,
    )
