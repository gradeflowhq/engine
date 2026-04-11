from pydantic import BaseModel, Field, computed_field

from ...questions.models import Question
from ...questions.types import Answer, QuestionId, QuestionType
from ..constraints import QuestionConstraint
from ..result import QuestionResult, Result
from ..types import RuleValidationError
from ..validators import is_empty, validate_answer_type

DEFAULT_MAX_POINTS = 1.0


class BaseRule(BaseModel):
    question_types: frozenset[QuestionType] = Field(
        default=frozenset(),
        frozen=True,
        json_schema_extra={"readOnly": True},
    )
    constraints: list[QuestionConstraint] = Field(
        default=[],
        frozen=True,
        json_schema_extra={"readOnly": True},
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def description(self) -> str:
        raise NotImplementedError("Subclasses must implement this method.")

    def validate_question_compatibility(self, question: Question) -> list[RuleValidationError]:
        assert hasattr(self, "type"), "Rule must have a 'type' attribute."
        errors: list[RuleValidationError] = []
        if question.type not in self.question_types:
            errors.append(
                f"Rule of type {self.type} "  # type: ignore[attr-defined]
                f"is not compatible with question type {question.type}."
            )
        return errors

    def _process_answer(self, answer: Answer) -> Result:
        raise NotImplementedError("Subclasses must implement this method.")

    def process_answer(self, answer: Answer) -> Result:
        if is_empty(answer):
            return Result(
                output=0,
                passed=False,
                feedback="No answer provided.",
                rule=self.type,  # type: ignore[attr-defined]
            )
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
        raise NotImplementedError("Subclasses must implement this method.")

    def process_submission(
        self, answer_map: dict[QuestionId, Answer], max_points_map: dict[QuestionId, float]
    ) -> dict[QuestionId, QuestionResult]:
        if self.question_id not in answer_map:
            raise ValueError(f"Answer for question ID {self.question_id} not found in submission.")
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
    def process_submission(
        self, answer_map: dict[QuestionId, Answer], max_points_map: dict[QuestionId, float]
    ) -> dict[QuestionId, QuestionResult]:
        raise NotImplementedError("Subclasses must implement this method.")
