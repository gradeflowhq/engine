from dataclasses import dataclass

from ..questions.types import QuestionType


@dataclass(frozen=True)
class QuestionConstraint:
    type: "QuestionType"
    source: str
    target: str
