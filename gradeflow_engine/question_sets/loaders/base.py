from pydantic import BaseModel

from ..model import QuestionSet


class BaseQuestionSetLoader(BaseModel):
    def load(self, data: str) -> QuestionSet:
        raise NotImplementedError("Load method must be implemented by subclasses.")
