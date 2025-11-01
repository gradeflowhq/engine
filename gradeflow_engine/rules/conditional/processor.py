"""Conditional rule grading processor."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models import GradeDetail, Submission
    from .model import ConditionalRule


def process_conditional(
    rule: "ConditionalRule", submission: "Submission"
) -> list["GradeDetail"] | None:
    """
    Apply a conditional grading rule to grade a submission.

    Evaluates if-conditions using their rules, and if the aggregated condition
    is met, applies the then-rules to grade the then-questions.

    Args:
        rule: The Conditional rule to apply
        submission: The student's submission

    Returns:
        List of GradeDetail for then-questions if condition is met, None otherwise
    """
    # Import here to avoid circular dependency
    from ..registry import rule_registry

    # Evaluate all if-conditions
    condition_results = []
    for question_id, condition_rule in rule.if_rules.items():
        # Get the processor for this rule type
        processor = rule_registry.get_processor(condition_rule.type)
        if processor is None:
            # Skip this condition if processor not found (shouldn't happen with valid rules)
            continue

        # Process the rule for this question
        result = processor(condition_rule, submission)

        # Determine if condition passed
        if result is None:
            # Rule didn't apply
            condition_results.append(False)
        elif isinstance(result, list):
            # Multiple results (shouldn't happen for single-question rules)
            # Check if any result is correct
            condition_results.append(any(r.is_correct for r in result))
        else:
            # Single result
            condition_results.append(result.is_correct)

    # Aggregate condition results based on if_aggregation mode
    if rule.if_aggregation == "AND":
        condition_met = all(condition_results) and len(condition_results) > 0
    else:  # OR
        condition_met = any(condition_results)

    if not condition_met:
        # Condition not met, don't grade the then-questions with this rule
        return None

    # Condition met, apply then-rules to then-questions
    results = []
    for question_id, then_rule in rule.then_rules.items():
        # Need to update the question_id for the then_rule if it's different
        # Most single-question rules have a question_id field
        if hasattr(then_rule, "question_id"):
            # Create a copy with updated question_id
            then_rule_dict = then_rule.model_dump()
            then_rule_dict["question_id"] = question_id
            then_rule = type(then_rule)(**then_rule_dict)
        
        # Get the processor for the then-rule
        then_processor = rule_registry.get_processor(then_rule.type)
        if then_processor is None:
            # Shouldn't happen with valid rules
            continue

        # Process the then-rule
        result = then_processor(then_rule, submission)

        # Handle the result
        if result is None:
            continue
        elif isinstance(result, list):
            # Multiple results (shouldn't happen for single-question rules)
            results.extend(result)
        else:
            # Single result
            results.append(result)
    
    return results if results else None
