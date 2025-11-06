"""AssumptionSet rule grading processor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Union, cast

if TYPE_CHECKING:
    from ...models import GradeDetail, Submission
    from .model import AssumptionSetRule


# Module-level typed container for per-assumption results
@dataclass(frozen=True)
class AssumptionResult:
    name: str
    total: float
    details: list["GradeDetail"]


# Alias for the types processors may return
GradeResult = Union["GradeDetail", list["GradeDetail"]] | None


def _to_detail(
    proc_result: GradeResult,
    submission: "Submission",
    question_id: str,
    subrule: Any,
    assumption_name: str,
    rule_type: str,
) -> "GradeDetail":
    """Normalize processor output to a single GradeDetail (use first if list).

    Imports that could cause circular dependencies are done inside the function.
    """
    if proc_result is None:
        max_points = _get_max_points(subrule)
        student_answer = submission.answers.get(question_id, "")
        return _create_failed_detail(
            question_id=question_id,
            student_answer=student_answer,
            max_points=max_points,
            assumption_name=assumption_name,
            rule_type=rule_type,
        )

    # processor returned a GradeDetail or list; pick first element if list
    chosen: "GradeDetail" = proc_result[0] if isinstance(proc_result, list) else proc_result  # type: ignore[assignment]
    return _update_feedback(chosen, assumption_name)


def process_assumption_set(
    rule: "AssumptionSetRule", submission: "Submission"
) -> list["GradeDetail"]:
    """
    Apply an assumption-based grading rule to grade a submission.

    Evaluates every named assumption (each contains its own list of rules),
    then aggregates results according to rule.mode:
      - "best": pick the assumption with the highest total points
      - "worst": pick the assumption with the lowest total points
      - "average": average points per question across assumptions
    """
    # Import here to avoid circular dependency
    from ..registry import rule_registry

    # Map: assumption name -> AssumptionResult
    assumption_map: dict[str, AssumptionResult] = {}

    for assumption in rule.assumptions:
        details: list["GradeDetail"] = []
        total_score = 0.0

        for subrule in assumption.rules:
            # subrule is dynamic; annotate as Any for type-checkers
            if not hasattr(subrule, "question_id"):
                continue

            question_id = subrule.question_id

            # Ensure the subrule's question_id is set correctly on the model instance
            try:
                rule_dict = subrule.model_dump()
                rule_dict["question_id"] = question_id
                subrule = type(subrule)(**rule_dict)
            except Exception:
                # If rebuilding fails, continue with original subrule object
                pass

            # Get processor for this subrule type; registry raises ValueError if unknown
            try:
                processor = rule_registry.get_processor(subrule.type)  # type: ignore
            except ValueError:
                # Skip unknown processors
                continue

            # Process the rule and normalize to a GradeDetail
            # cast the untyped processor result to our GradeResult alias for static checking
            raw = processor(subrule, submission)  # type: ignore
            result = cast(GradeResult, raw)
            detail = _to_detail(
                result, submission, question_id, subrule, assumption.name, rule.type
            )
            total_score += detail.points_awarded
            details.append(detail)

        assumption_map[assumption.name] = AssumptionResult(
            name=assumption.name, total=total_score, details=details
        )

    # No assumptions -> nothing to grade
    if not assumption_map:
        return []

    # Choose/aggregate based on mode
    mode = rule.mode
    if mode == "best":
        chosen = max(assumption_map.values(), key=lambda r: r.total)
        return chosen.details
    elif mode == "worst":
        chosen = min(assumption_map.values(), key=lambda r: r.total)
        return chosen.details
    elif mode == "average":
        from ...models import GradeDetail

        # collect per-question lists
        per_q: dict[str, list[GradeDetail]] = {}
        for rec in assumption_map.values():
            for d in rec.details:
                per_q.setdefault(d.question_id, []).append(d)

        averaged_details: list[GradeDetail] = []
        for qid, dlist in per_q.items():
            total_awarded = sum(d.points_awarded for d in dlist)
            avg_awarded = total_awarded / len(dlist)
            max_points = max(d.max_points for d in dlist)
            student_answer = dlist[0].student_answer
            correct_answer = dlist[0].correct_answer
            is_correct = avg_awarded >= max_points - 1e-9

            # combine unique feedback lines while preserving order
            seen_lines: list[str] = []
            for d in dlist:
                if d.feedback:
                    for line in d.feedback.splitlines():
                        if line not in seen_lines:
                            seen_lines.append(line)
            combined_feedback = "\n".join(seen_lines) if seen_lines else None

            averaged_details.append(
                GradeDetail(
                    question_id=qid,
                    student_answer=student_answer,
                    correct_answer=correct_answer,
                    points_awarded=avg_awarded,
                    max_points=max_points,
                    is_correct=is_correct,
                    rule_applied=rule.type,
                    feedback=(
                        f"Averaged across assumptions:\n{combined_feedback}"
                        if combined_feedback
                        else "Averaged across assumptions"
                    ),
                )
            )

        return averaged_details

    # Unknown mode -> fallback to best
    chosen = max(assumption_map.values(), key=lambda r: r.total)
    return chosen.details


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
        feedback=f"Graded using assumption: {assumption_name}",
    )


def _update_feedback(detail: "GradeDetail", assumption_name: str) -> "GradeDetail":
    """Update feedback to include assumption name."""
    # Create a copy with updated feedback
    detail_dict = detail.model_dump()
    current_feedback = detail_dict.get("feedback", "")
    assumption_feedback = f"Graded using assumption: {assumption_name}"

    if current_feedback:
        detail_dict["feedback"] = f"{current_feedback}\n{assumption_feedback}"
    else:
        detail_dict["feedback"] = assumption_feedback

    from ...models import GradeDetail

    return GradeDetail(**detail_dict)
