from typing import Literal

from pydantic import Field

from ...questions.models import Question
from ...questions.models.choice import ChoiceQuestion
from ...questions.types import Answer, QuestionType
from ..aggregations.completeness import points_fn
from ..constraints import QuestionConstraint
from ..result import Result
from ..types import CompletenessAggregation, RuleValidationError
from .base import BaseRule, BaseSingleQuestionRule


def choice_output_fn(
    answer_set: set[str], correct_set: set[str], mode: CompletenessAggregation
) -> float:
    if mode == "ALL":
        return float(answer_set == correct_set)
    elif mode == "ANY":
        return float(any(choice in answer_set for choice in correct_set))
    elif mode == "PARTIAL":
        num_correct = sum(1 for choice in correct_set if choice in answer_set)
        num_incorrect = sum(1 for choice in answer_set if choice not in correct_set)
        return max(0.0, num_correct - num_incorrect) / len(correct_set)
    else:
        raise ValueError(f"Unknown mode: {mode}")


def feedback_fn(
    answer_set: set[str], correct_set: set[str], mode: CompletenessAggregation, passed: bool
) -> str:
    correct_choices = answer_set & correct_set
    incorrect_choices = answer_set - correct_set
    notselected_correct = correct_set - answer_set
    feedback_parts: list[str] = []
    if correct_choices:
        feedback_parts.append(f"Correct choice(s) selected: {', '.join(sorted(correct_choices))}.")
    if incorrect_choices:
        feedback_parts.append(
            f"Incorrect choice(s) selected: {', '.join(sorted(incorrect_choices))}."
        )
    if notselected_correct:
        feedback_parts.append(
            f"Correct choice(s) not selected: {', '.join(sorted(notselected_correct))}."
        )
    feedback = " ".join(feedback_parts)
    if mode == "ALL" and not passed:
        feedback = "Incorrect choice(s).\n" + feedback
    if mode == "ANY" and not passed:
        feedback = "No correct choice(s) were selected.\n" + feedback
    if mode == "PARTIAL" and len(incorrect_choices) + len(notselected_correct) > 0:
        feedback = (
            f"Partial credit: "
            f"({len(correct_choices)} - {len(incorrect_choices)}) / {len(correct_set)} "
            "* max points (minimum: 0).\n"
        ) + feedback
    return feedback


def passed_fn(answer_set: set[str], correct_set: set[str], mode: CompletenessAggregation) -> bool:
    if mode == "ALL":
        return answer_set == correct_set
    elif mode in ["ANY", "PARTIAL"]:
        return len(answer_set & correct_set) > 0
    else:
        raise ValueError(f"Unknown mode: {mode}")


class MultipleChoiceRule(BaseRule):
    type: Literal["MULTIPLE_CHOICE"] = "MULTIPLE_CHOICE"
    question_types: frozenset[QuestionType] = frozenset({"CHOICE"})
    constraints: list[QuestionConstraint] = [
        QuestionConstraint(type="CHOICE", source="options", target="answer"),
    ]
    answer: set[str] = Field(..., min_length=1, description="Set of correct choices")
    mode: CompletenessAggregation = Field(
        default="ALL",
        description=(
            "Mode of choice matching: "
            "'ALL' requires all correct choices to be selected, "
            "'ANY' requires at least one, "
            "'PARTIAL' gives credit for each correct choice selected minus "
            "each incorrect choice selected."
        ),
    )

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
        assert isinstance(answer, set) and all(isinstance(a, str) for a in answer), (
            "Answer must be a set of strings for MultipleChoiceRule."
        )

        answer_set = set(map(str, answer))
        passed = passed_fn(answer_set, self.answer, mode=self.mode)
        output = choice_output_fn(answer_set, self.answer, mode=self.mode)
        feedback = feedback_fn(answer_set, self.answer, mode=self.mode, passed=passed)
        return Result(
            output=output,
            passed=passed,
            feedback=feedback,
            rule=self.__class__.__name__,
        )


class MultipleChoiceQuestionRule(MultipleChoiceRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result, max_points: float) -> float:
        return points_fn(result, mode=self.mode, max_points=max_points)
