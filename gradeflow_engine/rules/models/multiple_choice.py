from typing import Literal

from pydantic import Field, computed_field

from ...questions.models import Question
from ...questions.models.choice import ChoiceQuestion
from ...questions.types import Answer, QuestionType
from ..aggregations.completeness import points_fn
from ..constraints import QuestionConstraint
from ..result import Result
from ..types import CompletenessAggregation, RuleValidationError
from .base import (
    BaseRule,
    BaseSingleQuestionRule,
    rule_constraints_field,
    rule_display_name_field,
    rule_question_types_field,
    rule_type_field,
)


def _sorted_join(items: set[str]) -> str:
    return ", ".join(sorted(items))


def _build_feedback(
    answer_set: set[str], correct_set: set[str], mode: CompletenessAggregation, passed: bool
) -> str:
    correct_selected = answer_set & correct_set
    incorrect_selected = answer_set - correct_set
    missed_correct = correct_set - answer_set

    # --- Header: verdict line ---
    if passed:
        if mode == "PARTIAL" and (incorrect_selected or missed_correct):
            header = "Partially correct."
        else:
            header = "Correct."
    else:
        verdict_map: dict[CompletenessAggregation, str] = {
            "ALL": "Incorrect — all correct choices must be selected with no extras.",
            "CONTAIN": "Incorrect — all correct choices must be selected.",
            "NOT_CONTAIN": "Incorrect — none of the specified choices should be selected.",
            "ANY": "Incorrect — at least one correct choice must be selected.",
            "PARTIAL": "Incorrect.",
        }
        header = verdict_map.get(mode, "Incorrect.")

    # --- Body: breakdown ---
    body_parts: list[str] = []

    if correct_selected:
        body_parts.append(f"Correct choice(s) selected: {_sorted_join(correct_selected)}")
    if incorrect_selected:
        body_parts.append(f"Incorrect choice(s) selected: {_sorted_join(incorrect_selected)}")
    if missed_correct:
        body_parts.append(f"Correct choice(s) not selected: {_sorted_join(missed_correct)}")

    # --- Footer: scoring context for PARTIAL mode ---
    footer = ""
    if mode == "PARTIAL":
        n_correct = len(correct_selected)
        n_incorrect = len(incorrect_selected)
        n_total = len(correct_set)
        raw_score = max(0, n_correct - n_incorrect)
        footer = (
            f"Score: max(0, {n_correct} correct − {n_incorrect} incorrect) "
            f"/ {n_total} = {raw_score}/{n_total} of max points."
        )

    # --- Expected answer (shown on failure for learning) ---
    expected = ""
    if not passed:
        if mode == "NOT_CONTAIN":
            expected = f"Expected: none of {{{_sorted_join(correct_set)}}}"
        elif len(correct_set) == 1:
            expected = f"Expected: {_sorted_join(correct_set)}"
        else:
            label = "all of" if mode in ("ALL", "CONTAIN") else "any of"
            expected = f"Expected: {label} {{{_sorted_join(correct_set)}}}"

    # --- Assemble ---
    sections = [header]
    if body_parts:
        sections.append("\n".join(body_parts))
    if footer:
        sections.append(footer)
    if expected:
        sections.append(expected)

    return "\n".join(sections)


def _evaluate_choice(
    answer_set: set[str], correct_set: set[str], mode: CompletenessAggregation
) -> Result:
    if mode == "ALL":
        passed = answer_set == correct_set
        output = float(passed)
    elif mode == "CONTAIN":
        passed = correct_set.issubset(answer_set)
        output = float(passed)
    elif mode == "NOT_CONTAIN":
        passed = answer_set.isdisjoint(correct_set)
        output = float(passed)
    elif mode == "ANY":
        passed = len(answer_set & correct_set) > 0
        output = float(passed)
    elif mode == "PARTIAL":
        num_correct = sum(1 for choice in correct_set if choice in answer_set)
        num_incorrect = sum(1 for choice in answer_set if choice not in correct_set)
        output = max(0.0, num_correct - num_incorrect) / len(correct_set)
        passed = output > 0.0
    else:
        raise ValueError(f"Unknown mode: {mode}")

    return Result(
        output=output,
        passed=passed,
        feedback=_build_feedback(answer_set, correct_set, mode=mode, passed=passed),
        rule=MultipleChoiceRule.__name__,
    )


class MultipleChoiceRule(BaseRule):
    type: Literal["MULTIPLE_CHOICE"] = rule_type_field("MULTIPLE_CHOICE")
    display_name: Literal["Multiple Choice"] = rule_display_name_field("Multiple Choice")
    question_types: frozenset[QuestionType] = rule_question_types_field({"CHOICE"})
    constraints: list[QuestionConstraint] = rule_constraints_field(
        [QuestionConstraint(type="CHOICE", source="options", target="answer")]
    )
    answer: set[str] = Field(..., min_length=1, description="Set of correct choices")
    mode: CompletenessAggregation = Field(
        default="ALL",
        description=(
            "Mode of choice matching: "
            "'ALL' requires all specified choices to be selected, "
            "'CONTAIN' requires all specified choices to be selected but allows extra choices, "
            "'NOT_CONTAIN' requires none of the specified choices to be selected, "
            "'ANY' requires at least one of the specified choices to be selected, "
            "'PARTIAL' gives credit for each specified choice selected minus "
            "each unspecified choice selected."
        ),
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def description(self) -> str:
        if self.mode == "ALL":
            return f"Include all of these choices: {', '.join(self.answer)}."
        elif self.mode == "ANY":
            return f"Include at least one of these choices: {', '.join(self.answer)}."
        elif self.mode == "CONTAIN":
            return (
                f"Include all of these choices (but may include others): {', '.join(self.answer)}."
            )
        elif self.mode == "NOT_CONTAIN":
            return f"Do not include any of these choices: {', '.join(self.answer)}."
        elif self.mode == "PARTIAL":
            return f"Partial credit for correct choices: {', '.join(self.answer)}."
        else:
            raise ValueError(f"Unknown mode: {self.mode}")

    def validate_question_compatibility(self, question: Question) -> list[RuleValidationError]:
        errors: list[RuleValidationError] = []
        if not isinstance(question, ChoiceQuestion):
            errors.append(
                f"Rule of type {self.type} is not compatible with question type {question.type}."
            )
            return errors
        invalid_choices = self.answer - set(question.options)
        if invalid_choices:
            errors.append(
                f"Invalid answer choices: {', '.join(sorted(invalid_choices))}"
                f" for question with options: {', '.join(sorted(question.options))}"
            )
        return errors

    def _process_answer(self, answer: Answer) -> Result:
        if not isinstance(answer, set) or not all(isinstance(a, str) for a in answer):
            raise TypeError("Answer must be a set of strings for MultipleChoiceRule.")

        answer_set = set(map(str, answer))
        result = _evaluate_choice(answer_set, self.answer, mode=self.mode)
        return result.model_copy(update={"rule": self.__class__.__name__})


class MultipleChoiceQuestionRule(MultipleChoiceRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result, max_points: float) -> float:
        return points_fn(result, mode=self.mode, max_points=max_points)
