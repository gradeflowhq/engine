from typing import Literal

from pydantic import Field

from ..parser import BaseParserConfig
from ..types import NumericAnswer
from ..utils import is_empty_answer, try_parse_number
from .base import BaseQuestion


class NumericQuestion(BaseQuestion[NumericAnswer]):
    type: Literal["NUMERIC"] = "NUMERIC"
    config: BaseParserConfig = Field(
        default_factory=BaseParserConfig,
        description="Parser configuration for numeric questions.",
    )

    def parse(self, raw_answer: str) -> NumericAnswer:
        if is_empty_answer(raw_answer, self.config.empty_marker):
            return None
        return try_parse_number(raw_answer)
