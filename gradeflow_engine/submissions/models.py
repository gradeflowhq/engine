from pydantic import BaseModel, Field

from ..questions.types import Answer, QuestionId
from ..rules.result import QuestionResult
from .types import StudentId


class BaseSubmission(BaseModel):
    student_id: StudentId
    result_map: dict[QuestionId, QuestionResult] = Field(default_factory=dict)


class RawSubmission(BaseSubmission):
    raw_answer_map: dict[QuestionId, str]


class Submission(BaseSubmission):
    answer_map: dict[QuestionId, Answer]
