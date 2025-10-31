"""Composite rule grading processor."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models import GradeDetail, GradingRule, Submission
    from .model import CompositeRule


def process_composite(rule: "CompositeRule", submission: "Submission") -> list["GradeDetail"]:
    """
    Apply a composite rule by evaluating all sub-rules on the same question
    and combining their results based on the mode (AND/OR/WEIGHTED).

    All sub-rules evaluate the same question_id (from the composite rule).
    Returns a single GradeDetail with the combined score.

    Args:
        rule: The Composite rule to apply
        submission: The student's submission

    Returns:
        List containing a single GradeDetail with combined score

    Examples:
        AND mode - all criteria must pass:
            >>> rule = CompositeRule(
            ...     question_id="Q1",
            ...     mode="AND",
            ...     rules=[
            ...         ExactMatchRule(question_id="Q1", correct_answer="Paris", max_points=5),
            ...         LengthRule(question_id="Q1", min_words=2, max_points=5)
            ...     ]
            ... )
            >>> # Student must answer "Paris" AND use at least 2 words

        OR mode - at least one criterion must pass:
            >>> rule = CompositeRule(
            ...     question_id="Q1",
            ...     mode="OR",
            ...     min_passing=1,
            ...     rules=[
            ...         ExactMatchRule(question_id="Q1", correct_answer="London", max_points=10),
            ...         ExactMatchRule(question_id="Q1", correct_answer="Paris", max_points=10)
            ...     ]
            ... )
            >>> # Student can answer either "London" OR "Paris"

        WEIGHTED mode - weighted combination:
            >>> rule = CompositeRule(
            ...     question_id="Q1",
            ...     mode="WEIGHTED",
            ...     weights=[0.7, 0.3],
            ...     rules=[
            ...         SimilarityRule(
            ...             question_id="Q1", expected="example",
            ...             threshold=0.8, max_points=10
            ...         ),
            ...         LengthRule(question_id="Q1", min_words=10, max_points=10)
            ...     ]
            ... )
            >>> # 70% weight on similarity, 30% on length
    """
    # Import here to avoid circular dependency
    from ...models import GradeDetail

    # Override question_id in sub-rules to match the composite rule's question
    sub_results: list[GradeDetail] = []

    for sub_rule in rule.rules:
        # Create a modified sub-rule with the composite rule's question_id
        detail = _apply_single_rule_with_question_override(sub_rule, rule.question_id, submission)
        if detail:
            sub_results.append(detail)

    # If no results from sub-rules, return empty list
    if not sub_results:
        return []

    # Apply the composite mode logic
    if rule.mode == "AND":
        # All rules must pass (get full points)
        all_passed = all(detail.is_correct for detail in sub_results)

        # Calculate total points from sub-rules
        total_points = sum(d.points_awarded for d in sub_results) if all_passed else 0.0
        total_max = sum(d.max_points for d in sub_results)

        # Combine feedback
        if all_passed:
            feedback = f"All {len(sub_results)} criteria passed"
        else:
            failed_count = sum(1 for d in sub_results if not d.is_correct)
            feedback = f"AND mode: {failed_count}/{len(sub_results)} criteria failed"

        return [
            GradeDetail(
                question_id=rule.question_id,
                student_answer=submission.answers.get(rule.question_id, ""),
                correct_answer=None,
                points_awarded=total_points,
                max_points=total_max,
                is_correct=all_passed,
                rule_applied=rule.type,
                feedback=feedback,
            )
        ]

    elif rule.mode == "OR":
        # At least one rule must pass
        min_passing = rule.min_passing if rule.min_passing else 1
        passed_count = sum(1 for detail in sub_results if detail.is_correct)

        # Award points based on best result if passed
        if passed_count >= min_passing:
            best_points = max(d.points_awarded for d in sub_results)
            total_max = max(d.max_points for d in sub_results)
            feedback = f"OR mode: {passed_count}/{len(sub_results)} criteria passed"
            is_correct = True
        else:
            best_points = 0.0
            total_max = max(d.max_points for d in sub_results)
            feedback = f"OR mode: only {passed_count}/{len(sub_results)} passed, need {min_passing}"
            is_correct = False

        return [
            GradeDetail(
                question_id=rule.question_id,
                student_answer=submission.answers.get(rule.question_id, ""),
                correct_answer=None,
                points_awarded=best_points,
                max_points=total_max,
                is_correct=is_correct,
                rule_applied=rule.type,
                feedback=feedback,
            )
        ]

    elif rule.mode == "WEIGHTED":
        # Weighted average of all rules
        if not rule.weights or len(rule.weights) != len(sub_results):
            raise ValueError("WEIGHTED mode requires weights matching number of rules")

        # Weights are already validated to sum to 1.0, no normalization needed

        # Calculate weighted score
        weighted_points = 0.0
        weighted_max = 0.0

        for detail, weight in zip(sub_results, rule.weights, strict=True):
            weighted_points += detail.points_awarded * weight
            weighted_max += detail.max_points * weight

        # Use configurable threshold for correctness determination
        is_correct = weighted_points >= weighted_max * rule.correctness_threshold

        return [
            GradeDetail(
                question_id=rule.question_id,
                student_answer=submission.answers.get(rule.question_id, ""),
                correct_answer=None,
                points_awarded=weighted_points,
                max_points=weighted_max,
                is_correct=is_correct,
                rule_applied=rule.type,
                feedback=f"Weighted score: {weighted_points:.2f}/{weighted_max:.2f}",
            )
        ]

    # Fallback: return all results
    return sub_results


def _apply_single_rule_with_question_override(
    sub_rule: GradingRule, question_id: str, submission: Submission
) -> GradeDetail | None:
    """
    Apply a single rule but override its question_id to match composite rule.

    Uses Pydantic's model_copy() for efficient rule copying instead of
    manual field-by-field copying (saves ~100 lines of code!).

    Args:
        sub_rule: The rule to apply
        question_id: Question ID to override
        submission: Student submission

    Returns:
        GradeDetail or None
    """
    from ..registry import rule_registry

    # Use Pydantic's model_copy to create a modified rule with new question_id
    # This is much cleaner than manually copying all fields for each rule type!
    try:
        modified_rule = sub_rule.model_copy(update={"question_id": question_id})
    except Exception:
        # If model_copy fails for any reason, fallback to using rule as-is
        # (e.g., for ProgrammableRule which might not support question_id override)
        modified_rule = sub_rule

    # Get the processor for this rule type from registry
    processor = rule_registry.get_processor(modified_rule.type)

    # Apply the processor
    result = processor(modified_rule, submission)

    # Handle list results (some processors return lists)
    if isinstance(result, list):
        return result[0] if result else None  # type: ignore[no-any-return,return-value]

    return result  # type: ignore[no-any-return,return-value]
