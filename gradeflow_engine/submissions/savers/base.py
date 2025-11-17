from collections.abc import Iterable

from pydantic import BaseModel

from ...submissions.models import GradedSubmission


class SubmissionsSaverOutput(BaseModel):
    data: str
    extension: str


class BaseSubmissionsSaver(BaseModel):
    def save(self, submissions: Iterable[GradedSubmission]) -> SubmissionsSaverOutput:
        raise NotImplementedError("Save method must be implemented by subclasses.")
