"""Programmable rule grading processor."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models import GradeDetail, Submission
    from .model import ProgrammableRule


def process_programmable(
    rule: "ProgrammableRule", submission: "Submission"
) -> "GradeDetail | None":
    """
    Apply a programmable grading rule to grade a submission.

    Executes the custom Python script in a sandboxed environment.

    Args:
        rule: The Programmable rule to apply
        submission: The student's submission

    Returns:
        GradeDetail with points awarded and feedback
    """
    from ...sandbox import SandboxExecutionError, SandboxTimeoutError, execute_programmable_rule
    from ..base import create_grade_detail, get_student_answer

    student_answer = get_student_answer(submission, rule.question_id)

    try:
        points_awarded, feedback = execute_programmable_rule(
            script=rule.script,
            student_answers=submission.answers,
            question_id=rule.question_id,
            answer=student_answer,
            timeout_ms=rule.timeout_ms,
            memory_mb=rule.memory_mb,
        )

        # Clamp points to valid range
        points_awarded = max(0.0, min(points_awarded, rule.max_points))

        is_correct = points_awarded >= rule.max_points

        return create_grade_detail(
            question_id=rule.question_id,
            student_answer=student_answer,
            correct_answer=None,
            points_awarded=points_awarded,
            max_points=rule.max_points,
            is_correct=is_correct,
            feedback=feedback or None,
        )

    except (SandboxExecutionError, SandboxTimeoutError) as e:
        # Script failed, award 0 points and include error in feedback
        return create_grade_detail(
            question_id=rule.question_id,
            student_answer=student_answer,
            correct_answer=None,
            points_awarded=0.0,
            max_points=rule.max_points,
            is_correct=False,
            feedback=f"Grading script error: {str(e)}",
        )
