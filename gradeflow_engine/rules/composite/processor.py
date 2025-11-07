"""Composite rule grading processor."""

from __future__ import annotations

from functools import reduce
from operator import mul
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from ...models import GradeDetail, Submission
    from .model import CompositeRule


def _agg_max(details: list["GradeDetail"]) -> tuple[float, float, bool]:
    """Return the best single sub-result (points_awarded, max_points, is_correct)."""
    best = max(details, key=lambda d: d.points_awarded)
    return best.points_awarded, best.max_points, best.is_correct


def _agg_min(details: list["GradeDetail"]) -> tuple[float, float, bool]:
    """Return the weakest single sub-result (points_awarded, max_points, is_correct)."""
    worst = min(details, key=lambda d: d.points_awarded)
    return worst.points_awarded, worst.max_points, worst.is_correct


def _agg_sum(details: list["GradeDetail"]) -> tuple[float, float, bool]:
    """Sum points and max_points. Consider correct only if all sub-rules are correct."""
    total_points = sum(d.points_awarded for d in details)
    total_max = sum(d.max_points for d in details)
    all_correct = all(d.is_correct for d in details)
    return total_points, total_max, all_correct


def _agg_average(details: list["GradeDetail"]) -> tuple[float, float, bool]:
    """Average points and max_points. Correct if all sub-rules are correct."""
    n = len(details)
    avg_points = sum(d.points_awarded for d in details) / n
    avg_max = sum(d.max_points for d in details) / n
    all_correct = all(d.is_correct for d in details)
    return avg_points, avg_max, all_correct


def _agg_multiply(details: list["GradeDetail"]) -> tuple[float, float, bool]:
    """Multiply points and max_points. Correct if all sub-rules are correct."""
    multiplied_points = reduce(mul, (d.points_awarded for d in details), 1.0)
    multiplied_max = reduce(mul, (d.max_points for d in details), 1.0)
    all_correct = all(d.is_correct for d in details)
    return multiplied_points, multiplied_max, all_correct


# Aggregator dispatch map - easy to extend with new strategies
_AGGREGATORS = {
    "max": _agg_max,
    "min": _agg_min,
    "sum": _agg_sum,
    "average": _agg_average,
    "multiply": _agg_multiply,
}


def _format_feedback(aggregation: str, details: list["GradeDetail"]) -> str:
    """Create compact feedback summarizing the composite evaluation."""
    parts = [f"Composite ({aggregation.upper()}) of {len(details)} sub-rules"]
    # Include a short summary of sub-rule outcomes (e.g., "2/3 passed")
    passed = sum(1 for d in details if d.is_correct)
    parts.append(f"{passed}/{len(details)} passed")
    return " - ".join(parts)


def process_composite(rule: "CompositeRule", submission: "Submission") -> "GradeDetail":
    """
    Apply a composite rule by evaluating all sub-rules on the same question
    and aggregating their results according to rule.mode.

    Returns a single GradeDetail summarizing the composite result.
    """
    # Import here to avoid circular dependency
    from ...models import GradeDetail
    from ..registry import rule_registry

    # Collect sub-rule results (override question_id to composite question)
    sub_results: list[GradeDetail] = []
    for subrule in rule.rules:
        processor = rule_registry.get_processor(subrule.type)  # type: ignore
        raw = processor(subrule, submission)  # type: ignore
        result = cast(GradeDetail, raw)

        if result:
            sub_results.append(result)

    if not sub_results:
        raise ValueError("No valid sub-rule results for CompositeRule")

    # Use aggregation field directly (model guarantees presence); normalize key
    agg_key = rule.mode.lower()

    if agg_key not in _AGGREGATORS:
        raise ValueError(f"Unsupported aggregation mode '{rule.mode}' in CompositeRule")

    points_awarded, max_points, is_correct = _AGGREGATORS[agg_key](sub_results)

    feedback = _format_feedback(agg_key, sub_results)

    # Aggregate correct answers from sub-results if available
    correct_answers = [d.correct_answer for d in sub_results if d.correct_answer is not None]
    correct_answer = ", ".join(correct_answers) if correct_answers else None

    # Aggregate rule applied from sub-results
    rules_applied = [d.rule_applied for d in sub_results if d.rule_applied is not None]
    rule_applied = f"{rule.mode}: " + ", ".join(rules_applied) if rules_applied else None

    return GradeDetail(
        question_id=rule.question_id,
        student_answer=submission.answers.get(rule.question_id, ""),
        correct_answer=correct_answer,
        points_awarded=points_awarded,
        max_points=max_points,
        is_correct=is_correct,
        rule_applied=rule_applied,
        feedback=feedback,
    )
