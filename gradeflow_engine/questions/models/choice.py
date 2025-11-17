from typing import Literal

from pydantic import Field, model_validator

from ..parser import MultiValuedParserConfig
from ..types import ChoiceAnswer
from ..utils import parse_multi_value
from .base import BaseQuestion


class ChoiceQuestion(BaseQuestion[ChoiceAnswer]):
    type: Literal["CHOICE"] = "CHOICE"
    config: MultiValuedParserConfig = Field(
        default_factory=MultiValuedParserConfig,
        description="Parser configuration for choice questions.",
    )
    options: set[str] = Field(
        default_factory=set,
        description="Set of valid choices for this question.",
    )
    allow_multiple: bool = Field(
        default=False,
        description="Whether to allow multiple choices to be selected.",
    )

    @model_validator(mode="after")
    def _validate_and_normalize_options(self) -> "ChoiceQuestion":
        # Trim and optionally normalize case of options to match parsing behavior
        normalized_options: set[str] = set()
        seen: set[str] = set()
        for option in self.options:
            if self.config.trim_whitespace:
                option = option.strip()
            if self.config.normalize_case:
                option = option.lower()
            if not option:
                raise ValueError("Choice options must not contain empty values.")
            if option in seen:
                raise ValueError(f"Duplicate choice option detected: {option!r}")
            seen.add(option)
            normalized_options.add(option)
        self.options = normalized_options
        return self

    def parse(self, raw_answer: str) -> ChoiceAnswer:
        return set(
            parse_multi_value(
                raw_answer,
                delimiter=self.config.delimiter,
                trim_whitespace=self.config.trim_whitespace,
                normalize_case=self.config.normalize_case,
            )
        )
