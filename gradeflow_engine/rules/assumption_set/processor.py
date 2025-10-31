"""AssumptionSet rule grading processor."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models import GradeDetail, Submission
    from .model import AssumptionSetRule


def process_assumption_set(
    rule: "AssumptionSetRule", submission: "Submission"
) -> list["GradeDetail"]:
    """
    Apply an assumption-based grading rule to grade a submission.

    Tries all answer sets and returns the best one (or first matching one).

    Args:
        rule: The AssumptionSet rule to apply
        submission: The student's submission

    Returns:
        List of GradeDetail for all questions in the set
    """
    # Import here to avoid circular dependency
    from ...models import GradeDetail

    best_details: list[GradeDetail] | None = None
    best_score = -1.0

    # Try each answer set
    for answer_set in rule.answer_sets:
        details = []
        total_score = 0.0

        for question_id in rule.question_ids:
            student_answer = submission.answers.get(question_id, "").strip()
            correct_answer = answer_set.answers.get(question_id, "").strip()

            is_correct = student_answer == correct_answer

            # Determine points for this question
            if rule.points_per_question and question_id in rule.points_per_question:
                max_points = rule.points_per_question[question_id]
            else:
                max_points = 1.0  # Default

            points_awarded = max_points if is_correct else 0.0
            total_score += points_awarded

            details.append(
                GradeDetail(
                    question_id=question_id,
                    student_answer=student_answer,
                    correct_answer=correct_answer,
                    points_awarded=points_awarded,
                    max_points=max_points,
                    is_correct=is_correct,
                    rule_applied=rule.type,
                    feedback=f"Graded using assumption set: {answer_set.name}",
                )
            )

        # Check if this is the best set
        if rule.mode == "first_match" and total_score > 0:
            return details
        elif rule.mode == "favor_best" and total_score > best_score:
            best_score = total_score
            best_details = details

    # Return best set (or first set if none matched)
    return best_details if best_details else []
