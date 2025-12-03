from typing import Literal

from pydantic import Field

from ..parser import TextParserConfig
from ..types import TextAnswer
from ..utils import is_empty_answer
from .base import BaseQuestion


class TextQuestion(BaseQuestion[TextAnswer]):
    type: Literal["TEXT"] = "TEXT"
    config: TextParserConfig = Field(
        default_factory=TextParserConfig,
        description="Parser configuration for text questions.",
    )

    def parse(self, raw_answer: str) -> TextAnswer:
        if is_empty_answer(raw_answer, self.config.empty_marker):
            return None
        return str(raw_answer)
