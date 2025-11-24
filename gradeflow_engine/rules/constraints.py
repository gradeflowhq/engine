from pydantic import BaseModel

from ..questions.types import QuestionType


class QuestionConstraint(BaseModel):
    type: "QuestionType"
    source: str
    target: str
