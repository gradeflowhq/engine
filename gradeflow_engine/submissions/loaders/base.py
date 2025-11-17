from pydantic import BaseModel

from ..models import RawSubmission


class BaseSubmissionsLoader(BaseModel):
    def load(self, data: str) -> list[RawSubmission]:
        raise NotImplementedError("Load method must be implemented by subclasses.")
