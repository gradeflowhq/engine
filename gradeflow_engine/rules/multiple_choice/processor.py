"""MultipleChoice rule grading processor."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models import GradeDetail, Submission
    from .model import MultipleChoiceRule


def process_multiple_choice(
    rule: "MultipleChoiceRule", submission: "Submission"
) -> "GradeDetail | None":
    """
    Apply a multiple choice rule to grade a submission.

    Args:
        rule: The MultipleChoice rule to apply
        submission: The student's submission

    Returns:
        GradeDetail with points awarded and feedback
    """
    # Import here to avoid circular dependency
    from ...models import GradeDetail

    student_answer = submission.answers.get(rule.question_id, "").strip()

    # Parse student answer - could be single or multiple choices
    # Expect comma-separated or semicolon-separated format for multiple answers
    student_choices = {c.strip() for c in student_answer.replace(";", ",").split(",") if c.strip()}

    # Apply case sensitivity
    if not rule.case_sensitive:
        student_choices = {c.lower() for c in student_choices}
        correct_choices = {c.lower() for c in rule.correct_answers}
    else:
        correct_choices = set(rule.correct_answers)

    matched = student_choices & correct_choices
    incorrect = student_choices - correct_choices

    # Calculate points based on scoring mode
    points_awarded = 0.0
    is_correct = False
    feedback = ""

    if rule.scoring_mode == "all_or_nothing":
        if student_choices == correct_choices:
            points_awarded = rule.max_points
            is_correct = True
            feedback = "All correct"
        else:
            feedback = f"Incorrect. Expected: {', '.join(sorted(rule.correct_answers))}"

    elif rule.scoring_mode == "partial":
        if len(correct_choices) > 0:
            points_awarded = (len(matched) / len(correct_choices)) * rule.max_points
            is_correct = len(matched) == len(correct_choices) and len(incorrect) == 0
            feedback = f"Matched {len(matched)}/{len(correct_choices)} correct choices"

    elif rule.scoring_mode == "negative":
        # Award points for correct, deduct for incorrect
        if len(correct_choices) > 0:
            points_per_correct = rule.max_points / len(correct_choices)
            points_awarded = (
                len(matched) * points_per_correct - len(incorrect) * rule.penalty_per_wrong
            )
            points_awarded = max(0.0, points_awarded)  # Don't go negative
            is_correct = len(matched) == len(correct_choices) and len(incorrect) == 0
            feedback = f"Correct: {len(matched)}, Incorrect: {len(incorrect)}"

    return GradeDetail(
        question_id=rule.question_id,
        student_answer=student_answer,
        correct_answer=", ".join(sorted(rule.correct_answers)),
        points_awarded=points_awarded,
        max_points=rule.max_points,
        is_correct=is_correct,
        rule_applied=rule.type,
        feedback=feedback,
    )
