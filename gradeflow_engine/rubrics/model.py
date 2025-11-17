from pydantic import BaseModel

from ..question_sets.model import QuestionSet
from ..questions.models import Question
from ..questions.types import QuestionId
from ..rules.models import QuestionRule
from ..rules.result import QuestionResult
from ..rules.types import RuleValidationError
from ..rules.validators import validate_unique_target_questions_in_rules
from ..submissions.models import GradedSubmission, Submission


def grade_submission(rules: list[QuestionRule], submission: Submission) -> GradedSubmission:
    results: list[QuestionResult] = []
    for rule in rules:
        result = rule.process_submission(submission.answer_map)
        if isinstance(result, list):
            results.extend(result)
        else:
            results.append(result)
    graded_submission = GradedSubmission(
        student_id=submission.student_id,
        answer_map=submission.answer_map,
        results=results,
    )
    return graded_submission


class Rubric(BaseModel):
    rules: list[QuestionRule]

    def grade(self, submissions: list[Submission]) -> list[GradedSubmission]:
        return [grade_submission(self.rules, submission) for submission in submissions]

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
