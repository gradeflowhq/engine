from typing import Literal

from ..types import TextAnswer
from .base import BaseQuestion


class TextQuestion(BaseQuestion[TextAnswer]):
    type: Literal["TEXT"] = "TEXT"

    def parse(self, raw_answer: str) -> TextAnswer:
        return str(raw_answer)
