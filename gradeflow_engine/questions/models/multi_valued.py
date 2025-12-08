from typing import Any, Literal

from pydantic import Field

from ..parser import BaseParserConfig, MultiValuedParserConfig, TextParserConfig
from ..types import MultiValuedAnswer
from ..utils import parse_multi_value
from .base import BaseQuestion
from .numeric import NumericQuestion
from .text import TextQuestion

MultiValueTypes = Literal["TEXT", "NUMERIC"]


class MultiValuedQuestion(BaseQuestion[MultiValuedAnswer]):
    type: Literal["MULTI_VALUED"] = "MULTI_VALUED"
    config: MultiValuedParserConfig = Field(
        default_factory=MultiValuedParserConfig,
        description="Parser configuration for multi-valued questions.",
    )
    value_types: list[MultiValueTypes] = Field(
        ...,
        description=("Expected type for each value in the answer."),
    )

    def model_post_init(self, __context: Any) -> None:
        self._text_question = TextQuestion(
            config=TextParserConfig(
                empty_marker=self.config.empty_marker,
                trim_whitespace=self.config.trim_whitespace,
                normalize_case=self.config.normalize_case,
            )
        )
        self._numeric_question = NumericQuestion(
            config=BaseParserConfig(
                empty_marker=self.config.empty_marker,
            )
        )

    def parse(self, raw_answer: str) -> MultiValuedAnswer:
        raw_multi_valued_answer = parse_multi_value(
            raw_answer,
            delimiter=self.config.delimiter,
            trim_whitespace=self.config.trim_whitespace,
            normalize_case=self.config.normalize_case,
        )
        if len(raw_multi_valued_answer) != len(self.value_types):
            raise ValueError(
                f"Expected {len(self.value_types)} values, "
                f"but got {len(raw_multi_valued_answer)} values."
            )
        parsed_answer: MultiValuedAnswer = [None] * len(self.value_types)
        for i, (answer, value_type) in enumerate(
            zip(raw_multi_valued_answer, self.value_types, strict=True)
        ):
            if value_type == "NUMERIC":
                parsed_answer[i] = self._numeric_question.parse(str(answer))
            elif value_type == "TEXT":
                parsed_answer[i] = self._text_question.parse(str(answer))
            else:
                raise ValueError(f"Unsupported value type: {value_type}")

        return parsed_answer
