from typing import Generic, TypeVar

from pydantic import BaseModel, Field

AnswerType = TypeVar("AnswerType", covariant=True)


class BaseQuestion(BaseModel, Generic[AnswerType]):
    max_points: float = Field(default=1.0, description="Maximum points for the question")
    description: str | None = Field(
        default=None, description="Optional description of the question."
    )

    def parse(self, raw_answer: str) -> AnswerType:
        """Parse a raw answer string into an Answer object."""
        raise NotImplementedError("Subclasses must implement this method.")
