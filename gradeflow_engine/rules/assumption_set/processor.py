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

    Tries all answer sets (evaluating rules for each question) and returns
    the best one (or first matching one).

    Args:
        rule: The AssumptionSet rule to apply
        submission: The student's submission

    Returns:
        List of GradeDetail for all questions in the set
    """
    # Import here to avoid circular dependency
    from ..registry import rule_registry

    best_details: list[GradeDetail] | None = None
    best_score = -1.0

    # Try each answer set
    for answer_set in rule.answer_sets:
        details = []
        total_score = 0.0

        for question_id in rule.question_ids:
            # Get the rule for this question in this answer set
            question_rule = answer_set.answers.get(question_id)
            if question_rule is None:
                # No rule for this question in this answer set, skip
                continue

            # Update the question_id for the rule if it has one
            if hasattr(question_rule, "question_id"):
                # Create a copy with updated question_id
                rule_dict = question_rule.model_dump()
                rule_dict["question_id"] = question_id
                question_rule = type(question_rule)(**rule_dict)

            # Get the processor for this rule type
            processor = rule_registry.get_processor(question_rule.type)
            if processor is None:
                # Skip this question if processor not found
                continue

            # Process the rule for this question
            result = processor(question_rule, submission)

            # Handle the result
            if result is None:
                # Rule didn't apply, treat as incorrect
                max_points = _get_max_points(question_rule)
                details.append(
                    _create_failed_detail(
                        question_id=question_id,
                        student_answer=submission.answers.get(question_id, ""),
                        max_points=max_points,
                        assumption_name=answer_set.name,
                        rule_type=rule.type,
                    )
                )
            elif isinstance(result, list):
                # Multiple results (shouldn't happen for single-question rules)
                # Use the first one
                if result:
                    total_score += result[0].points_awarded
                    details.append(_update_feedback(result[0], answer_set.name))
            else:
                # Single result
                total_score += result.points_awarded
                details.append(_update_feedback(result, answer_set.name))

        # Check if this is the best set
        if rule.mode == "first_match" and total_score > 0:
            return details
        elif rule.mode == "favor_best" and total_score > best_score:
            best_score = total_score
            best_details = details

    # Return best set (or empty list if none matched)
    return best_details if best_details else []


def _get_max_points(question_rule: object) -> float:
    """Get max points for a question from the rule or default."""
    # Check if the question rule has max_points
    if hasattr(question_rule, "max_points"):
        return question_rule.max_points  # type: ignore
    # Default
    return 1.0


def _create_failed_detail(
    question_id: str,
    student_answer: str,
    max_points: float,
    assumption_name: str,
    rule_type: str,
) -> "GradeDetail":
    """Create a GradeDetail for a failed evaluation."""
    from ...models import GradeDetail

    return GradeDetail(
        question_id=question_id,
        student_answer=student_answer.strip(),
        correct_answer=None,
        points_awarded=0.0,
        max_points=max_points,
        is_correct=False,
        rule_applied=rule_type,
        feedback=f"Graded using assumption set: {assumption_name}",
    )


def _update_feedback(detail: "GradeDetail", assumption_name: str) -> "GradeDetail":
    """Update feedback to include assumption set name."""
    # Create a copy with updated feedback
    detail_dict = detail.model_dump()
    current_feedback = detail_dict.get("feedback", "")
    assumption_feedback = f"Graded using assumption set: {assumption_name}"

    if current_feedback:
        detail_dict["feedback"] = f"{current_feedback}\n{assumption_feedback}"
    else:
        detail_dict["feedback"] = assumption_feedback

    from ...models import GradeDetail

    return GradeDetail(**detail_dict)
