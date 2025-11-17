from pydantic import BaseModel

from ..questions.types import Answer, QuestionId
from ..rules.result import QuestionResult
from .types import StudentId


class BaseSubmission(BaseModel):
    student_id: StudentId


class RawSubmission(BaseSubmission):
    raw_answer_map: dict[QuestionId, str]


class Submission(BaseSubmission):
    answer_map: dict[QuestionId, Answer]


class GradedSubmission(Submission):
    results: list[QuestionResult]
