from typing import Literal

from ..types import NumericAnswer
from ..utils import try_parse_number
from .base import BaseQuestion


class NumericQuestion(BaseQuestion[NumericAnswer]):
    type: Literal["NUMERIC"] = "NUMERIC"

    def parse(self, raw_answer: str) -> NumericAnswer:
        return try_parse_number(raw_answer)
