from typing import Literal

from pydantic import Field

from ...questions.models import Question
from ...questions.models.choice import ChoiceQuestion
from ...questions.types import Answer, QuestionId, QuestionType
from ..aggregations.completeness import passed_fn, points_fn
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


class MultipleChoiceRule(BaseRule):
    type: Literal["MULTIPLE_CHOICE"] = "MULTIPLE_CHOICE"
    question_types: frozenset[QuestionType] = frozenset({"CHOICE"})
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

    def _process_answer(self, answer: Answer) -> Result:
        assert isinstance(answer, set), "Answer must be a set for MultipleChoiceRule."

        answer_set = set(map(str, answer))
        matches = [choice in answer_set for choice in self.answer]
        passed = passed_fn(matches, mode=self.mode)
        output = choice_output_fn(answer_set, self.answer, mode=self.mode)
        feedback = f"The answer ({answer}) " + (
            "is correct."
            if passed
            else f"is incorrect. Correct choices are: {', '.join(self.answer)}."
        )

        return Result(
            output=output,
            passed=passed,
            feedback=feedback,
            rule=self.__class__.__name__,
        )


class MultipleChoiceQuestionRule(MultipleChoiceRule, BaseSingleQuestionRule):
    def validate_compatibility(
        self, question_map: dict[QuestionId, Question]
    ) -> list[RuleValidationError]:
        errors = super().validate_compatibility(question_map)
        question = question_map.get(self.question_id)
        if not isinstance(question, ChoiceQuestion):
            errors.append(
                f"Question {self.question_id} is not a ChoiceQuestion, "
                f"but {self.__class__.__name__} requires a ChoiceQuestion."
            )
            return errors
        invalid_choices = self.answer - set(question.options)
        if invalid_choices:
            errors.append(
                f"Invalid answer choices for question {self.question_id}: "
                f"{', '.join(invalid_choices)}"
            )
        return errors

    def compute_points(self, result: Result) -> float:
        return points_fn(result, mode=self.mode, max_points=self.max_points)
