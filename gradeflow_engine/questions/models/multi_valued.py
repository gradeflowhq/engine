from collections.abc import Sequence
from typing import Literal

from pydantic import Field

from ..parser import MultiValuedParserConfig
from ..types import MultiValuedAnswer, SingleValuedAnswer
from ..utils import parse_multi_value, try_parse_number
from .base import BaseQuestion


def parse_multi_valued_answer(raw_multi_valued_answer: Sequence[str]) -> MultiValuedAnswer:
    result: list[SingleValuedAnswer] = []
    for value in raw_multi_valued_answer:
        try:
            num = try_parse_number(value)
            result.append(num)
        except ValueError:
            result.append(value)
    return result


class MultiValuedQuestion(BaseQuestion[MultiValuedAnswer]):
    type: Literal["MULTI_VALUED"] = "MULTI_VALUED"
    config: MultiValuedParserConfig = Field(
        default_factory=MultiValuedParserConfig,
        description="Parser configuration for multi-valued questions.",
    )

    def parse(self, raw_answer: str) -> MultiValuedAnswer:
        raw_multi_valued_answer = parse_multi_value(
            raw_answer,
            delimiter=self.config.delimiter,
            trim_whitespace=self.config.trim_whitespace,
            normalize_case=self.config.normalize_case,
        )
        return parse_multi_valued_answer(raw_multi_valued_answer)
