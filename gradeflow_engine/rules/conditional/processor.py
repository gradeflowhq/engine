"""Conditional rule grading processor."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from ...models import GradeDetail, Submission
    from .model import ConditionalRule

import logging

logger = logging.getLogger(__name__)


def _call_processor(
    rule_obj: Any, submission: "Submission"
) -> "GradeDetail | list[GradeDetail] | None":
    from ...models import GradeDetail  # type: ignore
    from ..registry import rule_registry

    processor = rule_registry.get_processor(rule_obj.type)  # type: ignore
    raw = processor(rule_obj, submission)  # type: ignore
    return cast(GradeDetail, raw)


def _result_is_passing(result: "GradeDetail | list[GradeDetail] | None") -> bool:
    """
    Convert a processor result into a boolean indicating whether the condition passed.

    - None -> False
    - GradeDetail -> result.is_correct
    - list[GradeDetail] -> True if any element is .is_correct
    """
    if result is None:
        return False
    if isinstance(result, list):
        return any(r.is_correct for r in result)
    return bool(result.is_correct)


def _evaluate_if_conditions(if_rules: list[Any], submission: "Submission") -> list[bool]:
    """Evaluate each if-rule and return list of booleans indicating pass/fail."""
    results: list[bool] = []
    for cond in if_rules:
        res = _call_processor(cond, submission)
        results.append(_result_is_passing(res))
    return results


def _aggregate_conditions(bools: list[bool], mode: str) -> bool:
    """Aggregate boolean condition results according to mode ('and'|'or')."""
    mode_normalized = (mode or "").lower()
    if mode_normalized == "and":
        return bool(bools) and all(bools)
    # default to 'or' semantics for anything else
    return any(bools)


def _apply_then_rules(then_rules: list[Any], submission: "Submission") -> list["GradeDetail"]:
    """Apply then-rules and collect GradeDetail results (flattening lists)."""
    results: list["GradeDetail"] = []
    for then_rule in then_rules:
        res = _call_processor(then_rule, submission)
        if res is None:
            continue
        if isinstance(res, list):
            results.extend(res)
        else:
            results.append(res)
    return results


def process_conditional(
    rule: "ConditionalRule", submission: "Submission"
) -> list["GradeDetail"] | None:
    """
    Apply a conditional grading rule to grade a submission.

    Evaluates if-conditions using their rules, and if the aggregated condition
    is met, applies the then-rules to grade the then-questions.
    """
    # Evaluate if-conditions
    condition_results = _evaluate_if_conditions(rule.if_rules, submission)

    # Aggregate based on rule.if_mode (model uses "and"/"or")
    condition_met = _aggregate_conditions(condition_results, rule.if_mode)

    if not condition_met:
        return None

    # Apply then-rules
    then_results = _apply_then_rules(rule.then_rules, submission)

    return then_results if then_results else None
