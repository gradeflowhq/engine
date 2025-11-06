"""MultipleChoice rule grading processor."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models import GradeDetail, Submission
    from .model import MultipleChoiceRule, MultipleChoiceRuleConfig


from ..base import create_grade_detail, preprocess_text
from ..utils import format_feedback


def _parse_student_choices(raw: str, config: "MultipleChoiceRuleConfig") -> set[str]:
    """Normalize a raw student answer into a set of preprocessed choices."""
    if not raw:
        return set()
    # Split using configured delimiter, then preprocess each token
    tokens = raw.split(config.delimiter)
    choices: set[str] = set()
    for t in tokens:
        t_proc = preprocess_text(t, config)
        if t_proc:
            choices.add(t_proc)
    return choices


def _calc_all_and_partial(
    rule: "MultipleChoiceRule", student_choices: set[str], correct_choices: set[str]
) -> tuple[float, bool, str]:
    """
    Calculate points, correctness and feedback for supported modes.

    Returns:
        (points_awarded, is_correct, feedback)
    """
    matched = student_choices & correct_choices
    incorrect = student_choices - correct_choices

    # Use configured delimiter for displaying expected answers
    display_delim = f"{rule.config.delimiter} "

    if rule.mode == "all":
        if student_choices == correct_choices:
            return (
                rule.max_points,
                True,
                format_feedback(True, expected=display_delim.join(sorted(rule.answers))),
            )
        return 0.0, False, format_feedback(False, expected=display_delim.join(sorted(rule.answers)))

    if rule.mode == "partial":
        if not correct_choices:
            return (
                0.0,
                False,
                format_feedback(False, expected=None, details="No correct answers configured"),
            )
        points = (len(matched) / len(correct_choices)) * rule.max_points
        is_correct = len(matched) == len(correct_choices) and len(incorrect) == 0
        details = f"Matched {len(matched)}/{len(correct_choices)}"
        if incorrect:
            details += f" - Incorrect selections: {len(incorrect)}"
        return (
            points,
            is_correct,
            format_feedback(
                is_correct, expected=display_delim.join(sorted(rule.answers)), details=details
            ),
        )

    # Unknown mode — fail fast so future modes are explicit
    raise ValueError(f"Unsupported MultipleChoice mode: {rule.mode}")


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
    student_answer = submission.answers.get(rule.question_id, "")
    student_choices = _parse_student_choices(student_answer, rule.config)

    # Preprocess configured correct answers using the same config
    correct_choices = {preprocess_text(ans, rule.config) for ans in rule.answers}

    points_awarded, is_correct, feedback = _calc_all_and_partial(
        rule, student_choices, correct_choices
    )

    # Display correct answer joined with configured delimiter
    display_delim = f"{rule.config.delimiter} "
    return create_grade_detail(
        question_id=rule.question_id,
        student_answer=student_answer,
        correct_answer=display_delim.join(sorted(rule.answers)),
        points_awarded=points_awarded,
        max_points=rule.max_points,
        is_correct=is_correct,
        feedback=feedback,
        rule_applied=rule.type,
    )
