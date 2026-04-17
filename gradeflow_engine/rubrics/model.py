import logging
from collections.abc import Mapping

from pydantic import BaseModel, Field

from ..exceptions import GradingError, MissingAnswerError
from ..question_sets.model import QuestionSet
from ..questions.models import Question
from ..questions.types import QuestionId
from ..rules.models import QuestionRule
from ..rules.models.manual import ManualQuestionRule
from ..rules.result import QuestionResult
from ..rules.types import RuleValidationError
from ..rules.validators import validate_unique_target_questions_in_rules
from ..submissions.models import Submission


def _missing_answer_result(max_points: float) -> QuestionResult:
    return QuestionResult(
        points=0.0,
        max_points=max_points,
        feedback="No answer provided.",
        rule="NoAnswer",
        passed=False,
        output=0.0,
    )


def _handle_missing_answer(
    e: MissingAnswerError,
    submission: Submission,
    rule: QuestionRule,
    max_points_map: dict[QuestionId, float],
    strict: bool,
) -> dict[QuestionId, QuestionResult]:
    if strict:
        raise GradingError(
            student_id=submission.student_id,
            question_id=e.question_id,
            reason=(f"Missing answer for question ID {e.question_id} required by rule {rule.type}"),
        ) from e
    logging.warning(
        f"Missing answer for question ID {e.question_id} required by rule {rule.type} "
        f"in submission from student {submission.student_id}. "
        f"Assigning 0 points for this question."
    )
    result = {
        question_id: _missing_answer_result(max_points=max_points_map.get(question_id, 0.0))
        for question_id in rule.get_target_question_ids()
    }
    return result


def _handle_grading_exception(
    e: Exception,
    submission: Submission,
    rule: QuestionRule,
    max_points_map: dict[QuestionId, float],
    strict: bool,
) -> dict[QuestionId, QuestionResult]:
    if strict:
        raise GradingError(
            student_id=submission.student_id,
            question_id=", ".join(sorted(rule.get_target_question_ids())),
            reason=str(e),
        ) from e
    logging.error(
        f"Error processing rule {rule.type} for submission from student "
        f"{submission.student_id}: {e}. "
        f"Assigning 0 points for affected questions."
    )
    result = {
        question_id: ManualQuestionRule(question_id=question_id).process_submission(
            submission.answer_map, max_points_map
        )[question_id]
        for question_id in rule.get_target_question_ids()
    }
    return result


def grade_submission(
    rules: list[QuestionRule],
    submission: Submission,
    question_map: Mapping[QuestionId, Question],
    strict: bool = False,
) -> Submission:
    max_points_map: dict[QuestionId, float] = {qid: q.max_points for qid, q in question_map.items()}
    result_map: dict[QuestionId, QuestionResult] = dict(submission.result_map)
    for rule in rules:
        try:
            result = rule.process_submission(submission.answer_map, max_points_map)
        except MissingAnswerError as e:
            result = _handle_missing_answer(e, submission, rule, max_points_map, strict)
        except Exception as e:
            result = _handle_grading_exception(e, submission, rule, max_points_map, strict)
        result_map.update(result)
    return submission.model_copy(update={"result_map": result_map})


class RubricCoverage(BaseModel):
    question_ids: set[QuestionId] = Field(default_factory=set)
    covered_question_ids: set[QuestionId] = Field(default_factory=set)
    total: int = 0
    covered: int = 0
    percentage: float = 0.0


class Rubric(BaseModel):
    rules: list[QuestionRule]

    def grade(
        self,
        submissions: list[Submission],
        question_map: Mapping[QuestionId, Question],
        strict: bool = False,
    ) -> list[Submission]:
        return [
            grade_submission(self.rules, submission, question_map, strict=strict)
            for submission in submissions
        ]

    def validate_questions_exist(self, question_ids: set[QuestionId]) -> list[RuleValidationError]:
        return [
            error for rule in self.rules for error in rule.validate_questions_exist(question_ids)
        ]

    def validate_compatibility(
        self, question_map: dict[QuestionId, Question]
    ) -> list[RuleValidationError]:
        return [error for rule in self.rules for error in rule.validate_compatibility(question_map)]

    def validate_unique_target_questions(self) -> list[RuleValidationError]:
        return validate_unique_target_questions_in_rules(self.rules)

    def validate_rubric(self, question_set: QuestionSet) -> list[RuleValidationError]:
        question_map = question_set.question_map
        question_ids = set(question_map.keys())
        errors = (
            self.validate_questions_exist(question_ids)
            + self.validate_compatibility(question_map)
            + self.validate_unique_target_questions()
        )
        return errors

    def get_target_question_ids(self) -> set[QuestionId]:
        return {
            question_id for rule in self.rules for question_id in rule.get_target_question_ids()
        }

    def get_coverage(self, question_set: QuestionSet) -> RubricCoverage:
        question_ids = set(question_set.question_map.keys())
        covered_question_ids = self.get_target_question_ids().intersection(question_ids)
        return RubricCoverage(
            question_ids=question_ids,
            covered_question_ids=covered_question_ids,
            total=len(question_ids),
            covered=len(covered_question_ids),
            percentage=len(covered_question_ids) / len(question_ids) if question_ids else 0.0,
        )
