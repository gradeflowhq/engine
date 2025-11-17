from pydantic import BaseModel

from ..model import Rubric


class BaseRubricLoader(BaseModel):
    def load(self, data: str) -> Rubric:
        raise NotImplementedError("Load method must be implemented by subclasses.")
