from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, Field, computed_field

from ...exceptions import MissingAnswerError
from ...questions.models import Question
from ...questions.types import Answer, QuestionId, QuestionType
from ..constraints import QuestionConstraint
from ..result import QuestionResult, Result
from ..types import RuleValidationError
from ..validators import is_empty, validate_answer_type

DEFAULT_MAX_POINTS = 1.0


def rule_type_field(default: str) -> Any:
    return Field(default=default, frozen=True, json_schema_extra={"readOnly": True})


def rule_display_name_field(default: str) -> Any:
    return Field(default=default, frozen=True, json_schema_extra={"readOnly": True})


def rule_question_types_field(question_types: Iterable[QuestionType]) -> Any:
    return Field(
        default=frozenset(question_types),
        frozen=True,
        json_schema_extra={"readOnly": True},
    )


def rule_constraints_field(constraints: Iterable[QuestionConstraint]) -> Any:
    return Field(
        default=list(constraints),
        frozen=True,
        json_schema_extra={"readOnly": True},
    )


class BaseRule(BaseModel, ABC):
    question_types: frozenset[QuestionType] = rule_question_types_field(())
    constraints: list[QuestionConstraint] = rule_constraints_field(())

    @computed_field  # type: ignore[prop-decorator]
    @property
    @abstractmethod
    def description(self) -> str:
        raise NotImplementedError("Subclasses must implement this method.")

    def validate_question_compatibility(self, question: Question) -> list[RuleValidationError]:
        rule_type = getattr(self, "type", self.__class__.__name__)
        errors: list[RuleValidationError] = []
        if question.type not in self.question_types:
            errors.append(
                f"Rule of type {rule_type} is not compatible with question type {question.type}."
            )
        return errors

    @abstractmethod
    def _process_answer(self, answer: Answer) -> Result:
        raise NotImplementedError("Subclasses must implement this method.")

    def process_answer(self, answer: Answer) -> Result:
        if is_empty(answer):
            return Result(
                output=0,
                passed=False,
                feedback="No answer provided.",
                rule=getattr(self, "type", self.__class__.__name__),
            )
        validate_answer_type(answer, self.question_types)
        return self._process_answer(answer)


class BaseQuestionRule(ABC):
    @abstractmethod
    def validate_questions_exist(self, question_ids: set[QuestionId]) -> list[RuleValidationError]:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def validate_unique_target_questions(self) -> list[RuleValidationError]:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get_target_question_ids(self) -> set[QuestionId]:
        raise NotImplementedError("Subclasses must implement this method.")


class BaseSingleQuestionRule(BaseRule, BaseQuestionRule):
    question_id: QuestionId

    def validate_compatibility(
        self, question_map: dict[QuestionId, Question]
    ) -> list[RuleValidationError]:
        if self.question_id not in question_map:
            return []  # Question existence is validated elsewhere
        return self.validate_question_compatibility(question_map[self.question_id])

    def validate_questions_exist(self, question_ids: set[QuestionId]) -> list[RuleValidationError]:
        if self.question_id not in question_ids:
            return [f"Question ID {self.question_id} does not exist in the assessment."]
        return []

    def validate_unique_target_questions(self) -> list[RuleValidationError]:
        return []

    def get_target_question_ids(self) -> set[QuestionId]:
        return {self.question_id}

    def compute_points(self, result: Result, max_points: float) -> float:
        return max_points if result.passed else 0.0

    def process_submission(
        self, answer_map: dict[QuestionId, Answer], max_points_map: dict[QuestionId, float]
    ) -> dict[QuestionId, QuestionResult]:
        if self.question_id not in answer_map:
            raise MissingAnswerError(self.question_id)
        answer = answer_map[self.question_id]
        result = self.process_answer(answer)
        max_points = max_points_map.get(self.question_id, DEFAULT_MAX_POINTS)
        question_result = QuestionResult(
            **result.model_dump(),
            max_points=max_points,
            points=self.compute_points(result, max_points),
        )
        return {self.question_id: question_result}


class BaseMultiQuestionRule(BaseRule, BaseQuestionRule):
    def _process_answer(self, answer: Answer) -> Result:
        raise NotImplementedError("Multi-question rules must process full submissions.")

    @abstractmethod
    def process_submission(
        self, answer_map: dict[QuestionId, Answer], max_points_map: dict[QuestionId, float]
    ) -> dict[QuestionId, QuestionResult]:
        raise NotImplementedError("Subclasses must implement this method.")
