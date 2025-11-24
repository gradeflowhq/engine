from pydantic import BaseModel, Field

from ...questions.models import Question
from ...questions.types import Answer, QuestionId, QuestionType
from ..constraints import QuestionConstraint
from ..result import QuestionResult, Result
from ..types import RuleValidationError
from ..validators import validate_answer_type


class BaseRule(BaseModel):
    question_types: frozenset[QuestionType] = frozenset()
    constraints: list[QuestionConstraint] = []

    def validate_compatibility(
        self, question_map: dict[QuestionId, Question]
    ) -> list[RuleValidationError]:
        raise NotImplementedError("Subclasses must implement this method.")

    def _process_answer(self, answer: Answer) -> Result:
        raise NotImplementedError("Subclasses must implement this method.")

    def process_answer(self, answer: Answer) -> Result:
        validate_answer_type(answer, self.question_types)
        return self._process_answer(answer)


class BaseQuestionRule:
    def validate_questions_exist(self, question_ids: set[QuestionId]) -> list[RuleValidationError]:
        raise NotImplementedError("Subclasses must implement this method.")

    def validate_unique_target_questions(self) -> list[RuleValidationError]:
        raise NotImplementedError("Subclasses must implement this method.")

    def get_target_question_ids(self) -> set[QuestionId]:
        raise NotImplementedError("Subclasses must implement this method.")


class BaseSingleQuestionRule(BaseRule, BaseQuestionRule):
    question_id: QuestionId
    max_points: float = Field(default=1.0, description="Maximum points for the question")

    def validate_compatibility(
        self, question_map: dict[QuestionId, Question]
    ) -> list[RuleValidationError]:
        assert hasattr(self, "type"), "Subclasses must define type."
        if self.question_id not in question_map:
            return []  # Question existence is validated elsewhere
        question_type = question_map[self.question_id].type
        if question_type not in self.question_types:
            return [
                f"Rule of type {self.type} is not compatible with question type {question_type}."  # type: ignore[attr-defined]
            ]
        return []

    def validate_questions_exist(self, question_ids: set[QuestionId]) -> list[RuleValidationError]:
        if self.question_id not in question_ids:
            return [f"Question ID {self.question_id} does not exist in the assessment."]
        return []

    def validate_unique_target_questions(self) -> list[RuleValidationError]:
        return []

    def get_target_question_ids(self) -> set[QuestionId]:
        return {self.question_id}

    def compute_points(self, result: Result) -> float:
        raise NotImplementedError("Subclasses must implement this method.")

    def process_submission(self, answer_map: dict[QuestionId, Answer]) -> QuestionResult:
        if self.question_id not in answer_map:
            raise ValueError(f"Answer for question ID {self.question_id} not found in submission.")
        answer = answer_map[self.question_id]
        result = self.process_answer(answer)
        question_result = QuestionResult(
            **result.model_dump(),
            question_id=self.question_id,
            max_points=self.max_points,
            points=self.compute_points(result),
        )
        return question_result


class BaseMultiQuestionRule(BaseRule, BaseQuestionRule):
    def process_submission(self, answer_map: dict[QuestionId, Answer]) -> list[QuestionResult]:
        raise NotImplementedError("Subclasses must implement this method.")
