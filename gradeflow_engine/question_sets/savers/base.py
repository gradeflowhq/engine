from pydantic import BaseModel

from ..model import QuestionSet


class QuestionSetSaverOutput(BaseModel):
    data: str
    extension: str


class BaseQuestionSetSaver(BaseModel):
    def save(self, question_set: QuestionSet) -> QuestionSetSaverOutput:
        raise NotImplementedError("Save method must be implemented by subclasses.")
