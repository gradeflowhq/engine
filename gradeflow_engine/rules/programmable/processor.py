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

    Uses helper functions to validate the rule code, invoke the sandbox,
    clamp the returned points and build a GradeDetail result.

    Returns:
        GradeDetail with points awarded and feedback, or raises on invalid rule.
    """
    from ...sandbox import SandboxExecutionError, SandboxTimeoutError, execute_programmable_rule
    from ..base import create_grade_detail

    def _validate_code(code: str) -> None:
        """Validate that the rule code exists and is non-empty."""
        if not code or not code.strip():
            raise ValueError("Programmable rule code cannot be empty")

    def _run_script(
        code: str, submission: "Submission", question_id: str, answer: str
    ) -> tuple[float, str]:
        """
        Execute the programmable script via the sandbox.

        Notes:
            - The sandbox module manages time/memory limits; do not pass limits here.
            - Raises SandboxExecutionError / SandboxTimeoutError / ValueError as appropriate.
        """
        points_awarded, feedback = execute_programmable_rule(
            script=code,
            student_answers=submission.answers,
            question_id=question_id,
            answer=answer,
        )
        return points_awarded, feedback

    def _clamp_points(points: float, max_points: float) -> float:
        """Clamp points to the valid range [0, max_points]."""
        return max(0.0, min(points, max_points))

    # Extract student's answer for the target question
    student_answer = submission.answers.get(rule.question_id, "")

    # Validate rule payload
    _validate_code(rule.code)

    try:
        # Execute script (sandbox handles limits)
        points_awarded, feedback = _run_script(
            code=rule.code,
            submission=submission,
            question_id=rule.question_id,
            answer=student_answer,
        )

        # Normalize points and determine correctness
        points_awarded = _clamp_points(float(points_awarded), rule.max_points)
        is_correct = points_awarded >= rule.max_points

        return create_grade_detail(
            question_id=rule.question_id,
            student_answer=student_answer,
            correct_answer=None,
            points_awarded=points_awarded,
            max_points=rule.max_points,
            is_correct=is_correct,
            feedback=feedback or None,
            rule_applied=None,
        )

    except (SandboxExecutionError, SandboxTimeoutError) as e:
        # Script failed: award 0 points and include error info in feedback
        return create_grade_detail(
            question_id=rule.question_id,
            student_answer=student_answer,
            correct_answer=None,
            points_awarded=0.0,
            max_points=rule.max_points,
            is_correct=False,
            feedback=f"Grading script error: {str(e)}",
            rule_applied=None,
        )
