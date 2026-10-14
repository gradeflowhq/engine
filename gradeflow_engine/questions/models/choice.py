from typing import Literal

from pydantic import Field, field_validator, model_validator

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
    options: dict[str, str | None] = Field(
        default_factory=dict,
        description="Mapping of valid choice IDs to optional displayed option text.",
    )
    allow_multiple: bool = Field(
        default=False,
        description="Whether to allow multiple choices to be selected.",
    )

    @field_validator("options", mode="before")
    @classmethod
    def _normalize_legacy_option_collections(cls, value: object) -> object:
        """Accept legacy YAML sets and JSON arrays while storing one canonical mapping."""
        if isinstance(value, (set, list, tuple)):
            return dict.fromkeys(value)
        return value

    @model_validator(mode="after")
    def _validate_and_normalize_options(self) -> "ChoiceQuestion":
        # Normalize IDs to match answer parsing while preserving displayed text casing.
        normalized_options: dict[str, str | None] = {}
        seen: set[str] = set()
        for option_id, option_text in self.options.items():
            if self.config.trim_whitespace:
                option_id = option_id.strip()
            if self.config.normalize_case:
                option_id = option_id.lower()
            if not option_id:
                raise ValueError("Choice options must not contain empty values.")
            if option_id in seen:
                raise ValueError(f"Duplicate choice option detected: {option_id!r}")
            if option_text is not None:
                option_text = option_text.strip()
                if not option_text:
                    raise ValueError("Choice option text must not be empty when provided.")
            seen.add(option_id)
            normalized_options[option_id] = option_text
        self.options = normalized_options
        return self

    @property
    def option_ids(self) -> set[str]:
        """Return the valid submission-facing choice IDs."""
        return set(self.options)

    def parse(self, raw_answer: str) -> ChoiceAnswer:
        return set(
            parse_multi_value(
                raw_answer,
                delimiter=self.config.delimiter,
                trim_whitespace=self.config.trim_whitespace,
                normalize_case=self.config.normalize_case,
            )
        )
